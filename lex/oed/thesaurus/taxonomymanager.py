"""
TaxonomyManager -- Manager for the Historical Thesaurus taxonomic tree.

@author: James McCracken
"""

import os
from lxml import etree  # @UnresolvedImport

from lex import lexconfig
from lex.oed.thesaurus.thesaurusclass import ThesaurusClass

PARSER = etree.XMLParser(remove_blank_text=True)
DEFAULT_PATH = lexconfig.HTOED_TAXONOMY_DIR


class TaxonomyManager(object):

    """
    Manager for the Historical Thesaurus taxonomic tree
    """

    def __init__(self, **kwargs):
        self.levels = kwargs.get('levels', None)
        self.path = kwargs.get('dir', DEFAULT_PATH)
        self.verbosity = kwargs.get('verbosity', None)
        self.fix_ligatures = kwargs.get('fixLigatures', True)
        self.lazyload = kwargs.get('lazy', False)
        self._file = None
        self._classmap = None
        self._load_data()

    def files(self):
        """
        Return the list of files that will be processed.
        """
        if self._file is None:
            if isinstance(self.path, list):
                self._file = self.path[:]
            elif os.path.isfile(self.path) and self.path.endswith('.xml'):
                self._file = [self.path, ]
            elif os.path.isdir(self.path):
                self._file = [os.path.join(self.path, fname) for fname in
                              os.listdir(self.path)]
            else:
                self._file = []
            self._file = [f for f in self._file if self._filecheck(f)]
        return self._file

    def _filecheck(self, fname):
        """
        Check whether a given file is usable -- return True if so,
        otherwise return False.
        """
        if fname.lower().endswith('.xml'):
            return True
        else:
            return False

    def file_count(self):
        """
        Return the number of files to be processed.
        """
        return len(self.files())

    def _load_data(self):
        """
        Load the XML data into memory as a list of ThesaurusClass instances.
        """
        self.classes = []
        for filename in self.files():
            if self.verbosity is not None:
                print('Reading %s...' % filename)
            if self.lazyload:
                for line in open(filename, 'r'):
                    line = line.strip('\n\t ')
                    if line.startswith('<class'):
                        if not line.endswith('</class>'):
                            line += '</class>'
                        thesaurus_class = ThesaurusClass(line)
                        if (self.levels is None or
                                thesaurus_class.level() <= self.levels):
                            self.classes.append(thesaurus_class)
            else:
                tree = etree.parse(filename, PARSER)
                for cnode in tree.findall('class'):
                    thesaurus_class = ThesaurusClass(cnode)
                    if (self.levels is None or
                            thesaurus_class.level() <= self.levels):
                        self.classes.append(thesaurus_class)
        self._classmap = {c.id(): c for c in self.classes}

    def find_class(self, class_id):
        """
        Return a particular class from the taxonomy, identified by its ID.

        Returns a ThesaurusClass instance, or None if the IDis not found.
        """
        try:
            class_id = int(class_id)
        except TypeError:
            return None
        try:
            return self._classmap[class_id]
        except KeyError:
            return None

    def children_of(self, class_id):
        """
        Return the list of immediate child classes of the class
        specified by the ID supplied.

        Returns a list of ThesaurusClass instances.
        """
        return [c for c in self.classes if c.parent() == class_id]

    def descendants_of(self, class_id):
        """
        Return a list of all descendants of the class
        specified by the ID supplied.

        Returns a list of ThesaurusClass instances.

        Non-inclusive, i.e. does not include the present class itself.
        """
        return [c for c in self.classes if c.id() != class_id and
                class_id in c.path()]

    def total_size(self):
        """
        Return the total size of the taxonomy (number of instances).
        """
        return sum([c.size(branch=True) for c in self.classes
                    if c.level() == 1])