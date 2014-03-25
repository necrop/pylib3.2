"""
OED entry class.

Author: James McCracken
"""

import re

from lxml import etree  # @UnresolvedImport

from lex.oed.multisensecomponent import MultiSenseComponent
from lex.oed.s1block import S1block
from lex.oed.etymology import Etymology
from lex.oed.variants.formslist import FormsList
from lex.lemma import Lemma

HWBRACKET_PATTERN = re.compile(r'^(.*)\((..?)$')
REVISED_PATTERN = re.compile(r'third edition', re.I)


class Entry(MultiSenseComponent):

    """
    OED entry class.
    """

    def __init__(self, node, **kwargs):
        MultiSenseComponent.__init__(self, node, **kwargs)
        self.id = self.attribute('id')

        # self.is_revised = False by default; set to 'True' if the
        #  publication info says "Third edition"
        pub_statement = self.node.findtext('./publicationInfo/pubStatement')
        if pub_statement is not None and REVISED_PATTERN.search(pub_statement):
            self.is_revised = True

    #====================================================
    # Headword-related functions
    #====================================================

    def headwords(self):
        """
        Return a list of all the headwords (as Lemma objects).
        """
        try:
            return self._headwords
        except AttributeError:
            self._headwords = [Lemma(n) for n in
                               self.node.findall('./hwSect/hw')]

            # If the headword contains internal bracketing, then we
            # uncompress this as two different headwords
            if (len(self._headwords) == 1 and
                HWBRACKET_PATTERN.search(self._headwords[0].text)):
                match = HWBRACKET_PATTERN.search(self._headwords[0].text)
                hw1 = etree.XML('<hw>%s</hw>' % match.group(1))
                hw2 = etree.XML('<hw>%s%s</hw>' % (match.group(1),
                                                   match.group(2)))
                self._headwords = [Lemma(hw1), Lemma(hw2)]
            return self._headwords

    def lemma_manager(self):
        """
        Return a Lemma object for the entry's (first) headword.
        """
        try:
            return self._lemma_object
        except AttributeError:
            try:
                self._lemma_object = self.headwords()[0]
            except IndexError:
                self._lemma_object = Lemma(etree.XML('<hw/>'))
            return self._lemma_object

    @property
    def headword(self):
        """
        Return the entry's headword.
        """
        return self.lemma_manager().lemma

    @property
    def lemma(self):
        """
        Return the entry's headword.
        """
        return self.lemma_manager().lemma

    def label(self, tagged=False):
        """
        Human-readable entry label, giving headword, part(s)-of-speech,
        and homograph number.

        Optional argument 'tagged':
         - False (default): gives homograph in slash form, e.g. 'march, n./1'
         - True: tags homograph in HTML <sup>, e.g. 'march, n.<sup>1</sup>'
        """
        parts_of_speech = []
        for ps_node in self.node.findall('./senseSect/s1/ps'):
            homograph_number = ps_node.get('hm', None)
            if homograph_number is None:
                pos = ps_node.get('type', 'n.')
            elif tagged:
                pos = '%s<sup>%s</sup>' % (ps_node.get('type', 'n.'),
                                           homograph_number)
            else:
                pos = '%s/%s' % (ps_node.get('type', 'n.'),
                                 homograph_number)
            pos = pos.replace('_', ' ')
            parts_of_speech.append(pos)
        if len(parts_of_speech) == 2:
            pos_string = '%s and %s' % tuple(parts_of_speech)
        elif len(parts_of_speech) == 3:
            pos_string = '%s, %s, and %s' % tuple(parts_of_speech)
        else:
            pos_string = ', '.join(parts_of_speech)
        return '%s, %s' % (' | '.join([hw.lemma for hw in self.headwords()]),
                           pos_string)

    def header(self):
        """
        Return the text of the entry-level header (if any).

        Return None if there's no entry-level header.
        """
        header_node = self.node.find('./senseSect/header')
        if header_node is not None:
            return etree.tostring(header_node,
                                  method='text',
                                  encoding='unicode')
        else:
            return None

    def lemsect_senses(self):
        """
        Return only senses in <lemSect>s, not main senses
        """
        return [s for s in self.senses() if s.is_in_lemsect()]

    def revsect_senses(self):
        """
        Return only senses in <lemSect>s, not main senses
        """
        return [s for s in self.senses() if s.is_in_revsect()]

    def quotations_main(self):
        """
        Return a list of quotation objects from the main senseSect.
        """
        try:
            return self.__quotations_main
        except AttributeError:
            self.__quotations_main = [q for q in self.quotations()
                                     if q.has_ancestor('senseSect')]
            return self.__quotations_main

    def num_quotations_main(self):
        """
        Return a count of quotations in the main senseSect.
        """
        return len(self.quotations_main())

    def etymology(self):
        """
        Return an Etymology object for this entry.

        This will be a dummy object if the entry has no etymology.
        """
        try:
            return self._etymology
        except AttributeError:
            node = self.node.find('./etymSect/etym')
            if node is None:
                node = '<etym/>'
            self._etymology = Etymology(node)
            self._etymology.is_revised = self.is_revised
            return self._etymology

    def variants(self):
        """
        Return a FormsList object containing a list of variant forms.

        This will be a dummy object if the entry has no forms list.
        """
        try:
            return self._variants
        except AttributeError:
            # If the entry has both a <vfSectLoose> and a <vfSect>, we prefer
            #  the former; the latter will have been computationally generated
            #  from the former, and not yet corrected, so is unreliable.
            node = self.node.find('./vfSectLoose')
            if node is None:
                node = self.node.find('./vfSect')
            if node is None:
                node = '<vfSect/>'  # Dummy node
            self._variants = FormsList(node, self.lemma_manager())
            return self._variants

    def s1blocks(self):
        """
        Return a list of S1block objects, representing each part-of-speech
        block (<s1>) in the entry (usually only one).
        """
        try:
            return self._s1blocks
        except AttributeError:
            self._s1blocks = [S1block(n, self.headword, self.id)
                               for n in self.node.findall('./senseSect/s1')]
            for block in self._s1blocks:
                block.is_revised = self.is_revised

            # If the entry is obsolete, then all blocks must be obsolete
            if self.is_marked_obsolete() == True:
                for block in self._s1blocks:
                    block.set_obsolete_marker(True)

            # Note the id of the first sibling <s1> block
            for i, block in enumerate(self._s1blocks):
                if i > 0:
                    block.first_sibling = self._s1blocks[0].node_id()

            # If there's only one block, then the block can use
            #  the entry's date-range (to save having to recalculate it)
            if len(self._s1blocks) == 1:
                self._s1blocks[0].set_dates(self.date())
            return self._s1blocks

    def paired_with(self):
        """
        Return the ID of the entry that this entry is etymologically
        paired with, if any; i.e. the entry that it shares a headword
        with and that it derives from.

        E.g. parade, v. is derived from parade, n./2, so
        self.paired_with() would return the ID of parade, n./2.

        Returns None if the entry is not paired with another.
        """
        try:
            return self._paired
        except AttributeError:
            self._paired = None
            if len(self.etymology().etyma()) == 1:
                etymon = self.etymology().etyma()[0]
                if (etymon.type() == 'cross-reference' and
                    etymon.lemma == self.lemma and
                    etymon.wordclass() != self.primary_wordclass().penn):
                    self._paired = etymon.refentry()
            return self._paired

    def adjust_s1_quotation_counts(self):
        """
        For each block block, adjust its quotation count so that it includes
        quotations in a compounds block as well as quotation in
        the block itself.

        If the entry has several block blocks, counts from a compounds block
        should be assigned to the right one (probably a JJ or a NN block).

        If the entry has both a JJ and a NN block, counts from a
        compounds block are shared out proportionately between them.
        """
        blocks = self.s1blocks()
        total_quotations = sum([block.num_quotations() for block in blocks])

        # Default - same as num_quotations()
        for block in blocks:
            block.num_quotations_adjusted = block.num_quotations()

        if len(blocks) == 1:
            blocks[0].num_quotations_adjusted = self.num_quotations()
        elif total_quotations < self.num_quotations():
            # Difference probably represents quotations in a compounds block
            delta = self.num_quotations() - total_quotations
            penn_set = set([block.primary_wordclass().penn for block in blocks
                            if block.primary_wordclass() is not None])

            # If we have a noun and an adjective block, we share the
            #  extra quotations out between them in proportion to
            #  to their original size
            if len(penn_set) == 2 and 'NN' in penn_set and 'JJ' in penn_set:
                for block in blocks:
                    if (block.primary_wordclass() is not None and
                        block.primary_wordclass().penn in penn_set):
                        ratio = block.num_quotations() / total_quotations
                        block.num_quotations_adjusted += int(ratio * delta)
            else:
                largest = max(blocks, key=lambda block: block.num_quotations())
                largest.num_quotations_adjusted += delta
