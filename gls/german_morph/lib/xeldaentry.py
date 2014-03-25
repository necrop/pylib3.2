import re
import itertools

from lxml import etree

class XeldaEntry(object):

    def __init__(self, node):
        self.node = node

    def id(self):
        return self.node.get('refid')

    def lemma(self):
        return self.node.findtext('lemma')

    def headword(self):
        return self.lemma()

    def wordclass(self):
        j = self.node.findtext('pos')
        if j == 'n':
            return 'noun'
        elif j == 'v':
            return 'verb'
        elif j == 'adj':
            return 'adjective'
        else:
            return j

    def gender(self):
        return self.node.findtext('gender')

    def rows(self):
        try:
            return self.rowset
        except AttributeError:
            nodes = self.node.findall('declensions/d')
            self.rowset = [Row(n, self.wordclass(), self.lemma()) for n in nodes]
            return self.rowset

    def declensions(self):
        j = []
        for r in self.rows():
            j.extend(r.declensions())
        return j


class Row(object):
    CASEMAP = {'nom': 'nominative', 'gen': 'genitive', 'dat': 'dative',
        'acc': 'accusative'}
    PERSONMAP = {'1p': 'first', '2p': 'second', '3p': 'third'}

    def __init__(self, node, wordclass, lemma):
        self.node = node
        self.wordclass = wordclass
        self.lemma = lemma

    def wordform(self):
        try:
            return self.wf
        except AttributeError:
            self.wf = self.node.text
            # Wordforms need to be downcased if the lemma is downcased
            #  (for some reason adj and verb wordforms are erroneously
            #  upcased in the Xelda data)
            if self.wf is not None and self.lemma.lower() == self.lemma:
                self.wf = self.wf.lower()
            return self.wf

    def tagparts(self):
        try:
            return self.tp
        except AttributeError:
            parts = reversed(self.node.get('tag').split('+'))
            self.tp = []
            for p in parts:
                if p in ('Noun', 'Adj', 'Verb'):
                    break
                else:
                    self.tp.append(p)
            return self.tp

    def declensions(self):
        try:
            return self.decl
        except AttributeError:
            grammar = {'number': None, 'person': None, 'gender': None,
                'case': None,'degree': None, 'mood': None, 'tense': None,
                'nonFinType': None, 'inflectionType': None}
            for t in self.tagparts():
                if t == 'Sg':
                    grammar['number'] = 'singular'
                elif t == 'Pl':
                    grammar['number'] = 'plural'
                elif t == 'Wk':
                    grammar['inflectionType'] = 'weak'
                elif t == 'St':
                    grammar['inflectionType'] = 'strong'
                elif t == 'Pos':
                    grammar['degree'] = 'positive'
                elif t == 'Comp':
                    grammar['degree'] = 'comparative'
                elif t in ('Sup', 'Sup2'):
                    grammar['degree'] = 'superlative'
                elif t == 'Past':
                    grammar['tense'] = 'past'
                elif t == 'Pres':
                    grammar['tense'] = 'present'
                elif t == 'Inf':
                    grammar['nonFinType'] = 'infinitive'
                elif t == 'PPres':
                    grammar['nonFinType'] = 'participle'
                    grammar['tense'] = 'present'
                elif t == 'PPast':
                    grammar['nonFinType'] = 'participle'
                    grammar['tense'] = 'past'
                elif t == 'Masc':
                    grammar['gender'] = 'masculine'
                elif t == 'Fem':
                    grammar['gender'] = 'feminine'
                elif t == 'Neut':
                    grammar['gender'] = 'neuter'
                elif t in ('Undef', 'MFN'):
                    grammar['gender'] = 'unspecified'

            # corrections - remove any values that shouldn't be there
            if self.wordclass in ('noun', 'adjective'):
                for att in ('tense', 'mood', 'nonFinType'):
                    grammar[att] = None
            if self.wordclass in ('noun', 'verb'):
                for att in ('degree', 'inflectionType'):
                    grammar[att] = None
            if self.wordclass == 'noun':
                grammar['gender'] = None
            if self.wordclass == 'adjective' and grammar['degree'] is None:
                grammar['degree'] = 'positive'

            # Generate the cartesian product of cases, person, and
            #  moods (since there may be more than one of each - though never
            #  more than one of all for any given row)
            z = itertools.product(self._cases(), self._persons(), self._moods())

            self.decl = []
            for p in z:
                # Copy the grammar dictionary
                vals = {k: v for k, v in grammar.items()}
                vals['case'] = p[0]
                vals['person'] = p[1]
                vals['mood'] = p[2]
                self.decl.append(Declension(self.wordform(), self.wordclass, vals))
            return self.decl

    def _cases(self):
        if self.wordclass in ('noun', 'adjective'):
            case_string = None
            for t in self.tagparts():
                if re.search(r'^(Nom|Acc|Gen|Dat)', t):
                    case_string = t
            j = []
            if case_string is not None:
                # split into chunks of 3 characters each
                case_string = re.sub(r'[0-9]', '', case_string)
                cases = [case_string[pos:pos + 3].lower() for pos in
                        xrange(0, len(case_string), 3)]
                for c in cases:
                    if c in self.CASEMAP:
                        j.append(self.CASEMAP[c])
            else:
                j.append(None)
            return j
        else:
            return [None,]

    def _persons(self):
        if self.wordclass == 'verb':
            person_string = None
            for t in self.tagparts():
                if re.search(r'^[123]P', t):
                    person_string = t
            j = []
            if person_string is not None:
                # split into chunks of 2 characters each
                persons = [person_string[pos:pos + 2].lower() for pos in
                             xrange(0, len(person_string), 2)]
                for p in persons:
                    if p in self.PERSONMAP:
                        j.append(self.PERSONMAP[p])
            else:
                j.append(None)
            return j
        else:
            return [None,]

    def _moods(self):
        if self.wordclass == 'verb':
            mood_string = None
            for t in self.tagparts():
                if re.search(r'^(Imp|Indc|Subj)', t):
                    mood_string = t
            j = []
            if mood_string == 'Imp':
                j.append('imperative')
            elif mood_string == 'Indc':
                j.append('indicative')
            elif mood_string == 'Subj':
                j.append('subjunctive')
            elif mood_string == 'IndcSubj':
                j.append('indicative')
                j.append('subjunctive')
            else:
                j.append(None)
            return j
        else:
            return [None,]


class Declension(object):
    ATTRIBUTES = ('gender', 'number', 'case', 'degree', 'inflectionType',
        'mood', 'tense', 'person', 'nonFinType')

    def __init__(self, wordform, wordclass, grammar):
        self.wordform = wordform
        self.wordclass = wordclass
        for att, val in grammar.items():
            self.__dict__[att] = val

    def grammar(self):
        vals = {}
        for att in self.ATTRIBUTES:
            if att in self.__dict__ and self.__dict__[att] is not None:
                vals[att] = self.__dict__[att]
        return vals

    def signature(self):
        return self.wordform + '_' +\
            '_'.join(['%s:%s' % (att, self.grammar()[att])
            for att in sorted(self.grammar().keys())
            if self.grammar()[att] is not None])

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
        for att, val in (('genConfirmed', 'no'),):
            node.set(att, val)
        return node

