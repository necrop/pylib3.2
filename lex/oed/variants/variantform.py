"""
VariantForm -- Class representing an OED variant form and its date range
VariantFormFromParser --Extended version of VariantForm.

@author: James McCracken
"""

import re

from lxml import etree

from lex.lemma import Lemma
from lex.oed.daterange import DateRange
from lex.oed.oedcomponent import OedComponent

GRAMMAR_PATTERNS = {
    'NNS': re.compile(r'(plural|pl\.)', re.I),
    'VBZ': re.compile(r'((3rd|2nd) (pers\. |person |)(pres\.|present|sing\.|pl\.)|(pres\.|present) indicative)', re.I),
    'VBG': re.compile(r'((pres\.|present) (pple\.|participle)|gerund)', re.I),
    'VBD': re.compile(r'((pa\.|past) tense|(ind\.|subj\.|indicative|subjunctive) (pa\.|past)|(pa\.|past) (ind\.|subj\.|indicative|subjunctive))', re.I),
    'VBN': re.compile(r'(pa\.|past)( tense and|) (pple\.|participle)', re.I),
    'JJR': re.compile(r'(compar\.|comparative)', re.I),
    'JJS': re.compile(r'(superl\.|superlative)', re.I),
    'negative': re.compile(r'negative', re.I),
    'genitive': re.compile(r'(genit\.|genitive)', re.I),
    'compound': re.compile(r'(compound|combining)', re.I),
    'unspecified': re.compile(r'inflected|inflection|inflexion', re.I)}

IRREGULAR_PATTERNS = re.compile(
    r'(non-?standard|humorous|jocular|joc\.|transmission error|irregular|irreg\.|contracted|contr\.|in sense|slang|colloq|erron\.|rare|arch\.|hist\.|improp\.|improperly|misprint|printed|misspell)', re.I)
REGIONAL_PATTERNS = re.compile(
    r'(^dial\.| dial\.|regional|Orm\.|Ormin|Layamon)')
DISTIL_PATTERNS = re.compile(
    r'(imp\.|imperative|tense) (sing\.|pl\.|singular|plural)')


class VariantForm(object):
    """
    Class representing an OED variant form and its date range.

    Arguments to init:
     -- form (string)
     -- start_date (int)
     -- end_date (int)
    """

    def __init__(self, form, start_date, end_date):
        self.original_form = form
        self.date = DateRange(start=start_date,
                              end=end_date,
                              hardEnd=True)
        self.wordclass = None  # usually stays undefined
        self._lemma_manager = None
        self.regional = False  # default
        self.irregular = False  # default
        self.has_en_ending = False  # default
        self.undated = False
        self.computed = False
        self.structural_id = 0  # default
        self.headers = []
        self.header_labels = []
        self.label = ''
        self.grammatical_information = ''

    def __repr__(self):
        return '<VariantForm: %s (%d\u2014%d)>' % (self.form,
                                                   self.date.start,
                                                   self.date.projected_end())

    @property
    def form(self):
        """
        Return the variant form itself (shortcut for self.lemma_manager.lemma).
        """
        return self.lemma_manager().lemma

    @property
    def sort(self):
        return self.lemma_manager().lexical_sort()

    def lemma_manager(self):
        """
        Return a Lemma object based on the variant form.
        """
        if self._lemma_manager is None:
            form = self.original_form.strip().replace('(', '').replace(')', '')
            self._lemma_manager = Lemma(form)
        return self._lemma_manager

    def reset_form(self, new_lemma):
        """
        Replace the Lemma object with a new Lemma object using a new form.

        Used by Formslist.detruncate when detruncating the forms list.
        """
        self._lemma_manager = Lemma(new_lemma)
        return self._lemma_manager

    def set_grammatical_information(self, value):
        self.grammatical_information = DISTIL_PATTERNS.sub(r'\1', value)
        return self.grammatical_information

    def is_truncated(self):
        """
        Return True if the form is truncated, or False if not.
        """
        return self.lemma_manager().is_affix()

    def check_en_ending(self, wordclass, headword):
        """
        Switch self.has_en_ending to True if this is a verb
        ending in -en (and the headword does *not* end in -n).
        """
        if (wordclass == 'VB' and
            self.date.end <= 1600 and
            re.search(r'[eay]n+$', self.form) and
            not re.search(r'ne?$', headword)):
            self.has_en_ending = True

    def merge(self, other):
        """
        Merge another VariantForm instance into this one.

        Argument is another VariantForm instance.

        Used by Formslist.forms_uniq. Since merging will only be done in
        cases where the two instances have exactly the same form and exactly
        the same grammatical info, we only have to check if the date range
        needs to be extended in either direction.
        """
        # Switch 'regional' setting to other's regional setting if other
        #  looks like a more significant form. Ditto 'irregular' setting.
        if not self.is_more_important_than(other):
            self.regional = other.regional
            self.irregular = other.irregular
        # If necessary, extend the start date to an earlier start date
        self.date.extend_range(other.date)
        return

    def is_more_important_than(self, other):
        if self.date.projected_end() > other.date.projected_end():
            return True
        if (self.date.projected_end() == other.date.projected_end() and
            self.date.span() > other.date.span()):
            return True
        return False


class VariantFormFromParser(VariantForm):
    """
    Extension of VariantForm used when initially parsing the variant form
    from the entry's vfSect or vfSectLoose.

    Note that unlike the base VariantForm class, this is initialized
    with a node node containing the form, rather than with the form directly
    as text. The node is needed because the node's lexid needs to be
    extracted.

    Arguments to init:
     -- xml (XML node)
     -- start date (int)
     -- end date (int)
    """

    def __init__(self, xml, start_date, end_date):
        text = etree.tostring(xml, method='text', encoding='unicode', with_tail=False)
        VariantForm.__init__(self, text, start_date, end_date)
        self.xml = xml
        self.node = OedComponent(xml)
        self.gram_type = {}

    def set_headers(self, header_list):
        self.headers = []
        for header in header_list:
            header = DISTIL_PATTERNS.sub(r'\1', header)
            self.headers.append(header)

    def determine_irregularity(self):
        value = False
        if (IRREGULAR_PATTERNS.search(self.label) or
            IRREGULAR_PATTERNS.search(self.grammatical_information)):
            value = True
        for label in self.header_labels:
            if label and IRREGULAR_PATTERNS.search(label):
                value = True
        for header in self.headers:
            if IRREGULAR_PATTERNS.search(header):
                value = True
        self.irregular = value

    def determine_regionality(self):
        # Any label that's not indicating irregularity of some kind is assumed
        #  to be indicating regional status of some kind.
        if self.label and not IRREGULAR_PATTERNS.search(self.label):
            value = True
        elif any([label and not IRREGULAR_PATTERNS.search(label)
                  for label in self.header_labels]):
            value = True
        elif self.governing_text_contains(REGIONAL_PATTERNS):
            value = True
        else:
            value = False
        self.regional = value

    def governing_text_contains(self, pattern):
        if pattern.search(self.grammatical_information):
            return True
        elif any([pattern.search(header) for header in self.headers]):
            return True
        else:
            return False

    def is_grammar_type(self, grammar_type):
        grammar_type = grammar_type.strip()
        try:
            return self.gram_type[grammar_type]
        except KeyError:
            try:
                value = self.governing_text_contains(
                        GRAMMAR_PATTERNS[grammar_type])
            except KeyError:
                value = False
            if (grammar_type == 'VBG' and
               self.is_grammar_type('unspecified') and
               re.search(r'ing$', self.form)):
                value = True
            if ((grammar_type == 'VBD' or grammar_type == 'VBN') and
               self.is_grammar_type('unspecified') and
               re.search(r'ed$', self.form)):
                value = True
            self.gram_type[grammar_type] = value
            return self.gram_type[grammar_type]

    def grammar_signature(self):
        """
        Return a signature string representing the form's grammatical
        attributes: a concatenation of grammar types plus their boolean values.

        May be used to check whether two apparently identical variant forms
        really represent the same thing. (If so, their signatures should be the
        same.)
        """
        try:
            return self.__grammar_signature
        except AttributeError:
            siglist = []
            for rxkey, pattern in GRAMMAR_PATTERNS.items():
                value = self.governing_text_contains(pattern)
                siglist.append(rxkey + '=' + str(value))
            siglist.sort()
            self.__grammar_signature = '#'.join(siglist)
        return self.__grammar_signature

    def is_unmarked(self):
        """
        Return True if no grammatical class is specified for this form.

        I.e. if True, the form should represent the lemma's base wordclass.
        If False, the form may be e.g. a plural, a past tense form, etc.
        """
        if any([self.governing_text_contains(pattern)
                for pattern in GRAMMAR_PATTERNS.values()]):
            return False
        else:
            return True

    def sort_score(self, lemma):
        """
        Return a sort value (int): variants with lower sort values should
        be more salient (more recent, less obscure) than variants with
        higher sort values.
        """
        score = 0
        if lemma != self.form:
            score += 500
        score += (2100 - self.date.projected_end())
        if self.regional:
            score += 1500
        if self.irregular:
            score += 2000
        return score

    def diagnostics(self):
        string = '%s\n\t%s\n' % (self.form, self.date.to_string())
        for grammar_type in GRAMMAR_PATTERNS.keys():
            string += '\t%s: %s\n' % (grammar_type,
                                      self.is_grammar_type(grammar_type))
        return string

    def clone(self):
        """
        Return a shallow copy of the current object
        """
        myclone = VariantFormFromParser(self.xml,
                                        self.date.start,
                                        self.date.end)
        # Copy various attributes (in case any have changed from
        #  their default values set at initialization)
        myclone.grammatical_information = self.grammatical_information
        myclone.label = self.label
        myclone.regional = self.regional
        myclone.irregular = self.irregular
        myclone.has_en_ending = self.has_en_ending
        myclone.undated = self.undated
        return myclone
