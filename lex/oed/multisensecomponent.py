"""
Class for multi-sense OED components, e.g. entries or s1 blocks.

Author: James McCracken
"""

from collections import defaultdict

from lex.oed.semanticcomponent import SemanticComponent
from lex.oed.sense import Sense


class MultiSenseComponent(SemanticComponent):

    """
    Class for multi-sense OED components, e.g. entries or s1 blocks.
    """

    def __init__(self, node, **kwargs):
        SemanticComponent.__init__(self, node, **kwargs)

    def senses(self):
        try:
            return self._senses
        except AttributeError:
            self._senses = [Sense(n, self.lemma_manager(), self.id)
                            for n in
                            self.node.xpath('.//*[@senseUnit="true"]')]
            for sense in self._senses:
                sense.is_revised = self.is_revised
            # If the entry is obsolete, then all senses must be obsolete
            if self.is_marked_obsolete():
                for sense in self._senses:
                    sense.set_obsolete_marker(True)
        return self._senses

    def current_senses(self):
        return [s for s in self.senses() if not s.is_marked_obsolete()]

    def lemma_senses(self):
        return [s for s in self.senses() if
                s.primary_wordclass() and
                not s.lemma_manager().is_phrasal() and
                s.is_sublemma()]

    def lemma_senses_uniq(self):
        try:
            return self._lemma_senses_uniq
        except AttributeError:
            self._lemma_senses_uniq = []
            idx = {}
            for s in self.lemma_senses():
                if not s.lemma_manager().dictionary_sort in idx:
                    self._lemma_senses_uniq.append(s)
                    idx[s.lemma_manager().dictionary_sort] = \
                        len(self._lemma_senses_uniq) - 1
                else:
                    i = idx[s.lemma_manager().dictionary_sort]
                    self._lemma_senses_uniq[i].merge(s)
            return self._lemma_senses_uniq

    def share_quotations(self):
        """
        Check for senses which don't have a quotation paragraph,
        and determine if each should share the quotation paragraph
        of its following sibling (where the following sibling is
        the last in the set of sibling senses).
        """
        # Check if it's worth bothering; bail out if not
        if len(self.senses()) == 1:
            return
        if not any([s.tag in ('s4', 's6') and not s.quotation_paragraphs()
                    for s in self.senses()]):
            return

        siblings = defaultdict(list)
        count = 0
        last_node_id = 0
        for sense in [s for s in self.senses() if s.tag in ('s4', 's6')]:
            if sense.ancestors()[0].lexid != last_node_id:
                count += 1
            siblings[count].append(sense)
            last_node_id = sense.ancestors()[0].lexid
        for sibling_set in [sibling_set for sibling_set in siblings.values()
                            if len(sibling_set) > 1 and
                            sibling_set[-1].quotation_paragraphs() and
                            not sibling_set[-2].quotation_paragraphs()]:
            last_sense = sibling_set.pop()
            sibling_set.reverse()
            for sense in sibling_set:
                if sense.quotation_paragraphs():
                    break
                else:
                    sense.insert_quotations(last_sense.quotation_paragraphs())
