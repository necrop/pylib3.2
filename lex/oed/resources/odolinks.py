"""
OdoLinks - extract OED->ODO links from GEL
"""

import os
import string
from collections import defaultdict

from lxml import etree

from lex.gel.dataiterator import OedContentIterator
from lex.entryiterator import EntryIterator
from lex import lexconfig

OED_DIR = lexconfig.OEDLATEST_TEXT_DIR
GEL_DIR = lexconfig.GEL_DATA_DIR
DEFAULT_LINKS = lexconfig.OED_LINKS_DIR
LETTERS = string.ascii_lowercase


class OdoLinks(object):

    def __init__(self, **kwargs):
        self.oed_dir = kwargs.get('oed_dir') or OED_DIR
        self.gel_dir = kwargs.get('gel_dir') or GEL_DIR
        self.out_dir = kwargs.get('out_dir') or DEFAULT_LINKS
        self.links = None

    def store_links_data(self):
        self._load_links_from_gel()
        for letter in LETTERS:
            print('Collecting links in %s...' % letter.upper())
            file_filter = 'oed_%s.xml' % letter.upper()
            iterator = EntryIterator(path=self.oed_dir,
                                     dictType='oed',
                                     fixLigatures=True,
                                     fileFilter=file_filter,
                                     verbosity=None)

            self.tree = etree.Element('entries')
            for entry in iterator.iterate():
                self.tree.append(self._build_node(entry))
            self._write_output(letter)

    def _build_node(self, entry):
        entry_node = etree.Element('e', xrid=entry.id)
        hw_node = etree.SubElement(entry_node, 'label')
        hw_node.text = entry.label()
        links_node = etree.SubElement(entry_node, 'links')
        for target_dict in ('ode', 'noad'):
            if target_dict in self.links[entry.id]:
                links_node.set(target_dict,
                               self.links[entry.id][target_dict])

    def _write_output(self, letter):
        with open(os.path.join(self.out_dir,
                               letter + '.xml'), 'w') as filehandle:
            filehandle.write(etree.tounicode(self.tree,
                                             pretty_print=True))

    def _load_links_from_gel(self):
        self.links = defaultdict(dict)
        gel_iterator = OedContentIterator(in_dir=self.gel_dir,
                                          include_entries=True,
                                          include_subentries=False)
        for wcs in gel_iterator.iterate():
            oed_id = wcs.link(target='oed', defragment=True)
            for target_dict in ('ode', 'noad'):
                if wcs.link(target=target_dict) is not None:
                    self.links[oed_id][target_dict] = wcs.link(target=target_dict)


if __name__ == "__main__":
    OdoLinks().store_links_data()
