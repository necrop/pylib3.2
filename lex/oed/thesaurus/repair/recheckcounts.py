import os
import re
from collections import defaultdict

from lex import lexconfig
from lex.oed.thesaurus.contentiterator import ContentIterator
from lex.oed.thesaurus.taxonomymanager import TaxonomyManager

CONTENT_DIR = lexconfig.HTOED_CONTENT_DIR
TAX_DIR = lexconfig.HTOED_TAXONOMY_DIR
CONTENT_DIR_TMP = os.path.join(lexconfig.HTOED_DIR, 'content_tmp')
TAX_DIR_TMP = os.path.join(lexconfig.HTOED_DIR, 'taxonomies_tmp')

ATTSTRING = ' numInstancesDirect="%d" numInstancesDescendant="%d">'


def recheck_counts():
    # Figure out the node sizes of all the individual classes
    node_sizes = defaultdict(int)
    iterator = ContentIterator(in_dir=CONTENT_DIR)
    for thesclass in iterator.iterate():
        node_sizes[thesclass.id()] = len(thesclass.instances())

    branch_sizes = {}
    cumulate = defaultdict(int)
    tree_manager = TaxonomyManager(dir=TAX_DIR, lazy=True, verbosity=None)
    levels = list(reversed(range(1, 20)))
    for level in levels:
        classes = [c for c in tree_manager.classes if c.level() == level]
        print(level, len(classes))
        for thesclass in classes:
            branch_sizes[thesclass.id()] = cumulate[thesclass.id()] + node_sizes[thesclass.id()]
        for thesclass in classes:
            cumulate[thesclass.parent()] += branch_sizes[thesclass.id()]

    iterator = ContentIterator(in_dir=CONTENT_DIR, out_dir=CONTENT_DIR_TMP)
    for thesclass in iterator.iterate():
        thesclass.node.set('numInstancesDirect', str(node_sizes[thesclass.id()]))
        thesclass.node.set('numInstancesDescendant', str(branch_sizes[thesclass.id()]))
        node_sizes[thesclass.id()] = len(thesclass.instances())

    for in_file in os.listdir(TAX_DIR):
        lines = []
        with open(os.path.join(TAX_DIR, in_file)) as filehandle:
            for line in filehandle:
                m = re.search('^[ \t]+<class id="(\d+)"', line)
                if m:
                    id = int(m.group(1))
                    additions = ATTSTRING % (node_sizes[id], branch_sizes[id])
                    line = re.sub('>', additions, line, count=1)
                lines.append(line)

        with open(os.path.join(TAX_DIR_TMP, in_file), 'w') as filehandle:
            filehandle.writelines(lines)


if __name__ == '__main__':
    recheck_counts()
