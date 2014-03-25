"""
WordclassBlock --ODE/NOAD wordclass block (<se1>)

@author: James McCracken
"""

from lex.odo.semanticcomponent import SemanticComponent
from lex.wordclass.wordclass import Wordclass


class WordclassBlock(SemanticComponent):
    """
    ODE/NOAD <se1> (wordclass/p.o.s. block) class.
    """

    def __init__(self, node):
        SemanticComponent.__init__(self, node)

    @property
    def wordclass(self):
        try:
            return self._wordclass
        except AttributeError:
            node = self.node.find('./posg/pos')
            if node is not None:
                val = node.get('value')
                if val == 'noun' and node.get('qualifier') == 'plural':
                    val = 'plural noun'
                if val == 'abbreviation':
                    val = _deduce_from_morphunits(self.node)
                self._wordclass = Wordclass(val).penn
            else:
                self._wordclass = 'NP'
            return self._wordclass


def _deduce_from_morphunits(node):
    for morph_unit in node.findall('.//morphUnit'):
        if morph_unit.get('pos') == 'NNP' or morph_unit.get('pos') == 'NN':
            return morph_unit.get('pos')
    return 'NN'  # best guess if all else has failed
