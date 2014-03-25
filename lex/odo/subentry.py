"""
SubEntry -- ODE/NOAD subentry (derivative)

@author: James McCracken
"""

from lex.odo.semanticcomponent import SemanticComponent
from lex.wordclass.wordclass import Wordclass
from lex.lemma import Lemma


class SubEntry(SemanticComponent):

    """
    ODE/NOAD subentry class (<subEntry>).
    """

    def __init__(self, node):
        SemanticComponent.__init__(self, node)

    def lemma_manager(self):
        try:
            return self._lemma_object
        except AttributeError:
            self._lemma_object = Lemma(self.node.findtext('./l') or '')
            return self._lemma_object

    @property
    def lemma(self):
        return self.lemma_manager().lemma

    @property
    def wordclass(self):
        try:
            return self._wordclass
        except AttributeError:
            node = self.node.find('./posg/pos')
            if node is not None:
                self._wordclass = Wordclass(node.get('value')).penn
            else:
                self._wordclass = 'NP'
            return self._wordclass
