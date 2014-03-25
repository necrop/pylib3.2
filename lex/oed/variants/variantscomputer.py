"""
VariantsComputer

@author: James McCracken
"""

import re

from lex import lexconfig
from lex.oed.variants import variantsconfig
from lex.oed.variants.variantscache import VariantsCache
from lex.oed.variants.variantform import VariantForm
from lex.oed.daterange import DateRange
from lex.oed.lemmawithvariants import LemmaWithVariants
from stringtools import lexical_sort

DERIVATIVE_AFFIXES = variantsconfig.DERIVATIVE_AFFIXES

# Variants will not be generated for the following, where they appear
#  in compounds (case-insensitive).
STOPWORDS_PATTERN = re.compile(variantsconfig.STOPWORDS_PATTERN, re.I)

# Maximum number of variants that will be generated for a compound.
#  If the number of possible compounds is higher than this, the list will
#  be truncated, starting with the oldest (those with the earliest end date).
COMPOUNDS_CAP = variantsconfig.COMPOUNDS_CAP


class VariantsComputer(object):

    def __init__(self, **kwargs):
        self.lemma_manager = LemmaWithVariants(kwargs.get('lemma'))
        self.lemma = kwargs.get('lemma')
        self.id = kwargs.get('id')
        self.wordclass = kwargs.get('wordclass')
        self.date = kwargs.get('daterange', DateRange(start=0, end=0))
        self.headwords = kwargs.get('headwords', [])
        self.hint_ids = []
        self.etyma = []

        if self.wordclass == 'NNS':
            self.wordclass = 'NN'
        self.headwords = [hw.replace('(', '').replace(')', '')
                          for hw in self.headwords]
        self.variants_cache = VariantsCache()

    def set_hint_ids(self, identifiers):
        self.hint_ids = identifiers

    def set_etyma(self, etyma):
        self.etyma = etyma

    def primary_sets(self):
        try:
            return self._primary_variant_sets
        except AttributeError:
            self._primary_variant_sets = self.variants_cache.find_all(id=self.id)
            return self._primary_variant_sets

    def hint_sets(self):
        try:
            return self._hint_variant_sets
        except AttributeError:
            self._hint_variant_sets = []
            for hint_id in self.hint_ids:
                for varset in self.variants_cache.find_all(id=hint_id):
                    self._hint_variant_sets.append(varset)
            return self._hint_variant_sets

    def compute(self):
        varsets = []
        for varset in self.primary_sets():
            if (varset.lemma == self.lemma and
                varset.revised_status != 'omitted'):
                varsets.append(varset)
        for varset in self.hint_sets():
            if (varset.lemma == self.lemma and
                varset.revised_status != 'omitted'):
                varsets.append(varset)
        if varsets:
            filtered_varsets = _filter_varsets(varsets,
                                               self.wordclass,
                                               self.date)
            self.lemma_manager.variants.extend(filtered_varsets)

        if (not varsets and
            self.lemma_manager.is_compound() and
            self.date.start):
            self._build_compound_variants()

        # If no variants listed, then default to the lemma itself
        if not self.lemma_manager.variants:
            variant_form = VariantForm(self.lemma,
                                       self.date.start,
                                       self.date.projected_end())
            self.lemma_manager.variants.append(variant_form)

        self._check_for_omissions()
        self._check_dating()
        self._check_compound_variation()

    def _build_compound_variants(self):
        for i, component in enumerate(self.lemma_manager.components()):
            if not STOPWORDS_PATTERN.search(component.lemma):
                component_varsets = [vs for vs in self.hint_sets() if
                                     vs.lemma == component.lemma]
                if not component_varsets:
                    component_varsets = self.variants_cache.find_all(lemma=component.lemma)
                    component_varsets = [vs for vs in component_varsets
                                         if vs.revised_status != 'omitted']

                if (i == 0 and
                        self.wordclass in ('NN', 'JJ') and
                        _test_varsets_for_wordclass(component_varsets, 'JJ')):
                    wordclass = 'JJ'
                elif component.lemma.startswith('-'):
                    wordclass = None
                else:
                    wordclass = self.wordclass
                filtered_varsets = _filter_varsets(component_varsets,
                                                   wordclass,
                                                   self.date)
                component.variants.extend(filtered_varsets)
            if not component.variants:
                dummy_vf = VariantForm(component.lemma,
                                       self.date.start - 10,
                                       self.date.projected_end() + 10)
                component.variants.append(dummy_vf)
        self.lemma_manager.recombine_components(date=self.date,
                                                cap=COMPOUNDS_CAP)

    def _check_for_omissions(self):
        # If there's a secondary/alternative headword, check that this has
        #   ended up included in the list of variants
        if self.lemma_manager.alt is not None:
            self.lemma_manager.refresh_variants_set()
            if not self.lemma_manager.in_variants_list(self.lemma_manager.alt.dictionary_sort):
                variant_form = VariantForm(self.lemma_manager.alt.lemma,
                                           self.date.start,
                                           self.date.projected_end())
                self.lemma_manager.variants.append(variant_form)

        varsets = []
        for varset in self.primary_sets():
            if varset.lemma == self.lemma:
                varsets.append(varset)
        variant_forms = _filter_varsets(self.primary_sets(),
                                        self.wordclass,
                                        self.date)
        if variant_forms:
            self.lemma_manager.refresh_variants_set()
            for variant_form in variant_forms:
                if not self.lemma_manager.in_variants_list(lexical_sort(variant_form.form)):
                    self.lemma_manager.variants.append(variant_form)

        # Check that the entry headword(s) is represented; given that the ODE
        #  lemma form may be substituted for the original OED lemma form, it's
        #  possible that it's not.
        if self.date.end > 1750:
            for headword in self.headwords:
                matches = [vf for vf in self.lemma_manager.variants if
                           vf.form.replace('~', '') == headword.replace('~', '')]
                if not matches:
                    variant_form = VariantForm(headword,
                                               self.date.start,
                                               self.date.projected_end())
                    self.lemma_manager.variants.append(variant_form)


    def _check_compound_variation(self):
        if (self.lemma_manager.is_compound() and
            not self.lemma_manager.is_affix() and
            self.lemma_manager.num_words() == 2 and
            self.lemma_manager.capitalization_type() == 'downcased'):
            compound_variants = []
            if self.wordclass == 'NN' and '-' in self.lemma:
                compound_variants.append(self.lemma.replace('-', ' '))
            elif (self.wordclass == 'NN' and
                  ' ' in self.lemma and
                  not '\'s ' in self.lemma):
                compound_variants.append(self.lemma.replace(' ', '-'))
            elif (self.wordclass == 'NN' and
                  '~' in self.lemma and
                  len(self.lemma_manager.words()[1]) > 3 and
                  not self.lemma_manager.words()[1] in DERIVATIVE_AFFIXES):
                compound_variants.append(self.lemma.replace('~', '-'))
            elif self.wordclass == 'JJ' and ' ' in self.lemma:
                compound_variants.append(self.lemma.replace(' ', '-'))

            for compound_form in compound_variants:
                matches = [vf for vf in self.lemma_manager.variants
                           if vf.form == compound_form]
                if not matches:
                    # print repr(self.lemma), self.wordclass, repr(compound_form)
                    variant_form = VariantForm(compound_form,
                                               self.date.start,
                                               self.date.projected_end())
                    self.lemma_manager.variants.append(variant_form)


    def _check_dating(self):
        """
        If the lemma is still current, make sure that the variant
        representing the lemma is also current. (To avoid e.g. the variant
        for 'whereupon' being dated according to the dates for 'where' and
        'upon' adv., the latter of which is obsolete.)
        """
        if self.date.projected_end() > 1950:
            for variant_form in self.lemma_manager.variants:
                if (variant_form.form == self.lemma and
                    variant_form.date.end < self.date.projected_end()):
                    variant_form.date.reset('end', self.date.projected_end())



def _test_varsets_for_wordclass(varsets, wordclass):
    if any([varset.wordclass == wordclass for varset in varsets]):
        return True
    else:
        return False

def _filter_varsets(varsets, wordclass, daterange):
    filtered = ([vs for vs in varsets if vs.wordclass == wordclass] or
                varsets[:])
    filtered.sort(key=lambda varset: varset.num_quotations, reverse=True)
    try:
        winner = filtered[0]
    except IndexError:
        return []
    else:
        base_wordclass = winner.wordclass
        if base_wordclass in winner.variants:
            return [vf for vf in winner.variants[base_wordclass]
                    if vf.date.overlap(daterange)]
        else:
            return []
