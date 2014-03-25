"""
ParserUnrevised -- parser for handling an unrevised variants section
    (<vfSectLoose>).

@author: James McCracken
"""

import re

from lxml import etree  # @UnresolvedImport

from lex.oed.variants.variantform import VariantFormFromParser
from lex.oed.variants.parsers import utilities

# Nodes collected by xpath when parsing an unrevised forms list.
#   Note that la, w, pr, and p are not really required, but
#   are collected in order to access any tail text they may have.
SALIENT_NODES_XPATH = './/vf | .//gr | .//vd | .//la | .//w | .//pr | .//p | .//cf | .//xr'

GREEK_LETTERS_PATTERN = re.compile('(\u03b1|\u03b2|\u03b3|\u03b4)')
IGNORABLE_GRAMMAR_PATTERN = re.compile(r'^(forms|wk\.|weak|str\.|strong)(| forms?)$', re.I)

# The following are used when determining whether a <cf> element should
#  be treated like <gr> or like <la>.
GRAMMAR_LIKE = re.compile(r'(infle[cx]|plural|compar|superl)', re.I)
LABEL_LIKE = re.compile(r'(north|south|kentish|anglian|mercian|york|arch|incorrect|misspell|printed|ormin|orm\.|layamon)', re.I)

PERIOD_MAP = {'old english': 'OE', 'middle english': 'ME',
              'modern english': '16-', 'early modern english': '15-16'}


class ParserUnrevised(object):

    """
    Parser for handling an unrevised variants section (<vfSectLoose>).
    """

    def __init__(self, node):
        self.node = _modify_node(node)

    def parse(self):
        """
        Parse the forms list and return a list of VariantForm objects.
        """
        # Build a list of all the elements of the vfsectLoose, in sequence,
        #  including all tagged nodes (vd, variant_form, grammar, etc.)
        #  and all text
        elements = []

        # Handle any text preceding the very first tag
        pretag_nodes = _handle_tail(self.node.text)
        elements.extend(pretag_nodes)

        for node in self.node.xpath(SALIENT_NODES_XPATH):
            elements.append(VfsectLooseNode(node=node))
            # Handle any significant text following the element (tail)
            tail_nodes = _handle_tail(node.tail)
            elements.extend(tail_nodes)

        # Add the previous and following tags to each element as 'previous'
        #   and 'next'
        for i, element in enumerate(elements):
            try:
                element.previous = elements[i - 1].tag
            except IndexError:
                element.previous = None
            try:
                element.next = elements[i + 1].tag
            except IndexError:
                element.next = None

        vf_list = _build_vflist(elements)
        return utilities.unpack_parentheses(vf_list)


class VfsectLooseNode(object):

    """
    Element within an unrevised forms list.
    """

    def __init__(self, **kwargs):
        if kwargs.get('node') is not None:
            self.node = kwargs.get('node')
            self.tag = self.node.tag
            self.text = self.node.text
            self.src = self.node.text
            self._correct_cf_tag()
            # __date_range may sometimes be an attribute rather than text
            if self.tag == 'vd' and not self.text:
                self.text = self.node.get('date')

        elif kwargs.get('text') is not None:
            self.node = kwargs.get('text')
            self.text = kwargs.get('text')
            self.tag = kwargs.get('tag')
            self.src = kwargs.get('src')

    def _correct_cf_tag(self):
        """
        Correct <cf> tag to <la> or <gr>.
        """
        if self.tag == 'cf' and self.text:
            if GRAMMAR_LIKE.search(self.text):
                self.tag = 'gr'
            elif LABEL_LIKE.search(self.text):
                self.tag = 'la'


def _modify_node(node):
    for vd_range in node.findall('.//vdRange'):
        dates = []
        for vd_node in vd_range.findall('./vd'):
            date = vd_node.get('date') or vd_node.text
            dates.append(date)
        if len(dates) == 1 and re.search(r'^[a-zA-Z0-9]+$', dates[0]):
            new_vd = etree.Element('vd', date=dates[0] + '-')
        elif len(dates) == 2:
            new_vd = etree.Element('vd', date=dates[0] + '-' + dates[1])
        elif dates:
            new_vd = etree.Element('vd', date=dates[0])
        else:
            new_vd = etree.Element('vd', date='null')
        new_vd.tail = vd_range.tail
        vd_range.getparent().replace(vd_range, new_vd)
    return node

def _handle_tail(tail):
    tail_nodes = []
    if tail is not None:
        src = tail
        for word in ('also', 'Also', 'and', 'etc.', 'etc', '&amp;', '&'):
            tail = tail.replace(word, '')
        tail = tail.replace(',', '').strip()
        tail = GREEK_LETTERS_PATTERN.sub(':', tail)
        tail = re.sub(r'([();:]|Forms)', r'#\1#', tail)
        for token in tail.split('#'):
            token = re.sub(r'^[ .,?-]+|[ ,?-]+$', '', token)
            tag = None
            if token == ';' or token == ':':
                tag = 'softBreak'
            elif token == 'Forms':
                tag = 'newStart'
            elif token.lower() in PERIOD_MAP:
                tag = 'vd'
                token = PERIOD_MAP[token.lower()]
            elif token == '(':
                tag = 'openParen'
            elif token == ')':
                tag = 'closeParen'
            elif token:
                tag = 'text'
            if tag is not None:
                tail_nodes.append(VfsectLooseNode(tag=tag, text=token, src=src))
    return tail_nodes

def _build_vflist(elements):
    # Iterate through the list of elements, keeping track of state, and
    #   for each vf element create a VariantForm object based on current
    #   state (the set of dates and grammar information governing the vf).

    # 'state' is used to keep track of state:

    # state['outside'] keeps track of the main state, i.e. state outside
    #  parens. Includes:
    #   -- last encountered date-range;
    #   -- last encountered grammar information (<gr>);
    #   -- last encountered label (<la>).

    # state['inside'] keeps track of the state inside parens.
    #  Includes:
    #   -- last encountered date-range;
    #   -- last encountered grammar information (<gr>);
    #   -- last encountered label (<la>).
    #  This is cleared every time we hit a closing paren.

    # state['parens'] keeps track of whether we're inside or outside
    #  parens (value is 'inside' or 'outside').

    # Each time a <vf> is encountered, a VariantForm is created
    #  for it using information from the current state. Usually this is
    #  state['outside']. Values from state['inside'] are only used if the
    #  <vf> is inside parens (i.e. state['parens'] == 'inside') *and* the
    #  value of state['inside'] is populated; otherwise, the corresponding
    #  value from state['outside'] is used by default.

    # All __state is cleared every time we reach a hard break (e.g. a para).

    vf_list = []
    state = StateMachine()
    for element in elements:
        element = _adjust_element(element, state)
        if element.tag == 'vf':
            date_start, date_end = state.read('date_range')
            if not date_start:
                date_start, date_end = state.read('date_range',
                                                  paren_state='outside')
            grammar = (state.read('grammar') or
                       state.read('grammar', paren_state='outside'))
            label = (state.read('label') or
                     state.read('label', paren_state='outside'))
            variant_form = VariantFormFromParser(element.node,
                                                 date_start,
                                                 date_end)
            variant_form.set_grammatical_information(grammar)
            variant_form.label = label
            vf_list.append(variant_form)
        elif element.tag == 'vd':
            state.set('date_range', utilities.find_range(element.text))
            if element.previous != 'la':
                state.set('label', '')
        elif element.tag == 'hardBreak' or element.tag == 'p':
            state.clear()
        elif element.tag == 'softBreak':
            state.set('parens', 'outside')
            state.set('label', '')
        elif element.tag == 'openParen' and element.next != 'vf':
            state.set('parens', 'inside')
            # Make sure that grammar and date-range inside parens are set to null
            state.set('grammar', '')
            state.set('label', '')
            state.set('date_range', (0, 0))
        elif element.tag == 'closeParen':
            state.set('parens', 'outside')
        elif ((element.tag == 'gr' or element.tag == 'text') and
              element.text and
              not IGNORABLE_GRAMMAR_PATTERN.search(element.text)):
            state.set('grammar', element.text)
        elif element.tag == 'la':
            state.set('label', element.text)
        elif element.tag == 'newStart':
            vf_list = []
            state.clear()

    return vf_list

def _adjust_element(element, state):
    if element.text == 'pple.':
        match = re.search(r'(pa\.|past) tense', state.read('grammar'))
        if match is not None:
            element.text = '%s %s' % (match.group(1), element.text)
    if (element.text == 'pl.' and
        re.search(r'(pa\.|past) tense', state.read('grammar'))):
        element.text = ''
    return element


class StateMachine(object):

    """
    System for maintaining state information as we parse through an
    unrevised forms list (<vfSectLoose>).

    This keeps track of whether we're inside or outside parentheses.

    It also keeps track of:
     -- the last date range encountered;
     -- the last grammatical information encountered;
     -- the last label encountered.
    Two versions of this information are maintained: one for outside
    parentheses ('outside'), the other for inside parentheses ('inside').
    This means that once a pair of parentheses have been closed,
    we can revert to using the 'outside' version again.
    """

    def __init__(self):
        self.__parens = None
        self.__state = None
        self.clear()

    def clear(self):
        """
        Clear the state machine.

        We hit this every time we encounter a semicolon or similar.
        """
        self.__parens = 'outside'
        self.__state = {
            'outside': {'date_range': (0, 0), 'grammar': '', 'label': ''},
            'inside': {'date_range': (0, 0), 'grammar': '', 'label': ''}
        }

    def read(self, att, paren_state=None):
        """
        Read a current value from the state machine.
        """
        if att == 'parens':
            return self.__parens
        else:
            if paren_state is None:
                paren_state = self.__parens
            try:
                return self.__state[paren_state][att]
            except KeyError:
                return None

    def set(self, att, value):
        """
        Set a new value in the state machine.
        """
        if att == 'parens':
            self.__parens = value
        else:
            self.__state[self.__parens][att] = value
