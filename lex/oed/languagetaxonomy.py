"""
LanguageTaxonomy -- Class for managing the OED's language taxonomy.

@author: James McCracken
"""

from lxml import etree  # @UnresolvedImport

from lex import lexconfig

TAXONOMY_FILE = lexconfig.OED_LANGUAGE_TAXONOMY


class LanguageTaxonomy(object):

    """
    Class for managing the OED's language taxonomy.
    """

    taxonomy = None
    taxonomy_map = {}

    def __init__(self):
        self._load_taxonomy()
        self.families = set()

    def languages(self):
        """
        Return the list of all languages in the taxonomy.

        Returns a list of Language objects.
        """
        return LanguageTaxonomy.taxonomy

    def node(self, language=None, id=None):
        if language is not None:
            try:
                return self.taxonomy_map[language.lower()]
            except KeyError:
                return None
        elif id is not None:
            for record in self.languages():
                if record.id == id:
                    return record
        return None

    def root_of(self, language):
        try:
            return self.taxonomy_map[language.lower()].root()
        except KeyError:
            return None

    def parent_of(self, language):
        try:
            return self.taxonomy_map[language.lower()].parent()
        except KeyError:
            return None

    def children_of(self, language):
        try:
            return self.taxonomy_map[language.lower()].children()
        except KeyError:
            return []

    def family_of(self, language):
        if self.families:
            try:
                lang = self.taxonomy_map[language.lower()]
            except KeyError:
                return None
            else:
                if lang.name in self.families:
                    return lang
                for ancestor in lang.ancestors:
                    if ancestor.name in self.families:
                        return ancestor
                return None
        else:
            return self.root_of(language)

    def _load_taxonomy(self):
        if LanguageTaxonomy.taxonomy is not None:
            return
        LanguageTaxonomy.taxonomy = []
        tree = etree.parse(TAXONOMY_FILE)
        language_nodes = tree.findall('.//class')
        LanguageTaxonomy.taxonomy = [Language(node) for node in
                                     language_nodes]

        LanguageTaxonomy.taxonomy_map = {l.name.lower(): l for l in
                                         LanguageTaxonomy.taxonomy}

        for node in language_nodes:
            name = node.findtext('./name')
            lang = LanguageTaxonomy.taxonomy_map[name.lower()]
            lang.ancestors = self._compile_ancestors(node)

    def _compile_ancestors(self, node):
        ancestors = []
        pnode = node.getparent()
        while pnode is not None:
            if pnode.tag == 'class':
                name = pnode.findtext('./name')
                plang = LanguageTaxonomy.taxonomy_map[name.lower()]
                ancestors.append(plang)
            pnode = pnode.getparent()
        return ancestors


class Language(object):

    """
    Class for an individual language within the taxonomy.
    """

    def __init__(self, node):
        self.name = node.findtext('./name')
        self.id = int(node.get('id').replace('etymonLanguage', ''))
        self.ancestors = []

    def parent(self):
        """
        Return the immediate parent language.

        Returns a Language object or None.
        """
        try:
            return self.ancestors[0]
        except IndexError:
            return None

    def root(self):
        """
        Return the top-level parent language (or itself, if this
        language has no parent)

        Returns a Language object.
        """
        try:
            return self.ancestors[-1]
        except IndexError:
            return self

    def children(self):
        """
        Return the immediate child languages of this language.

        Returns a list of Language objects (or an empty list, if
        no children).
        """
        return [l for l in LanguageTaxonomy.taxonomy if l.parent() == self]
