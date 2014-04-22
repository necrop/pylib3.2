import os
from collections import defaultdict

from lxml import etree

from lex import lexconfig
from lex.oed.thesaurus.contentiterator import ContentIterator
from lex.oed.thesaurus.taxonomymanager import TaxonomyManager

CONTENT_DIR = lexconfig.HTOED_CONTENT_DIR
TAX_DIR = lexconfig.HTOED_TAXONOMY_DIR
CONTENT_DIR_TMP = os.path.join(lexconfig.HTOED_DIR, 'content_tmp')


def insert_child_nodes():
    """
    Copy child nodes from the taxonomy version of the data, and insert
    into the content version
    """
    tree_manager = TaxonomyManager(dir=TAX_DIR, lazy=True, verbosity=None)
    childmap = defaultdict(list)
    for thesclass in tree_manager.classes:
        if thesclass.parent():
            childmap[thesclass.parent()].append(thesclass)

    iterator = ContentIterator(in_dir=CONTENT_DIR, out_dir=CONTENT_DIR_TMP)
    for thesclass in iterator.iterate():
        if thesclass.id() in childmap:
            cn_node = etree.Element('childNodes')
            for child in childmap[thesclass.id()]:
                n = etree.SubElement(cn_node, 'node')
                n.set('idref', str(child.id()))
                n.set('numInstancesDescendant', str(child.size(branch=True)))
                if child.label():
                    n.text = child.label()
                if child.is_wordclass_level():
                    n.set('pos', child.wordclass())
            thesclass.node.append(cn_node)


if __name__ == '__main__':
    insert_child_nodes()
