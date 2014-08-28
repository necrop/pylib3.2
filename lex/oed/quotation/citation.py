"""
Citation - OED citation class (citation details for a quotation).

@author: James McCracken
"""

import re
from lxml import etree

from lex.oed.oedcomponent import OedComponent
from lex.oed.quotation.renderbibdetails import renderbibdetails

# Used to help spot dictionary quotations
GLOSSLIKE = ('Dict.', 'Gloss.', 'Lexicon', 'Word-bk.',
             'World of Words', 'N.E.D.')

# Used to help spot newspaper quotations
NEWSPAPER_NAMES = {'Herald', 'Times', 'Star', 'Daily', 'Morning',
                   'Evening', 'Echo', 'Post', 'Telegraph',
                   'Recorder', 'Sentinel', 'Guardian', 'Mail',
                   'Gaz.', 'Saturday', 'Sunday', 'Tel.', 'Inquirer',
                   'Sun', 'Mercury', 'Advertiser', 'Gazette'}


class Citation(OedComponent):

    """
    OED citation class.
    """

    def __init__(self, node):
        if node is None:
            node = etree.Element('cit')
        OedComponent.__init__(self, node)
        self._year = None

    #===============================================================
    # Date-related functions
    #===============================================================

    @property
    def year(self):
        """
        Return the quotation date, as an integer.

        By default, this is taken from the value of the dorder attribute,
        not from the text of the <d> element.
        """
        if self._year is None:
            self._year = _parse_year(self.node)
        return self._year

    @property
    def date(self):
        return self.year

    @property
    def date_qualifier(self):
        """
        Return the date qualifier ('a', 'c', '?a', '?c'), if any.

        Returns None if the date has no qualifier.
        """
        return _parse_date_qualifier(self.node.find('./d'))

    @property
    def datestring(self):
        """
        Return the human-readable string for the date
        (including 'a', 'c', etc., if any).
        """
        return _compose_datestring(self.node.find('./d'))

    @property
    def composition_datestring(self):
        """
        Return the human-readable string for the composition date
        (including 'a', 'c', etc., if any).

        Returns an empty string if there's no composition date.
        """
        return _compose_datestring(self.node.find('./dc'))

    @property
    def publication_datestring(self):
        """
        Return the human-readable string for the publication date
        (including 'a', 'c', etc., if any).

        Returns an empty string if there's no publication date.
        """
        return _compose_datestring(self.node.find('.//dp'))

    #===============================================================
    # Bibliographic details
    #===============================================================

    @property
    def bibsub(self):
        """
        Return the <bibSub> node.
        """
        return self.node.find('./bibSub')

    @property
    def bibmain(self):
        """
        Return the <bibMain> node.
        """
        return self.node.find('./bibMain')

    def author(self, **kwargs):
        """
        Return the first author name.

        Include the argument 'full=True' to return the full form
        of the author name.
        """
        if not self.author_forms():
            return None
        elif kwargs.get('full') and len(self.author_forms()) > 1:
            return self.author_forms()[1]
        else:
            return self.author_forms()[0]

    def title(self, **kwargs):
        """
        Returns the title.

        Include the argument 'full=True' to return the full form of the title
        """
        if not self.title_forms():
            return None
        elif kwargs.get('full') and len(self.title_forms()) > 1:
            return self.title_forms()[1]
        else:
            return self.title_forms()[0]

    def citation_signature(self):
        """
        Return a simple author + title text version of the citation.
        """
        sig = ''
        if self.author():
            sig += self.author() + ' '
        if self.title():
            sig += '_%s_' % self.title()
        return sig.strip()

    def author_forms(self):
        try:
            self._author_forms
        except AttributeError:
            self._author_forms = []
            if self.bibsub is not None:
                anode = self.bibsub.find('.//a')
            elif self.bibmain is not None:
                anode = self.bibmain.find('.//a')
            if anode is not None:
                self._author_forms.append(anode.text)
                if anode.get('ch_fullAuthor') is not None:
                    self._author_forms.extend(
                        anode.get('ch_fullAuthor').split('|'))

            # Add versions without quote marks (for G. Eliot, etc.)
            authorset = set(self._author_forms)
            additional_set = set()
            for a in authorset:
                a_unquoted = a.replace("'", "").replace('\u2018', '').replace('\u2019', '')
                if a_unquoted not in authorset:
                    additional_set.add(a_unquoted)
            self._author_forms.extend(list(additional_set))

        return self._author_forms

    def title_forms(self):
        try:
            self._title_forms
        except AttributeError:
            self._title_forms = []
            if self.bibmain is not None:
                tnode = self.bibmain.find('.//w')
                if tnode is not None:
                    text = etree.tounicode(tnode, method='text')
                    self._title_forms.append(text)
                    if tnode.get('ch_fullTitle') is not None:
                        self._title_forms.extend(
                            tnode.get('ch_fullTitle').split('|'))
        return self._title_forms

    @property
    def edition(self):
        """
        Return the text of any edition statement (<edn>) in the citation
        (usually appears bracketed following the main title).
        E.g. 'rev. ed.'
        """
        if self.bibmain is not None:
            edn_node = self.bibmain.find('./edn')
        else:
            edn_node = None
        if edn_node is not None:
            return edn_node.text
        else:
            return None

    #========================================================
    # Test various properties/characteristics of the citation
    #========================================================

    def contains(self, **kwargs):
        """
        Return True if the citation matches any of the list of authors
        and/or titles passed as keyword arguments.
        """
        authors = kwargs.get('authors', [])
        titles = kwargs.get('titles', [])
        authors_matched = [a for a in authors if a in self.author_forms()]
        titles_matched = [t for t in titles if t in self.title_forms()]
        if ((authors_matched or not authors) and
                (titles_matched or not titles)):
            return True
        else:
            return False

    citation_matches = contains

    def is_glossary(self):
        """
        Return True if the quotation appears to be from a
        dictionary or glossary.
        """
        if not self.title():
            return False
        for word in GLOSSLIKE:
            if word in self.title():
                return True
        return False

    def is_newspaper(self):
        """
        Return True if the quotation appears to be from a newspaper.
        """
        if self.author() is not None:
            return False
        if self._citation() is None or self.title() is None:
            return False
        if self._citation().find('.//place') is not None:
            return True
        if self._citation().find('.//di')is not None:
            date = self._citation().find('.//di').text
            if date and re.search(r'^[123]?[0-9] [A-Z]', date):
                tokens = self.title().split()
                if any([token in NEWSPAPER_NAMES for token in tokens]):
                    return True
        return False

    def is_modernized_text(self):
        """
        Return True if this is a marked as being modernized text
        """
        text = etree.tounicode(self.node, method='text')
        return 'modernized text' in text.lower()

    def is_electronic_text(self):
        """
        Return True if this is a marked as being electronic text
        """
        text = etree.tounicode(self.node, method='text')
        return 'electronic text' in text.lower()

    def is_title_quotation(self):
        """
        Return true if the quotation is the title of the text
        (i.e. citation contains <tt>title</tt>)
        """
        if self.bibmain is not None:
            tt_node = self.bibmain.find('.//tt')
            if tt_node is not None and tt_node.text == 'title':
                return True
        return False

    def is_translation(self):
        """
        Return true if this is a translation
        """
        if (self.bibmain is not None and
                self.bibmain.find('tr') is not None):
            return True
        if (self.bibsub is not None and
                self.bibsub.find('tr') is not None):
            return True
        return False

    #========================================================
    # HTML or plain-text renderings of the full citation
    #========================================================

    @property
    def html(self):
        """
        Return a HTML rendering of the citation
        """
        return self._render('html')

    @property
    def html_lite(self):
        """
        Return a 'light' HTML rendering of the citation - using
        <i>, <b>, and <sc> instead of <cite>, <span style="...">, etc.
        """
        return self._render('html_lite')

    @property
    def plaintext(self):
        """
        Return a plain-text rendering of the citation
        """
        return self._render('plaintext')

    def _render(self, method):
        _citstring = ''
        if self.datestring:
            if method == 'html':
                _citstring += '<strong>' + self.datestring + '</strong> '
            elif method == 'html_lite':
                _citstring += '<b>' + self.datestring + '</b> '
            else:
                _citstring += self.datestring + ' '
        if self.composition_datestring:
            _citstring += '(' + self.composition_datestring + ') '
        if self.bibsub is not None:
            _citstring += renderbibdetails(self.bibsub, method) + ' in '
        if self.bibmain is not None:
            _citstring += renderbibdetails(self.bibmain, method)
        return _citstring


def _parse_year(node):
    date_node = node.find('./d')
    if date_node is not None:
        year_string = date_node.get('dorder', '')
    else:
        year_string = ''
    match = re.search(r'(\d+)', year_string)
    if match:
        num_string = match.group(1)
        if len(num_string) == 6:
            year = num_string[:4]
        elif len(num_string) == 4:
            year = num_string
        else:
            year = 0
    else:
        year = 0
    return int(year)


def _parse_date_qualifier(node):
    if node is not None:
        qualifier = node.get('type', None)
        if qualifier:
            qualifier = qualifier.replace('q', '?')
        return qualifier
    else:
        return None


def _compose_datestring(node):
    if node is not None:
        _year_string = node.text
        qualifier = _parse_date_qualifier(node)
        if qualifier:
            _year_string = qualifier + _year_string
    else:
        _year_string = ''
    return _year_string
