"""
Sense -- ODE/NOAD sense

@author: James McCracken
"""

from lex.odo.odecomponent import OdeComponent
from lex.odo.morphset import MorphSet, MorphGroup


class Sense(OdeComponent):

    """
    ODE/NOAD sense class.
    """

    def __init__(self, node, count):
        OdeComponent.__init__(self, node)
        self.entry_order = count

    def is_first_sense(self):
        if self.entry_order == 0:
            return True
        else:
            return False

    def type(self):
        return self.node.get('type', 'core')

    def morphsets(self):
        try:
            return self._morphsets
        except AttributeError:
            self._morphsets = [MorphSet(node) for node in
                               self.node.findall('./nlp/morphSet')]
            return self._morphsets

    def morphgroups(self):
        try:
            return self._morphgroups
        except AttributeError:
            self._morphgroups = []
            for morphset in self.morphsets():
                self._morphgroups.extend(morphset.morphgroups())
            for morphgroup in self._morphgroups:
                if self.is_first_sense():
                    morphgroup.score += 3
                elif self.type == 'core':
                    morphgroup.score += 2
                else:
                    morphgroup.score += 1
            return self._morphgroups

