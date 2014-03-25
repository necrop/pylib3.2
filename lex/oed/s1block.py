"""
S1block -- OED <s1> block class

@author: James McCracken
"""

import copy

from lex.oed.multisensecomponent import MultiSenseComponent
from lex.lemma import Lemma


class _SenseContainer(MultiSenseComponent):

    """
    Base class for S1block and S2block
    """

    def __init__(self, node, headword, entry_id):
        MultiSenseComponent.__init__(self, node)
        self.id = entry_id
        self.entry_id = entry_id
        self._lemma_manager = Lemma(headword)
        self.first_sibling = None
        self.is_revised = False

    @property
    def lemma(self):
        return self.lemma_manager().lemma

    def lemma_manager(self):
        return self._lemma_manager

    def set_lemma(self, new_lemma_manager):
        self._lemma_manager = new_lemma_manager


class S1block(_SenseContainer):

    """
    OED <s1> block class.
    """

    def s2blocks(self):
        """
        Return a list of <s2> blocks (if any).
        """
        try:
            return self._s2blocks
        except AttributeError:
            self._s2blocks = [S2block(n, self.lemma, self.id)
                              for n in self.node.findall('./s2')]
            for block in self._s2blocks:
                block.is_revised = self.is_revised

            # If the entry is obsolete, then all blocks must be obsolete
            if self.is_marked_obsolete():
                for block in self._s2blocks:
                    block.set_obsolete_marker(True)
            return self._s2blocks


class S2block(_SenseContainer):

    """
    OED <s2> block class.
    """
    pass
