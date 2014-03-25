"""
FindMorelinks

@author: James McCracken
"""

import re
from collections import defaultdict, namedtuple

from lex.odo.linkmanager import LinkManager
from lex.odo.distiller import Distiller
from lex.entryiterator import EntryIterator
from lex.lemma import Lemma

COMPLEMENTS = {'ode': 'noad', 'noad': 'ode'}
LINK_MANAGERS = {dictname: LinkManager(dictName=dictname, includeAdditions=False)
                 for dictname in ('ode', 'noad')}
DISTILLERS = {dictname: Distiller(dictName=dictname)
              for dictname in ('ode', 'noad')}
OedData = namedtuple('OedData', ['id', 'headword', 'definition'])


class FindMoreLinks(object):

    def __init__(self):
        self.dictname = None
        self.oed_entries = []
        for dictname in ('ode', 'noad'):
            LINK_MANAGERS[dictname].parse_link_file()
            DISTILLERS[dictname].load_distilled_file()

    def complement(self):
        try:
            return COMPLEMENTS[self.dictname]
        except KeyError:
            return None

    def process(self, dictname):
        self.dictname = dictname
        if not self.oed_entries:
            self.oed_entries = _load_oed_entries()
        matches = []
        for entry in DISTILLERS[dictname].entries:
            if entry.wordclass == 'NP':
                headword = re.sub(r', .*$', '', entry.headword)
                headword = Lemma(headword).asciified()
                if headword in self.oed_entries:
                    for z in self.oed_entries[headword]:
                        j = '%s\t%s\t%s\t%s' % (entry.headword, entry.lexid, z.headword, z.id)
                        matches.append((j, entry.wordclass_blocks[0].definition, z.id))
        return matches

def _load_oed_entries():
    iterator = EntryIterator(dictType='oed', verbosity='low')
    oed_entries = defaultdict(list)
    for entry in iterator.iterate():
        headword = entry.lemma_manager().asciified()
        if (re.search(r'^[A-Z][a-z]', headword) and
                LINK_MANAGERS['ode'].translate_id(entry.id) is None):
            oed_entries[headword].append(OedData(entry.id,
                                                 entry.headword,
                                                 entry.definition(length=100)))
    return oed_entries
