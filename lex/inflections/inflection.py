#-------------------------------------------------------------------------------
# Name: inflection
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import re

from regexcompiler import ReplacementListCompiler


INFLECTION_PATTERNS = {
    'VBZ': ReplacementListCompiler((
        (r'([sxz]|sh|ch)$', r'\1es'),
        (r'([^aeiou])y$', r'\1ies'),
        (r'$', r's'))),
    'VBG': ReplacementListCompiler((
        (r'e$', r'ing'),
        (r'([bcdfghlmnprstvwz][aeiou])([bdfglmnpstz])$', r'\1\2\2ing'),
        (r'([bcdfghlmnprstvwz][aiou])r$', r'\1rring'),
        (r'$', r'ing'))),
    'VBD': ReplacementListCompiler((
        ('(e|\u00e9)$', r'\1d'),
        (r'([^aeiou])y$', r'\1ied'),
        (r'([bcdfghlmnprstvwz][aeiou])([bdfglmnpstz])$', r'\1\2\2ed'),
        (r'([bcdfghlmnprstvwz][aiou])r$', r'\1rred'),
        (r'$', r'ed'))),
    'NNS': ReplacementListCompiler((
        (r'([aoy])sis$', r'\1ses'),
        (r'thesis$', r'theses'),
        (r'ix$', r'ices'),
        (r'man$', r'men'),
        (r'person$', r'people'),
        (r'childe?$', r'children'),
        (r'tooth$', r'teeth'),
        (r'goose$', r'geese'),
        (r'foot$', r'feet'),
        (r'sheep$', r'sheep'),
        (r'mouse$', r'mice'),
        (r'zoon$', r'zoa'),
        (r'eau$', r'eaux'),
        (r'(l|w|kn)ife$', r'\1ives'),
        (r'lf$', r'lves'),
        (r'eaf$', r'eaves'),
        (r'([^\'][sxz]|sh|ch)$', r'\1es'),
        (r'([^aeiou])y$', r'\1ies'),
        (r'([^A-Z\' 0-9.,?!-])$', r'\1s'))),
    'NNSarchaic': ReplacementListCompiler((
        (r'chylde?$', r'chyldren'),
        (r'(l|w|kn)yfe?$', r'\1yves'),
        (r'([^aeiou])ye$', r'\1ies'),
        (r'([^ei])z$', r'\1z'),
        (r'ma(nne?)$', r'me\1'))),
    'JJR': ReplacementListCompiler((
        (r'e$', r'er'),
        (r'([^aeiou])y$', r'\1ier'),
        (r'([bcdfghlmnprstvwz][aeiou])([bdfglmnpstz])$', r'\1\2\2er'),
        (r'([bcdfghlmnprstvwz][aiou])r$', r'\1rrer'),
        (r'$', r'er'))),
    'JJS': ReplacementListCompiler((
        (r'e$', r'est'),
        (r'([^aeiou])y$', r'\1iest'),
        (r'([bcdfghlmnprstvwz][aeiou])([bdfglmnpstz])$', r'\1\2\2est'),
        (r'([bcdfghlmnprstvwz][aiou])r$', r'\1rrest'),
        (r'$', r'est')))
}
INFLECTION_PATTERNS['RBR'] = INFLECTION_PATTERNS['JJR']
INFLECTION_PATTERNS['RBS'] = INFLECTION_PATTERNS['JJS']
INFLECTION_PATTERNS['VBN'] = INFLECTION_PATTERNS['VBD']

COMPOUND_PATTERN = re.compile(r'^([^ -]+)([ -](of|in|with)[ -].*|-general)$', re.I)
PLURALIZED_PATTERN = re.compile(r'([^aiouys]s|men|mice|children|brethren|cattle|teeth|eaux)(| of .+)$')

ARCHAIC_ENDINGS = [
    ('NNS|VBZ', '([bcdfghjklmnprstvwz])ies', ('ys', 'yes', 'yse', 'yis')),
    ('NNS|VBZ', '([bcdfghjklmnprstvwzy])es', ('is', 'ys', 'ez', 'iz')),
    ('VBG', '([bcdfghjklmnprstvwzy])ing', ('inge', 'yng', 'ynge')),
    ('VBN|VBD', '([bcdfghjklmnprstvwz])ed', ('ede', 'id', 'yd')),
    ('VBN|VBD', '([bcdfghjklmnprstvwz])ied', ('ide', 'yde')),
    ('VBN', '([bcdfghjklmnprstvwz])en', ('yn', 'ene'))]

VERBISH = set(('VBZ', 'VBD', 'VBN', 'VBG'))
PHRASAL_VERB_PATTERN = re.compile(r'^(.{3,})([ -](up|down|back|away|in|out|off|on|to|for|by|after|against|again|with|upon))$')


class Inflection(object):

    """
    Engine to manage various ways to inflect a lemma.
    """

    def __init__(self):
        pass

    def compute_inflection(self, lemma, wordclass, archaic=None):
        """
        Compute the inflection of a lemma, for a given wordclass.

        Wordclass should use one of the following Penn Treebank codes:
        NNS, VBZ, VBG, VBN, VBD, JJR, JJS, RBR, RBS

        If anything other than a string is passed as the first argument, or
        a non-valid wordclass is passed as the second argument, the lemma
        is returned unchanged.

        Arguments:
         -- lemma (string)
         -- wordclass (Penn Treebank code, e.g. 'NNS')

        Returns a string representing the inflected form.
        """
        wordclass = wordclass.strip().upper()
        inf = lemma
        if wordclass == 'NNS':
            inf = self.pluralize(lemma, archaic=archaic)
        else:
            tail = ''
            if wordclass in VERBISH:
                match = PHRASAL_VERB_PATTERN.search(lemma)
                if match is not None:
                    lemma, tail = match.group(1, 2)
            try:
                inf = INFLECTION_PATTERNS[wordclass].edit_once(lemma)
                inf = inf + tail
            except KeyError:
                pass
        return inf

    def pluralize(self, lemma, archaic=None):
        """
        Return the plural of a singular noun.

        Returns a pluralized string
        """
        tail = ''
        cmatch = COMPOUND_PATTERN.search(lemma)
        if cmatch is not None:
            lemma = cmatch.group(1)
            tail = cmatch.group(2)
        if archaic:
            inf = INFLECTION_PATTERNS['NNSarchaic'].edit_once(lemma)
            if inf == lemma:
                inf = INFLECTION_PATTERNS['NNS'].edit_once(lemma)
        else:
            inf = INFLECTION_PATTERNS['NNS'].edit_once(lemma)
        return inf + tail

    def has_plural_form(self, lemma):
        if PLURALIZED_PATTERN.search(lemma):
            return True
        else:
            return False


class ArchaicEndings(object):

    def __init__(self):
        self.processors = []
        self.compile()

    def compile(self):
        for row in ARCHAIC_ENDINGS:
            condition = re.compile('^(' + row[0] + ')$')
            ending = re.compile('(...)' + row[1] + '$')
            replacements = []
            for replacement in row[2]:
                replacements.append(r'\1\2' + replacement)
            self.processors.append((condition, ending, replacements,))

    def process(self, form, wordclass):
        output = set()
        for condition, ending, replacements in self.processors:
            if condition.search(wordclass):
                match = ending.search(form)
                if match is not None:
                    for replacement in replacements:
                        arch_form = ending.sub(replacement, form)
                        if arch_form != form:
                            output.add(arch_form)
        return output
