import re
import copy

from lxml import etree

subdirs = {
    '04_allVerbs.models-applied': ('verb', 7,
        ['mood', 'tense', 'person_number', 'pronoun', 'wordform']),
    '05_allVerbs.regular': ('verb', 7,
        ['mood', 'tense', 'person_number', 'pronoun', 'wordform']),
    'x3_adj_nouns.infl': ('adjective', 6,
        ['wordform', 'gender', 'case', 'number', 'type']),
    'x3_adj_nouns_with_lexBase.infl': ('adjective', 6,
        ['wordform', 'gender', 'case', 'number', 'type']),
    'x3_nouns.infl': ('noun', 5,
        ['wordform', 'gender', 'case', 'number']),
    'x3_nouns_with_lexBase.infl': ('noun', 5,
        ['wordform', 'gender', 'case', 'number']),
    'x4_adjectives.infl': ('adjective', 7,
        ['wordform', 'gender', 'case', 'number', 'type', 'degree']),
}


class OxfordFormSet(object):

    def __init__(self, filepath, **kwargs):
        self.filepath = filepath
        self.variant_type = kwargs.get('vartype', 'null')
        self.classify()
        self.read_file()

    def classify(self):
        for dir, vals in subdirs.items():
            if dir in self.filepath:
                self.wordclass = vals[0]
                self.lemma_col = vals[1]
                self.column_names = vals[2]
                break

    def read_file(self):
        lines = []
        with open(self.filepath, 'r') as fh:
            for l in fh:
                l = l.decode('utf8').strip()
                if self.variant_type == 'min':
                    l = re.sub(r'\[[a-z]+\]', '', l)
                if self.variant_type in ('max', 'min'):
                    l = l.replace('[', '').replace(']', '')
                if l:
                    lines.append(l)

        lemma = None
        for l in lines:
            columns = [k or None for k in l.split('\t')]
            lemma = columns[self.lemma_col]
        self.lemmas = self._unpack_lemma(lemma)

        inflections = []
        for l in lines:
            inflections.append(Inflection(l, self.column_names, self.wordclass))
        self.inflections = self._unpack_inflections(inflections)

    def _unpack_lemma(self, lemma):
        if not lemma:
            return ()
        else:
            return self._unpack_brackets(lemma)

    def _unpack_inflections(self, inflections):
        # Unpack bracketed wordforms into two distinct inflections
        unpacked1 = []
        for i in [i for i in inflections if i.wordform]:
            variants = self._unpack_brackets(i.wordform)
            if len(variants) == 1:
                unpacked1.append(i)
            else:
                v1 = copy.copy(i)
                v1.wordform = variants[0]
                v2 = copy.copy(i)
                v2.wordform = variants[1]
                unpacked1.append(v1)
                unpacked1.append(v2)
        # Unpack 'mf'/'fm' gender into distinct 'm' and 'f' inflections
        unpacked2 = []
        for i in unpacked1:
            try:
                i.gender
            except AttributeError:
                unpacked2.append(i)
            else:
                if i.gender in ('mf', 'fm'):
                    v1 = copy.copy(i)
                    v1.gender = 'm'
                    v2 = copy.copy(i)
                    v2.gender = 'f'
                    unpacked2.append(v1)
                    unpacked2.append(v2)
                else:
                    unpacked2.append(i)
        return unpacked2

    def _unpack_brackets(self, wordform):
        if not '[' in wordform:
            return(wordform,)
        else:
            v1 = wordform.replace('[', '').replace(']', '').strip()
            v2 = re.sub(r'\[[a-z]+\]', '', wordform)
            v2 = v2.replace('[', '').replace(']', '').strip()
            return (v1, v2,)



class Inflection(object):

    def __init__(self, line, colnames, wordclass):
        self.line = re.sub(r'\tu11.*$', '', line)
        self.wordclass = wordclass
        columns = [k or None for k in line.split('\t')]
        for colname, val in zip(colnames, columns):
            if val is None or not val.strip():
                self.__dict__[colname] = None
            else:
                self.__dict__[colname] = val.strip()

        # Convert verb person+number value into separate person and
        # number attributes
        try:
            self.person_number
        except AttributeError:
            pass
        else:
            if self.person_number is not None and "_" in self.person_number:
                self.person, self.number = self.person_number.split("_")
            else:
                self.person, self.number = (None, None)

        if self.wordclass == 'adjective':
            try:
                self.degree
            except AttributeError:
                self.degree = 'positive'


    def is_viable(self):
        if (self.wordform is None or
            not self.wordform or
            " " in self.wordform):
            return False
        else:
            return True

    def grammar(self):
        try:
            return self.gram
        except AttributeError:
            vals = {}
            if self.wordclass in ('noun', 'adjective'):
                vals['number'] = convert_value(self.number, 'number')
                vals['case'] = convert_value(self.case, 'case')
            if self.wordclass == 'adjective':
                vals['gender'] = convert_value(self.gender, 'gender')
                vals['inflectionType'] = convert_value(self.type, 'type')
                vals['degree'] = convert_value(self.degree, 'degree')
            if self.wordclass == 'verb':
                vals['number'] = convert_value(self.number, 'number')
                vals['person'] = convert_value(self.person, 'person')
                vals['tense'] = convert_value(self.tense, 'tense')
                vals['mood'] = convert_value(self.mood, 'mood')
                vals['nonFinType'] = convert_value(self.mood, 'nonfintype')
                # If infinitive, all the other values should be null
                if vals['nonFinType'] == 'infinitive':
                    for att in vals.keys():
                        vals[att] = None
                    vals['nonFinType'] = 'infinitive'
                if vals['mood'] == 'imperative':
                    vals['tense'] = None
            self.gram = vals
            return self.gram

    def xml(self):
        if self.wordclass == 'noun':
            wrapper = 'nounUnit'
        elif self.wordclass == 'adjective':
            wrapper = 'adjUnit'
        elif self.wordclass == 'verb':
            wrapper = 'verbUnit'
        node = etree.Element(wrapper)
        wf = etree.SubElement(node, 'wordForm')
        base = etree.SubElement(wf, 'base')
        base.text = self.wordform

        # set grammar attributes
        for att, val in self.grammar().items():
            if val is not None:
                node.set(att, val)
        # set mandated attributes
        for att, val in (('genType', 'generated'),
                        ('genSource', 'Oxford German Dictionary'),
                        ('genConfirmed', 'no')):
            node.set(att, val)

        return node

    def signature(self):
        return self.wordform + '_' +\
            '_'.join(['%s:%s' % (att, self.grammar()[att])
            for att in sorted(self.grammar().keys())
            if self.grammar()[att] is not None])


def convert_value(value, type):
    if value is None:
        return None
    else:
        value = value.lower()
        type = type.lower()
        if type == 'number':
            return convert_number(value)
        elif type == 'case':
            return convert_case(value)
        elif type == 'gender':
            return convert_gender(value)
        elif type == 'person':
            return convert_person(value)
        elif type == 'degree':
            return convert_degree(value)
        elif type == 'tense':
            return convert_tense(value)
        elif type == 'mood':
            return convert_mood(value)
        elif type == 'nonfintype':
            return convert_nonfintype(value)
        elif type == 'type':
            return convert_type(value)
        else:
            return None

def convert_number(val):
    if val == 'sg':
        return 'singular'
    if val == 'pl':
        return 'plural'
    else:
        return None

def convert_case(val):
    if val == 'nom':
        return 'nominative'
    elif val in ('acc', 'akk'):
        return 'accusative'
    elif val == 'dat':
        return 'dative'
    elif val == 'gen':
        return 'genitive'
    else:
        return None

def convert_gender(val):
    if val == 'm':
        return 'masculine'
    elif val == 'f':
        return 'feminine'
    elif val == 'n':
        return 'neuter'
    elif val == 'mfn':
        return 'unspecified'
    elif val in ('mf', 'mn'):
        return 'masculine'
    elif val in ('fm', 'fn'):
        return 'feminine'
    else:
        return None

def convert_person(val):
    if val in ('first', 'second', 'third'):
        return val
    else:
        return None

def convert_degree(val):
    if val in ('positive', 'comparative', 'superlative'):
        return val
    else:
        return None

def convert_tense(val):
    if val == 'present':
        return 'present'
    elif val in ('preterite', 'past'):
        return 'past'
    else:
        return None

def convert_mood(val):
    if val in ('indicative', 'subjunctive', 'imperative'):
        return val
    else:
        return None

def convert_nonfintype(val):
    if val in ('infinitive', 'participle'):
        return val
    else:
        return None

def convert_type(val):
    if val in ('strong', 'weak'):
        return val
    else:
        return None


