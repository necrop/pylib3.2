"""
OedFrequencyIterator -- iterates through the OED frequency files
"""

import string
import os

from lxml import etree  # @UnresolvedImport

import stringtools
from lex.frequencytable import FrequencyTable
from lex import lexconfig

DEFAULT_INPUT = lexconfig.OED_FREQUENCY_DIR
LETTERS = string.ascii_lowercase


class FrequencyIterator(object):

    """
    Iterate through each entry in the OED frequency files,
    yielding each entry in turn.
    """

    parser = etree.XMLParser(remove_blank_text=True)

    def __init__(self, **kwargs):
        self.in_dir = kwargs.get('inDir') or kwargs.get('in_dir') or DEFAULT_INPUT
        self.letters = kwargs.get('letters', None)
        self.verbosity = kwargs.get('verbosity', None)
        self.message = kwargs.get('message', None)
        if self.message is None and self.verbosity is not None:
            self.message = 'Processing frequency data'

    def iterate(self):
        for letter in string.ascii_lowercase:
            if self.letters and letter not in self.letters:
                continue
            if self.message:
                print('%s: %s...' % (self.message, letter,))
            files = [os.path.join(self.in_dir, letter, f) for f in
                     os.listdir(os.path.join(self.in_dir, letter))
                     if f.endswith('.xml')]
            files.sort()

            for filepath in files:
                basename = os.path.basename(filepath)
                doc = etree.parse(filepath, self.parser)
                for e in doc.findall('e'):
                    entry = FrequencyEntry(e)
                    entry.letter = letter
                    entry.filename = basename
                    yield entry


class EntryComponent(object):

    def __init__(self, node):
        self.node = node

    def has_frequency_table(self):
        return bool(self.frequency_table())

    def direct_frequency_table(self):
        try:
            return self._own_frequency_table
        except AttributeError:
            freq_node = self.node.find('./frequency')
            if freq_node is not None:
                self._own_frequency_table = FrequencyTable(node=freq_node)
            else:
                self._own_frequency_table = None
            return self._own_frequency_table

    def frequencies(self):
        if self.frequency_table():
            return self.frequency_table().frequencies()
        else:
            return None


class FrequencyEntry(EntryComponent):

    def __init__(self, node):
        EntryComponent.__init__(self, node)
        self.id = node.get('xrid')
        self.xrid = node.get('xrid')
        self.xrnode = node.get('xrnode')
        self.label = node.findtext('./label')
        self.parent_label = node.findtext('./parentLabel')
        self.lemma = node.findtext('./lemma')
        self.definition = node.findtext('./definition') or ''
        self.start = int(node.get('firstDate', 0))
        self.end = int(node.get('lastDate', 0))
        if node.get('obsolete') == 'True':
            self.obs = True
        else:
            self.obs = False
        if node.get('type') == 'entry':
            self.is_main_entry = True
        else:
            self.is_main_entry = False

    def is_obsolete(self):
        return self.obs

    def alphasort(self):
        return stringtools.lexical_sort(self.lemma)

    def wordclass_sets(self):
        try:
            return self._wordclass_sets
        except AttributeError:
            self._wordclass_sets = [WordclassSet(n) for n in
                                    self.node.findall('./wordclass')]
            return self._wordclass_sets

    def types(self):
        types_list = []
        for wordclass_set in self.wordclass_sets():
            types_list.extend(wordclass_set.types())
        return types_list

    def wordclass(self):
        try:
            return self.wordclass_sets()[0].wordclass
        except IndexError:
            return None

    def frequency_table(self):
        if self.direct_frequency_table():
            return self.direct_frequency_table()
        elif self.wordclass_sets():
            return self.wordclass_sets()[0].frequency_table()

    def todict(self, **kwargs):
        return {'ft': self.frequencies(),
                'wordclasses': [w.todict(**kwargs) for w in self.wordclass_sets()]}


class WordclassSet(EntryComponent):

    def __init__(self, node):
        EntryComponent.__init__(self, node)
        self.wordclass = self.node.get('penn', 'NN')

    def types(self):
        try:
            return self._types
        except AttributeError:
            self._types = [Type(node) for node in
                           self.node.findall('.types/type')]
            return self._types

    def frequency_table(self):
        if self.direct_frequency_table():
            return self.direct_frequency_table()
        elif self.types():
            return self.types()[0].frequency_table()

    def todict(self, **kwargs):
        return {'ft': self.frequencies(),
                'pos': self.wordclass,
                'types': [t.todict(**kwargs) for t in self.types()]}


class Type(EntryComponent):

    def __init__(self, node):
        EntryComponent.__init__(self, node)
        self.form = self.node.findtext('./form')
        self.wordclass = self.node.get('penn', 'NN')

    def frequency_table(self):
        return self.direct_frequency_table()

    def todict(self, **kwargs):
        mask_quotes = kwargs.get('mask_quotes', False)
        wordform = self.form
        if mask_quotes:
            wordform = wordform.replace('"', '.').replace("'", '.')
        return {'ft': self.frequencies(),
                'form': wordform, 'pos': self.wordclass}
