"""
Lemma -- Manager for a dictionary lemma (e.g. headword or sublemma)

@author: James McCracken
"""

import re
from collections import namedtuple

from lxml import etree

import stringtools
from regexcompiler import ReplacementListCompiler
from lex.inflections.inflection import Inflection

REGEXES = {
    'stress': re.compile('(\u02c8|\u02cc|\u2020)'),
    'unreverse': re.compile(r'^([^,]+), ([^,]+ (of|in|de|du|d\'|de la|von))$',
                            re.I),
    'phrasal': re.compile(r'^(not |)to .+ .'),
    'compound': re.compile(r'.[ ~-].'),
    'closed_compound': re.compile(r'.~.'),
    'initialism': re.compile(r'^([A-Z]{2,}|[A-Za-z]\.([A-Za-z]\.)+)$'),
}
WORDSPLIT_PATTERN = re.compile('(.)(~|-|\u2014)(.)')


class Lemma(object):

    """
    Lexical lemma (e.g. dictionary entry headword or sublemma).

    Argument should be either a string or an XML node; in the
    latter case, the immediate child text will be taken to be the lemma.
    """

    inflector = Inflection()

    def __init__(self, arg):
        # Test whether a node or a string has been passed in.
        # If a string, then self.node is set to None
        try:
            self.text = arg.text
            self.node = arg
        except AttributeError:
            self.text = arg
            self.node = None
        if self.text == None:
            try:
                self.text = etree.tostring(arg,
                                           method='text',
                                           encoding='unicode')
            except AttributeError:
                self.text = ''
        self.text = self.text.strip()
        self.lemma = _parse_lemma(self.text)

    def parenstripped(self):
        return self.lemma.replace('(', '').replace(')', '')

    lemma_parenstripped = parenstripped

    def hyphenstripped(self):
        return self.lemma.strip(' -')

    lemma_hyphenstripped = hyphenstripped

    def asciified(self):
        return stringtools.asciify(self.lemma)

    def lexical_sort(self):
        try:
            return self._lexical_sort
        except AttributeError:
            self._lexical_sort = stringtools.lexical_sort(self.lemma)
            return self._lexical_sort

    dictionary_sort = lexical_sort

    def length(self):
        return len(self.lexical_sort())


    #======================================================
    # Functions relating to substrings
    #======================================================

    def initial(self):
        return stringtools.initial(self.lexical_sort())

    def terminator(self):
        return stringtools.terminator(self.lexical_sort())

    def starts_with_vowel(self):
        """
        Return True if the first letter is a vowel.
        """
        return stringtools.is_vowel(self.initial())

    def ends_with_vowel(self):
        """
        Return True if the last letter is a vowel.
        """
        return stringtools.is_vowel(self.terminator())

    def prefix(self):
        return stringtools.prefix(self.lexical_sort(), 3)

    def suffix(self):
        return stringtools.suffix(self.lexical_sort(), 3)

    SliceTuple = namedtuple('SliceTuple', ['left', 'right'])

    def slices(self):
        try:
            return self._slices
        except AttributeError:
            lemma = re.sub(r'~', '', self.parenstripped())
            self._slices = [self.SliceTuple(Lemma(start), Lemma(end),)
                             for start, end in stringtools.bisect(lemma)]
            return self._slices


    #======================================================
    # Functions testing for various characteristics
    #======================================================

    def is_asterisked(self):
        if self.text.startswith('*'):
            return True
        else:
            return False

    def is_affix(self):
        if self.is_prefix() or self.is_suffix():
            return True
        else:
            return False

    def is_infix(self):
        if self.is_prefix() and self.is_suffix():
            return True
        else:
            return False

    def is_prefix(self):
        if self.lemma.endswith('-'):
            return True
        else:
            return False

    def is_suffix(self):
        if self.lemma.startswith('-'):
            return True
        else:
            return False

    def is_compound(self):
        if REGEXES['compound'].search(self.lemma):
            return True
        else:
            return False

    def is_closed_compound(self):
        if REGEXES['closed_compound'].search(self.lemma):
            return True
        else:
            return False

    def is_phrasal(self):
        if REGEXES['phrasal'].search(self.lemma):
            return True
        else:
            return False

    def is_initialism(self):
        if REGEXES['initialism'].search(self.lemma):
            return True
        else:
            return False

    def capitalization_type(self):
        try:
            return self._capitalization_type
        except AttributeError:
            tmp = self.asciified().replace('\'', '')
            tmp = re.sub(r'[ ~-]+', ' ', tmp)
            components = tmp.strip().split()
            if re.search(r'^[a-z]+$', components[0]):
                ctype = 'downcased'
            elif re.search(r'^[A-Z]([a-z]+)?$', components[0]):
                ctype = 'capitalized'
            elif re.search(r'^[A-Z][A-Z.]*$', components[0]):
                ctype = 'upcased'
            elif re.search(r'[a-z][A-Z]', components[0]):
                ctype = 'camelcased'
            else:
                ctype = 'mixed'
            if len(components) > 1:
                if (ctype == 'capitalized' and
                    re.search(r'^[a-z]+$', components[1])):
                    ctype = 'sentence-start'
                elif (ctype == 'downcased' and
                      re.search(r'[A-Z]', components[1])):
                    ctype = 'mixed'
                elif (ctype == 'upcased' and
                      re.search(r'^[a-z]$', components[1])):
                    ctype = 'mixed'
            self._capitalization_type = ctype
            return self._capitalization_type

    cap_type = capitalization_type


    def plurals(self):
        try:
            return self._plurals
        except AttributeError:
            self._plurals = self.inflector.pluralize(self.lemma)
            return self._plurals

    def words(self):
        try:
            return self._words
        except AttributeError:
            tmp = WORDSPLIT_PATTERN.sub(r'\1 \3', self.lemma)
            tmp = WORDSPLIT_PATTERN.sub(r'\1 \3', tmp).strip()
            self._words = tmp.split(' ')
            return self._words

    def num_words(self):
        """
        Return the number of space- or hyphen-separated words in
        the lemma.
        """
        return len(self.words())

    def decompose(self, base=None, break_affix=False):
        """
        Break the lemma into its constituent parts.

        The parts are returned as a list of one or more component strings
        """
        if base is not None and break_affix:
            base = base.strip('-')
        if self.num_words() > 1:
            return self.words()
        elif base is None or not base:
            return [self.lemma, ]
        elif self.lemma.startswith(base) and len(self.lemma) > len(base) + 3:
            return [base, self.lemma[len(base):], ]
        else:
            return [self.lemma, ]

    def abstract(self, level):
        return Abstractor().abstract(self.lexical_sort(), level)


def _parse_lemma(text):
    # Remove stress marks and initial asterisks
    destressed = REGEXES['stress'].sub('', text)
    destressed = destressed.strip(' *')

    # Unreverse proper names
    return REGEXES['unreverse'].sub(r'\2 \1', destressed)


class Abstractor(object):

    replacers = [
        ReplacementListCompiler(()),  # zero-index is dummy

        ReplacementListCompiler((
            (r'i(ck|k|qu)e?$', 'ic'),
            (r'(qw|qu|q)', 'k'),
            (r'([aeiouy])c(e|ie|y)', r'\1s\2'),
            (r'chr', 'cr'),
            (r'(sch|ssh|sh|zh|tch)', 'ch'),
            (r'(sc|sk)', 'ss'),
            (r'(y|ie)', 'i'),
            (r'wh', 'w'),
            (r'ph', 'f'),
            (r'th', 't'),
            (r'xc', 'x'),
            (r'(ck|kk)', 'k'),
            (r'(dg|gh|j)', 'g'),
            (r'[tcs][iy]o[uw]?([smnl])', r'tio\1'),
            (r'[mn]', 'm'),
            (r'([bdfglmnprstz])\1', r'\1'),)),  # consonant doubling

        # flatten vowels and vowel sequences
        ReplacementListCompiler((
            (r'[aeiouy]', '#'),
            (r'#+', '#'),)),

        # remove medial -e
        ReplacementListCompiler((
            (r'([bcdfghklmnprstwxz])e([bcdfghklmnprstwxz])', r'\1\2'),)),

        ReplacementListCompiler((
            (r'(ch|cc|c|k)', 'k'),
            (r'z', 's'),
            (r'(p|f|v)', 'f'),)),

        ReplacementListCompiler((
            (r'(v|u)', 'v'),
            (r'[aeo][uw]', 'aw'),
            (r'cc', 'ct'),
            (r'ble$', 'bile$'),  # -able to -abile, etc.
            ('([bcdfghklmnprstwxz])e$', r'\1'),  # terminal -e
            (r'(sh|s|c|z)', 's'),)),

        ReplacementListCompiler((
           (r'(ear|ere|ier|ire)', 'eer'),
           (r'(ea|ee|ie)([bdfgklmnpstxz])', r'ee\2'),
           (r'e([dklmnpstz])e', r'ee\1'),
           (r'(ei|ai|ay)([dklmnpstz])e?', r'ai\1'),
           (r'a([dklmnpstz])e', r'ai\1'),)),

        ReplacementListCompiler((
            (r'(ly|li|lic|lik|lich|lych)e?$', 'ly'),)),
    ]

    def __init__(self):
        pass

    def abstract(self, text, level=2):
        """Create an abstracted 'skeleton' version of the text.

        Useful for testing if two strings look like variant spellings of
        each other; in particular, it flattens all vowels and vowel sequences
        to '#', and uniqs all doubled consonants.

        This is fairly crude: it assumes that vowels can vary,
        but that consonants should stay the same.

        Returns a string.
        """
        level = int(level)
        for i, replacer in enumerate(self.replacers):
            text = replacer.edit(text)
            if i == level:
                break
        return text
