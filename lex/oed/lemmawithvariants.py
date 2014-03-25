"""
LemmaWithVariants -- OED extended lemma class

@author: James McCracken
"""

import re

from lex.lemma import Lemma
from lex.oed.variants.combiner import Combiner
from regexcompiler import ReplacementListCompiler
from stringtools import lexical_sort

COMPONENTIZER = ReplacementListCompiler((
    (r"('s )", r'@'),
    (r"('s-)", r'%'),
    (r'(.)([ ~@%-])(.)', r'\1\2#\3'),
))

SUFFIXES = {'ing', 'ed', 'er', 'able', 'ness', 'ity', 'ally', 'ism',
            'ist', 'ship', 'hood', 'ish', 'ize', 'ian', 'less', 'dom',
            'ful', 'ment', 'ous', 'ical', 'ically', 'ess', 'ized',
            'ization'}


class LemmaWithVariants(Lemma):

    """
    OED lemma class - extends the base Lemma class (lex.lemma.Lemma)
    to allow it to contain:
     -- A list of variants (VariantForm objects).
     -- A list of component words (LemmaWithVariants objects), if a compound.
    """

    def __init__(self, arg):
        Lemma.__init__(self, arg)
        self.variants = []
        self.alt = None

    def set_variants(self, variants_list):
        self.variants = variants_list

    def set_alt(self, lemma_manager):
        self.alt = lemma_manager

    def components(self):
        try:
            return self._components
        except AttributeError:
            self._components = []
            tmp = COMPONENTIZER.edit(self.lemma)
            for component in tmp.split('#'):
                match = re.search(r'^(.+)([ ~@%-])$', component)
                if match is None:
                    word, connector = (component, '')
                    if self.is_closed_compound() and word in SUFFIXES:
                        word = '-' + word
                else:
                    word, connector = (match.group(1), match.group(2))
                    if connector == '@':
                        connector = "'s_"
                    elif connector == '%':
                        connector = "'s-"
                    elif connector == ' ':
                        connector = '_'
                component = LemmaWithVariants(word)
                component.connector = connector
                self._components.append(component)
            return self._components

    def recombine_components(self, **kwargs):
        combine_harvester = Combiner(**kwargs)
        for component in self.components():
            combine_harvester.add_tokenset(component.variants,
                                           connector=component.connector)
        combine_harvester.combine_tokens()
        self.variants = combine_harvester.output
        for variant_form in self.variants:
            if variant_form.form != self.lemma:
                variant_form.computed = True

    def variants_set(self):
        try:
            return self._variants_set
        except AttributeError:
            self.refresh_variants_set()
            return self._variants_set

    def refresh_variants_set(self):
        self._variants_set = set()
        for variant_form in self.variants:
            self._variants_set.add(lexical_sort(variant_form.form))
            self._variants_set.add(variant_form.form)
            self._variants_set.add(variant_form.form.replace('~', ''))

    def in_variants_list(self, form):
        if form in self.variants_set():
            return True
        else:
            return False
