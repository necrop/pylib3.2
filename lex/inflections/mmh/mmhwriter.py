"""
mmhwriter - Generates and stores morphology hub as XML documents
"""

import re
import os
from collections import defaultdict

from lxml import etree

from lex import lexconfig
from lex.entryiterator import EntryIterator

WORDCLASS_PATTERN = re.compile(r'^(NN|NNS|JJ|RB|VB)$')
OUTPUT_DIR = lexconfig.MORPHOLOGY_DIR


class MmhWriter(object):

    def __init__(self):
        self.count = 0
        self.store = defaultdict(lambda: defaultdict(
            lambda: defaultdict(lambda: defaultdict(dict))))

    def load_morphgroups(self):
        iterator = EntryIterator(dictType='ode')
        for entry in iterator.iterate():
            for morphgroup in entry.morphgroups():
                if (WORDCLASS_PATTERN.search(morphgroup.baseclass) and
                        not morphgroup.variant_type == 'deprecated'):
                    self._process_morphgroup(morphgroup)

    def _process_morphgroup(self, morphgroup):
        target = self.store[morphgroup.initial()][morphgroup.lexical_sort()]\
            [morphgroup.lemma][morphgroup.baseclass]
        if not morphgroup.signature in target:
            target[morphgroup.signature] = morphgroup
        else:
            target[morphgroup.signature].score += morphgroup.score

    def write_morphgroups(self):
        for initial, letterset in self.store.items():
            doc = etree.Element('mmh')
            doc.set('initial', initial)
            doc.set('lang', 'EN')
            for lemmasort, lemmas in sorted(letterset.items()):
                for lemma, wordclasses in sorted(lemmas.items()):
                    entry_node = etree.Element('e')
                    hwg = etree.SubElement(entry_node, 'hwg')
                    hw = etree.SubElement(hwg, 'hw')
                    hw.text = lemma
                    for baseclass, sigset in wordclasses.items():
                        gramb = etree.Element('gramb')
                        nlp = etree.SubElement(gramb, 'nlp')
                        for sig, morphgroup in sigset.items():
                            mgnode = morphgroup.to_node()
                            mgnode.set('id', self._next_id())
                            nlp.append(mgnode)
                        entry_node.append(gramb)
                    doc.append(entry_node)

            fname = os.path.join(OUTPUT_DIR, initial + '.xml')
            with open(fname, 'w') as filehandle:
                filehandle.write(etree.tostring(doc,
                                                pretty_print=True,
                                                encoding='unicode'))

    def _next_id(self):
        self.count += 1
        return '%09d' % self.count


if __name__ == '__main__':
    writer = MmhWriter()
    writer.load_morphgroups()
    writer.write_morphgroups()
