"""
Sense -- OED sense unit (sense or subentry)

@author: James McCracken
"""

import re

from lex.oed.semanticcomponent import SemanticComponent
from lex.lemma import Lemma

CURRENT_SENSE_INDICATORS = {
    'current usual sense', 'now the usual sense',
    '(the usual sense', 'most usual sense',
    'more usual sense', 'usual modern sense', 'ordinary modern sense',
    'prevailing modern sense', 'chief modern sense',
    'most frequent modern use', 'ordinary current sense',
    'now the most common sense', 'leading sense', 'leading current sense',
    'now the most frequent sense', 'now the ordinary sense',
    'the current sense', 'the chief current sense', 'main current sense',
    'the prevailing sense', 'the usual current sense'
}
RARE_INDICATORS = (
    re.compile(r'now only [a-z]+\.?(| (or|and) [a-z]+\.?)$', re.I),
    re.compile(r'now (|chiefly )(rare|hist|arch|regional|dial)\.*(| (and|or) [a-z]+\.?)$', re.I),
    re.compile(r'[( ](rare|hist|arch|regional)\.?\)\.?$', re.I),
    re.compile(r'now (rare|hist|arch|regional|dial)\.? (exc\.|except) [a-z -]+\.$', re.I),
    re.compile(r'(\.| and| or| exc\.) (rare|hist|arch|regional|dial)\.*$', re.I),
    re.compile(r'(rare|hist\.|arch\.|dial\.) or obs\.$', re.I),
    re.compile(r'perh\. obs[.)]*$', re.I),
    re.compile(r' (obs\.|rare|hist\.|arch\.|regional|dial\.) exc\. (|in )[a-z]+\.?(| [a-z]+\.?)$', re.I),
    re.compile(r'obs\. exc\. [a-z]+\.?(| (or|and) [a-z]+\.?)$', re.I),
)
EXTENDED_USE_INDICATORS = (
    re.compile('^in (proverb|figurative|fig\.|extended)', re.I),
    re.compile('^(transf|fig)\. ', re.I),
    re.compile('^(proverb|hence[: ])', re.I),
)
ATTRIB_INDICATOR = re.compile(r'^(|gen\. |general )(attrib\.|attributive)', re.I)
PHRASAL_INDICATOR = re.compile(r'^(in |)(phrase|compound)', re.I)
REGIONAL = {'Scotland', 'Ireland', 'Northern England', 'Caribbean',
            'India', 'Australia', 'New Zealand', 'Africa'}


class Sense(SemanticComponent):

    """
    OED sense unit (sense or subentry)
    """

    def __init__(self, node, headword_object, identifier):
        SemanticComponent.__init__(self, node)
        self.id = identifier
        self._lemma_object = None
        self._headword_object = headword_object

    def sense_number(self):
        return self.node.get('senseNumber', None)

    def s4_number(self):
        """
        Return the sense number of the parent <s4> sense (or of this sense,
        if it's a <s4>)
        Defaults to 0 (if this is not inside a <s4>, or if the <s4> is
        unnumbered)
        """
        if self.tag == 's4':
            return self.num
        elif self.tag in ('s6', 's7',):
            for node in self.node.iterancestors(tag='s4'):
                return int(node.get('num', 0))
        return 0

    def s6_number(self):
        """
        Return the sense number of the parent <s6> sense (or of this sense,
        if it's a <s6>)
        Defaults to 0 (if this is not inside a <s6>)
        """
        if self.tag == 's6':
            return self.num
        elif self.tag in ('s7',):
            for node in self.node.iterancestors(tag='s6'):
                return int(node.get('num') or 0)
        return 0

    def s7_number(self):
        """
        Return the sense number of the parent <s7> sense (or of this sense,
        if it's a <s7>)
        Defaults to 0 (if this is not inside a <s7>)
        """
        if self.tag == 's7':
            return self.num
        else:
            return 0

    #===================================================
    # Lemma-related functions
    #===================================================

    @property
    def lemma(self):
        """
        Return the lemma for this sense or subentry (as a string).
        """
        return self.lemma_manager().lemma

    @property
    def headword(self):
        """
        Return the headword for the sense's parent entry (as a string).
        """
        return self.headword_manager().lemma

    def lemma_manager(self):
        """
        Return the Lemma instance containing the
        lemma for this sense or subentry.
        """
        if self._lemma_object is None:
            lemma = self.characteristic_first('lemma')
            if not lemma and self.is_subentry():
                lemma = (self.node.findtext('./lemUnit/lemVersions/lm') or
                         self.node.findtext('./lm') or '')
            elif not lemma and self.is_subentry_like():
                lemma = (self.node.findtext('./sub/lemUnit/lemVersions/lm') or
                         self.node.findtext('./sub/lm') or '')
            self._lemma_object = Lemma(lemma)
        return self._lemma_object

    def set_lemma(self, new_lemma_object):
        """
        Reset self._lemma_object to a new value.

        Argument must be an instance of Lemma.
        """
        self._lemma_object = new_lemma_object

    def alt_lemma_manager(self):
        """
        Alternative form of the lemma - taken from <vl> if the sense
        is a subentry.

        Value will be '' if the sense is not a subentry or does not
        have a <vl>.
        """
        try:
            return self._alt_lemma_object
        except AttributeError:
            if self.is_subentry():
                lemma = self.node.findtext('./subVfSect/vl') or ''
            elif self.is_subentry_like():
                lemma = self.node.findtext('./sub/subVfSect/vl') or ''
            else:
                lemma = ''
            self._alt_lemma_object = Lemma(lemma)
            return self._alt_lemma_object

    def headword_manager(self):
        """
        Return the Lemma instance containing the headword for the
        sense's parent entry.
        """
        return self._headword_object

    def is_compound_of(self, **kwargs):
        headword = kwargs.get('headword', '').lower()
        components = kwargs.get('lemmas') or [kwargs.get('lemma'),]
        components = [word.lower() for word in components]
        lemma = self.lemma.lower()
        if self.is_phrase():
            return False
        for word in components:
            if (lemma.startswith(word + '-') or
                    lemma.startswith(word + ' ') or
                    lemma.endswith('-' + word) or
                    lemma.endswith(' ' + word)):
                return True
            if (headword and
                    (lemma == headword + word or lemma == word + headword)):
                return True
        return False

    def lemma_matches_headword(self, **kwargs):
        if self.lemma == self.headword:
            return True
        elif (kwargs.get('loose') and
                self.lemma_manager().lexical_sort() ==
                self.headword_manager().lexical_sort()):
            return True
        else:
            return False

    #===========================================================
    # Functions used to characterize the sense
    #  - most return True/False depending on whether the sense
    #   has the feature being tested for.
    #============================================================

    def is_in_sensesect(self):
        return any([a.tag == 'senseSect' for a in self.ancestor_nodes()])

    def is_in_lemsect(self):
        return any([a.tag == 'lemSect' for a in self.ancestor_nodes()])

    def is_in_revsect(self):
        return any([a.tag == 'revSect' for a in self.ancestor_nodes()])

    def is_subentry(self):
        return self.tag == 'sub'

    def is_subentry_like(self):
        if self.is_subentry():
            return False
        else:
            try:
                child = self.node[0]
            except IndexError:
                child = None
            if child is not None and child.tag == 'sub':
                return True
            else:
                return False

    def is_derivative(self):
        """
        Return True if this is a derivative subentry.
        """
        if (self.is_subentry() and
                any([ancestor.tag == 'lemSect' and
                    ancestor.get('type') == 'Derivatives'
                    for ancestor in self.ancestor_nodes()])):
            return True
        else:
            return False

    def subentry_type(self):
        if not self.is_subentry():
            return None
        else:
            for ancestor_type in [a.get('type').lower() for a in
                                  self.ancestor_nodes()
                                  if a.tag == 'lemSect' and a.get('type')]:
                atype = ancestor_type.rstrip('s').replace('_', ' ')
                if atype == 'special use':
                    atype = 'compound'
                return atype
        return None

    def is_sublemma(self):
        if (self.is_subentry() or
            (self.is_subentry_like() and self.lemma != self.headword) or
            self.lemma_manager().length() > self.headword_manager().length() + 3):
            return True
        else:
            return False

    def is_phrase(self):
        return (self.primary_wordclass.source == 'phrase' or
                self.lemma_manager().is_phrasal())

    def is_simple(self):
        return not self.is_sublemma() and not self.is_phrase()

    def is_figurative(self):
        """
        Return True if the current definition, or any headers above it,
        suggest that this sense is figurative or extended.
        Returns False otherwise.
        """
        definition1 = self.definition_manager().text_start()
        definition2 = self.definition_manager().text_start(with_header=True)
        if any([pattern.search(definition1) or pattern.search(definition2)
                for pattern in EXTENDED_USE_INDICATORS]):
            return True
        else:
            return False

    def has_current_sense_indicator(self):
        """
        Test the definition for markers indicating that this is the
        prevailing modern sense. Returns True if such a marker is found,
        False if not.

        False does not necessarily mean that this is *not* the prevailing
        modern sense, just that it's not explicitly marked as such.
        """
        definition = self.definition().lower()
        headers = ''.join([h.lower() for h in self.header_strings()])
        if any([marker in definition or marker in headers
                for marker in CURRENT_SENSE_INDICATORS]):
            return True
        else:
            return False

    is_current_sense = has_current_sense_indicator

    def has_rare_indicator(self):
        definition1 = self.definition_manager().text_start()
        definition2 = re.sub(r'\([^()]+\)\.?$', '', definition1)
        definition2 = definition2.strip()
        if any([pattern.search(definition1) for pattern in RARE_INDICATORS]):
            return True
        elif (definition2 != definition1 and
                any([pattern.search(definition2) for pattern in RARE_INDICATORS])):
            return True
        else:
            return False

    def is_grammatically_atypical(self):
        if (self.primary_wordclass().penn == 'NN' and
                self.has_attributive_indicator()):
            return True
        elif (self.primary_wordclass().penn == 'JJ' and
                self.has_absol_indicator()):
            return True
        else:
            return False

    def has_attributive_indicator(self):
        if ATTRIB_INDICATOR.search(self.definition()):
            return True
        else:
            return False

    def has_absol_indicator(self):
        return self.definition().startswith('absol.')

    def is_supplement_sense(self):
        """
        Return True if this appears to be a supplement sense in an
        unrevised OED1 entry
        """
        if not self.is_revised and self.date().end > 1950:
            return True
        else:
            return False

    def is_regional(self):
        regions = set(self.characteristic_nodes('region'))
        if regions.intersection(REGIONAL):
            return True
        else:
            return False

    def has_phrasal_indicator(self):
        definition1 = self.definition_manager().text_start()
        definition2 = self.definition_manager().text_start(with_header=True)
        if (PHRASAL_INDICATOR.search(definition1) or
                PHRASAL_INDICATOR.search(definition2)):
            return True
        else:
            return False

    def is_xref_sense(self):
        """
        Return True is this is a cross-reference sense (i.e. has a
        'see'-type cross-reference but no quotations);
        otherwise return False.
        """
        xrefs = self.definition_manager().cross_references()
        return (self.num_quotations() == 0 and
                not self.has_shared_quotations() and
                xrefs and
                xrefs[0].type == 'see')

    #====================================================
    # Thesaurus-related functions
    #====================================================

    def thesaurus_categories(self):
        """
        Return the ID breadcrumbs for the sense's thesaurus branches.
        """
        return self.characteristic_list('thesaurus')

    def thesaurus_nodes(self):
        """
        Return the end-node IDs from the list of thesaurus branches.
        """
        return self.characteristic_leaves('thesaurus')

    thesaurus_leaves = thesaurus_nodes
