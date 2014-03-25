"""
mmhcache - Loads the morphology metadata hub into memory
"""

import os
import re
import string
from collections import namedtuple, defaultdict

from lxml import etree

from lex import lexconfig
from stringtools import lexical_sort

IN_DIR = lexconfig.MORPHOLOGY_DIR
PREFIXES = re.compile(r'^(over|under|extra|semi|pseudo|super|ultra|anti|hyper|contra|infra|post|auto|re|mis|dis|sub|ex|un|pre)([a-z]+)$', re.I)
NOUN_PHRASES = re.compile(r'(^[a-z]+)(-((in|with|of)-[a-z-]+|general))$', re.I)
VERB_PHRASES = re.compile(r'^([a-z]+)(-(up|in|on|off|to|for|by|out))$', re.I)

MorphUnit = namedtuple('MorphUnit', ['form', 'wordclass',])


class MmhCache(object):

    """
    Load and query the morphology metadata hub
    """

    cache = defaultdict(list)

    def __init__(self):
        if not MmhCache.cache:
            self.load_cache()

    def load_cache(self):
        if MmhCache.cache:
            return
        for letter in string.ascii_lowercase:
            filename = os.path.join(IN_DIR, letter + '.xml')
            doc = etree.parse(filename)
            for node in doc.findall('//morphSet'):
                morphset = MorphSet(node=node)
                MmhCache.cache[morphset.sortcode].append(morphset)

    def cache_size(self):
        return len(MmhCache.cache)

    def find_sortcode(self, sortcode):
        if sortcode in MmhCache.cache:
            return MmhCache.cache[sortcode]
        else:
            return []

    def find_lemma(self, lemma, **kwargs):
        wordclass = kwargs.get('wordclass')
        locale = kwargs.get('locale')
        candidates = self.find_sortcode(lexical_sort(lemma))
        candidates = [c for c in candidates if (c.lemma == lemma and
                      (wordclass is None or c.wordclass == wordclass))]
        if locale == 'uk':
            candidates = [c for c in candidates if c.variant_type != 'us']
        if locale == 'us':
            candidates = [c for c in candidates if c.variant_type != 'uk']

        # Sort so that the longest and highest-scoring morphsets are at the top
        candidates.sort(key=lambda c: c.score, reverse=True)
        candidates.sort(key=len, reverse=True)
        return candidates

    def inflect_fuzzy(self, lemma, **kwargs):
        wordclass = kwargs.get('wordclass')
        locale = kwargs.get('locale')

        morphsets = self.find_lemma(lemma, wordclass=wordclass, locale=locale)

        if not morphsets and wordclass in ('NN', 'VB'):
            words = lemma.split()
            if wordclass == 'NN':
                if len(words) == 1:
                    targets = [0, ]
                elif len(words) == 3 and words[1] in ('and', 'or'):
                    targets = [0, 2]
                elif len(words) >= 3 and words[1] in ('of', 'in', 'with'):
                    targets = [0, ]
                else:
                    targets = [len(words)-1, ]
            if wordclass == 'VB':
                if len(words) == 1:
                    targets = [0, ]
                elif len(words) == 3 and words[1] in ('and', 'or'):
                    targets = [0, 2]
                elif words[0] in ('not',):
                    targets = [1, ]
                else:
                    targets = [0, ]

            local_morphsets = {t: self._fuzzy_match(words[t], wordclass,
                               locale) for t in targets}
            if any([m is None for m in local_morphsets.values()]):
                pass
            else:
                if wordclass == 'NN':
                    inflections = ('NN', 'NNS')
                elif wordclass == 'VB':
                    inflections = ('VB', 'VBZ', 'VBG', 'VBD', 'VBN')
                morphunits = []
                for infclass in inflections:
                    words2 = []
                    for i, word in enumerate(words):
                        if i in local_morphsets:
                            morphset = local_morphsets[i][0]
                            new_word = morphset.form_for(infclass)
                            if wordclass == 'VB' and not new_word:
                                new_word = word
                        else:
                            new_word = word
                        words2.append(new_word)
                    if not None in words2:
                        inflected_lemma = ' '.join(words2)
                        morphunits.append(MorphUnit(inflected_lemma, infclass))
                morphsets = [MorphSet(morphunits=morphunits), ]
                if wordclass == 'VB' and lemma.startswith('to '):
                    morphsets = []

        return morphsets

    def _fuzzy_match(self, lemma, wordclass, locale):
        morphsets = self.find_lemma(lemma,
                                    wordclass=wordclass,
                                    locale=locale)
        if morphsets:
            return morphsets

        target = None
        if wordclass == 'VB':
            match1 = VERB_PHRASES.search(lemma)
        else:
            match1 = NOUN_PHRASES.search(lemma)
        match2 = re.search(r'^(.*-)(.+?)$', lemma, re.I)
        match3 = PREFIXES.search(lemma)
        if match1:
            prefix, target, suffix = ('', match1.group(1), match1.group(2))
        elif match2:
            prefix, target, suffix = (match2.group(1), match2.group(2), '')
        elif match3:
            prefix, target, suffix = (match3.group(1), match3.group(2), '')
        if target:
            morphsets = self.find_lemma(target,
                                        wordclass=wordclass,
                                        locale=locale)

        # Create new versions of the morphsets with prefix and suffix
        # added back on
        if morphsets:
            morphsets2 = []
            for morphset in morphsets:
                morphunits = [MorphUnit(prefix + unit.form + suffix,
                              unit.wordclass) for unit in morphset.morphunits]
                morphsets2.append(MorphSet(morphunits=morphunits,
                                           variant_type=morphset.variant_type))
            return morphsets2
        else:
            return None


class MorphSet(object):

    def __init__(self, **kwargs):
        node = kwargs.get('node', None)
        morphunits = kwargs.get('morphunits', None)
        if node is not None:
            self.sortcode = node.get('sort')
            self.variant_type = node.get('variantType')
            self.id = node.get('id')
            self.morphunits = [MorphUnit(n.findtext('./wordForm'), n.get('pos'))
                               for n in node.findall('./morphUnit')]
            self.score = int(node.get('score'))*2 or 0
        elif morphunits is not None:
            self.morphunits = morphunits
            self.sortcode = lexical_sort(self.lemma)
            self.variant_type = kwargs.get('variant_type', 'default')
            self.score = kwargs.get('score', 0)
            self.id = kwargs.get('id', 0)

        self.source = self.lemma  # this should remain unchanged
        if self.variant_type != 'us':
            self.score += 1
        self.computed = False

    def __len__(self):
        return len(self.morphunits)

    @property
    def lemma(self):
        return self.morphunits[0].form

    @property
    def wordclass(self):
        return self.morphunits[0].wordclass

    def length(self):
        return len(self.morphunits)

    def contains(self, text):
        if any([unit.form == text or unit.wordclass == text
                for unit in self.morphunits]):
            return True
        else:
            return False

    def form_for(self, wordclass):
        """
        Return the frm corresponding to a given wordclass (or None if the
        wordclass is not found).
        """
        for unit in self.morphunits:
            if unit.wordclass == wordclass:
                return unit.form
        return None

    def to_string(self):
        text = '%s (%s, %s)\t|%s|\n\t%s\n\tscore: %d' % (self.lemma,
                                                         self.wordclass,
                                                         self.source,
                                                         self.sortcode,
                                                         self.variant_type,
                                                         self.score)
        for mu in self.morphunits:
            text += '\n\t\t%s (%s)' % (mu.form, mu.wordclass)
        return text

    def add_affixes(self, prefix, suffix):
        self.morphunits = [MorphUnit(prefix + unit.form + suffix, unit.wordclass)
                           for unit in self.morphunits]
        # Update the sortcode based on the new first lemma
        self.sortcode = lexical_sort(self.lemma)


