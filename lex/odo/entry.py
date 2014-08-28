"""
Entry -- ODE/NOAD dictionary entry

@author: James McCracken
"""

from lex.odo.semanticcomponent import SemanticComponent
from lex.odo.wordclassblock import WordclassBlock
from lex.odo.subentry import SubEntry
from lex.odo.etymology import Etymology
from lex.lemma import Lemma


class Entry(SemanticComponent):

    """
    ODE/NOAD dictionary entry class.
    """

    def __init__(self, node):
        SemanticComponent.__init__(self, node)
        self.id = self.attribute('lexid')

    def lemma_manager(self):
        """
        Return the lemma manager for the entry's headword.
        """
        try:
            return self._lemma_object
        except AttributeError:
            node = self.node.findtext('./hg/hw')
            if node is not None:
                self._lemma_object = Lemma(node,
                                           reversible=self.is_encyclopedic())
            else:
                self._lemma_object = Lemma('')
            return self._lemma_object

    @property
    def headword(self):
        return self.lemma_manager().lemma

    def is_encyclopedic(self):
        if self.node.get('type') == 'encyclopedic':
            return True
        else:
            return False

    def variant_group(self):
        try:
            return self._variant_group
        except AttributeError:
            self._variant_group = self.node.find('./hg/vg')
            return self._variant_group

    def us_lemma_manager(self):
        try:
            return self._us_lemma_object
        except AttributeError:
            self._us_lemma_object = Lemma('')
            if self.variant_group() is not None:
                region = self.variant_group().findtext('./lg/ge')
                form = self.variant_group().findtext('./v')
                if region in ('US', 'N. Amer.'):
                    self._us_lemma_object = Lemma(form)
            return self._us_lemma_object

    @property
    def headword_us(self):
        return self.us_lemma_manager().lemma

    def etymology(self):
        try:
            return self._etymology
        except AttributeError:
            node = self.node.find('./etym')
            if node is None:
                node = '<etym/>'
            self._etymology = Etymology(node)
            return self._etymology

    def date(self):
        try:
            return self._date
        except AttributeError:
            date = self.etymology().date() or None
            if (date is None and
                self.definition_manager().biodate() is not None and
                self.definition_manager().biodate() > 1200):
                date = self.definition_manager().biodate() + 20
            self._date = date
            return self._date

    def wordclass_blocks(self):
        try:
            return self._wordclass_blocks
        except AttributeError:
            self._wordclass_blocks = [WordclassBlock(n) for n in
                                      self.node.findall('./sg/se1')]
            return self._wordclass_blocks

    def subentries(self):
        try:
            return self._subentries
        except AttributeError:
            allsubs = [SubEntry(n) for n in self.node.xpath(
                       './subEntryBlock[@type="derivatives"]/subEntry')]
            self._subentries = [sub for sub in allsubs
                                if sub.lemma and sub.wordclass]
            return self._subentries
