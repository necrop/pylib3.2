"""
Distiller -- Create and read a distilled version of ODE or NOAD

@author: James McCracken
"""

from collections import namedtuple
import pickle

from lex import lexconfig
from lex.entryiterator import EntryIterator

FILEPATHS = {'ode': lexconfig.ODE_DISTILLED, 'noad': lexconfig.NOAD_DISTILLED}

Entry = namedtuple('Entry', ['lexid', 'headword', 'headword_us', 'date',
                             'wordclass_blocks', 'subentries'])
WordclassBlock = namedtuple('WordclassBlock', ['wordclass', 'definition',
                                               'is_truncated', 'morphgroups',
                                               'complement'])
MorphGroup = namedtuple('MorphGroup', ['wordclass', 'variant_type',
                                       'score', 'morphunits'])
MorphUnit = namedtuple('MorphUnit', ['form', 'wordclass'])
SubEntry = namedtuple('SubEntry', ['lexid', 'lemma', 'wordclass'])


class Distiller(object):

    """
    Create and read a distilled version of ODE or NOAD, suitable for
    use when generating GEL.

    Keyword arguments:
     -- dictName: 'ode' or 'noad'
     -- defLength: maximum length of definitions (number of characters).
            Only required when using Distiller to *generate* a distilled file.
    """

    def __init__(self, **kwargs):
        self.dict_name = kwargs.get('dictName', 'ode').lower()
        self.definition_length = int(kwargs.get('defLength', 1000))
        self.pickle_file = FILEPATHS[self.dict_name]
        self.entries = []
        self.entry_map = {}

    def distil(self):
        iterator = EntryIterator(dictType=self.dict_name)

        with open(self.pickle_file, 'wb') as filehandle:
            for entry in iterator.iterate():
                distilled = _parse_source_entry(entry, self.definition_length)
                if distilled.wordclass_blocks:
                    pickle.dump(distilled, filehandle)

    def load_distilled_file(self):
        self.entries = []
        with open(self.pickle_file, 'rb') as filehandle:
            while (1):
                try:
                    entry = pickle.load(filehandle)
                except EOFError:
                    break
                else:
                    self.entries.append(entry)
        self.entry_map = {e.lexid: e for e in self.entries}

    def entry_by_id(self, lexid):
        try:
            return self.entry_map[lexid]
        except KeyError:
            return None

    def headword_by_id(self, lexid):
        entry = self.entry_by_id(lexid)
        if entry is None:
            return None
        else:
            return entry.headword


def _parse_source_entry(entry, definition_length):
    wordclass_blocks = []
    for block in entry.wordclass_blocks():
        if block.wordclass is None or not block.morphgroups():
            continue
        definition = block.definition(definition_length)
        if not definition :
            continue
        def_truncation = block.definition_manager().is_truncated(definition_length)
        morphgroups = _parse_morphgroups(block.morphgroups())
        wcb = WordclassBlock(block.wordclass, definition, def_truncation,
                             morphgroups, block.paired_id())
        wordclass_blocks.append(wcb)

    subentries = [SubEntry(sub.lexid(), sub.lemma, sub.wordclass)
                  for sub in entry.subentries()]

    return Entry(entry.id, entry.headword, entry.headword_us,
                 entry.date(), wordclass_blocks, subentries)

def _parse_morphgroups(source):
    output = []
    for morphgroup in source:
        units = [MorphUnit(unit.form, unit.wordclass)
                 for unit in morphgroup.morphunits]
        output.append(MorphGroup(morphgroup.baseclass,
                                 morphgroup.variant_type,
                                 morphgroup.score,
                                 units))
    return output


def check_contents():
    test = Distiller(dictName='noad')
    test.load_distilled_file()
    for entry in test.entries:
        print(entry.headword, entry.date)
        for b in entry.wordclass_blocks:
            print('\t', b.wordclass, b.definition, b.complement)
            for mg in b.morphgroups:
                print('\t\t%s %d----------------' % (mg.variant_type, mg.score))
                for unit in mg.morphunits:
                    print('\t\t', unit.form, unit.wordclass)

