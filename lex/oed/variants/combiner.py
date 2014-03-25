"""
Combiner

@author: James McCracken
"""

from lex.oed.variants.variantform import VariantForm


class Combiner(object):

    def __init__(self, **kwargs):
        self.tokens = []
        self.connectors = []
        self.output = []
        self.reference_date = kwargs.get('date')
        self.cap = int(kwargs.get('cap', 50))

    def add_tokenset(self, varlist, **kwargs):
        if not self.reference_date:
            varlist2 = varlist[:]
        else:
            varlist2 = [vf for vf in varlist
                        if vf.date.overlap(self.reference_date)]
        self.tokens.append(varlist2)
        self.connectors.append(kwargs.get('connector', ' '))

    def num_tokens(self):
        return len(self.tokens)

    def estimate_output(self):
        """
        Return an estimate of the total number of combinations
         that could be generated.
        """
        total = 1
        for varlist in self.tokens:
            total = total * len(varlist)
        return total

    def combine_tokens(self):
        self._trim_token_lists()
        self._sanitize_connectors()
        self._seed_output()
        self._recurse()
        self._desanitize_output()

    def _seed_output(self):
        self.output = [VariantForm('', 1000, 2050)]
        self.count = 0

    def _recurse(self):
        tmp = []
        i = self.count
        for stem in self.output:
            for variant_form in self.tokens[i]:
                # Extend the lemma string by appending this component
                stem_extended = stem.form + variant_form.form + self.connectors[i]

                # Narrow the date range so that the date range is always
                # limited to the overlap of the components handled so far
                if variant_form.date.start > stem.date.start:
                    adjusted_start = variant_form.date.start
                else:
                    adjusted_start = stem.date.start
                if variant_form.date.end < stem.date.end:
                    adjusted_end = variant_form.date.end
                else:
                    adjusted_end = stem.date.end

                new_variant_form = VariantForm(stem_extended,
                                               adjusted_start,
                                               adjusted_end)
                if stem.irregular or variant_form.irregular:
                    new_variant_form.irregular = True
                if stem.regional or variant_form.regional:
                    new_variant_form.regional = True

                if (new_variant_form.date.span() >= 0 and
                    (not self.reference_date or
                     new_variant_form.date.overlap(self.reference_date))):
                    tmp.append(new_variant_form)
        if tmp:
            self.output = tmp
        self.count += 1
        if self.count == self.num_tokens():
            return
        self._recurse()

    def _sanitize_connectors(self):
        # Mask spaces in connectors; since these a likely to be stripped
        #  in the course of generating lemmas
        for connector in self.connectors:
            connector = connector.replace(' ', '_')

    def _desanitize_output(self):
        for variant_form in self.output:
            new_form = variant_form.form.replace('_', ' ').replace('~-', '~')
            variant_form.reset_form(new_form.strip())

    def _trim_token_lists(self):
        # Remove regional and irregular variants
        for i, varlist in enumerate(self.tokens):
            tmp = [vf for vf in varlist if not vf.regional and
                   not vf.irregular and not vf.has_en_ending and
                   vf.date.start < 2000]
            # If this left nothing, try again but leave in regional forms
            if not tmp:
                tmp = [vf for vf in varlist if not vf.irregular and
                      not vf.has_en_ending and vf.date.start < 2000]
            # If this left nothing, don't filter at all
            if tmp:
                self.tokens[i] = tmp

        # Remove older forms if the estimated number of combinations
        #  would exceed the cap; keep removing older forms until the
        #  estimated number of combinations is below the cap.
        if self.cap is not None:
            while self.estimate_output() > self.cap:
                lenlist = [len(varlist) for varlist in self.tokens]
                i = lenlist.index(max(lenlist))
                self.tokens[i].pop()
