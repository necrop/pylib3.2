"""
SemanticComponent -- Base class for ODE/NOAD entries and wordclass blocks.

@author: James McCracken
"""

from lex.odo.odecomponent import OdeComponent
from lex.odo.sense import Sense


class SemanticComponent(OdeComponent):

    """
    Base class for ODE/NOAD entries and wordclass blocks.
    """

    def __init__(self, node):
        OdeComponent.__init__(self, node)

    def senses(self):
        try:
            return self._senses
        except AttributeError:
            self._senses = [Sense(node, i) for i, node in
                            enumerate(self.node.findall('.//msDict'))]
            return self._senses

    def morphgroups(self):
        try:
            return self._morphgroups
        except AttributeError:

            # Basic set of MorphGroups produced by appending MorphGroups
            #  from each sense
            self._morphgroups = []
            for sense in self.senses():
                self._morphgroups.extend(sense.morphgroups())

            # For each MorphGroup, increment its score every time it's
            # referenced from another (empty) morphSet
            for sense in self.senses():
                for morphset in sense.morphsets():
                    if not morphset.is_empty():
                        continue
                    for morphgroup in self._morphgroups:
                        if morphgroup.parent_id == morphset.reference():
                            if sense.is_first_sense():
                                morphgroup.score += 3
                            elif sense.type() == 'core':
                                morphgroup.score += 2
                            else:
                                morphgroup.score += 1

            # Deduplicate (shouldn't be necessary, but just in case...)
            morphgroups_uniq = []
            uniqed = {}
            for morphgroup in self._morphgroups:
                if morphgroup.signature in uniqed:
                    uniqed[morphgroup.signature] = uniqed[morphgroup.signature] + morphgroup.score
                else:
                    morphgroups_uniq.append(morphgroup)
                    uniqed[morphgroup.signature] = 0
            self._morphgroups = morphgroups_uniq

            # Take the score from any MorphGroup that's been thrown away in
            # deduplication, and add to the remaining morphGroup's score
            for morphgroup in self._morphgroups:
                morphgroup.score += uniqed[morphgroup.signature]

            # Reverse sort by score
            self._morphgroups.sort(key=lambda morphgroup: morphgroup.score)
            self._morphgroups.reverse()

            return self._morphgroups

