"""
NgramFinder - find the ngram for a given word
"""

import os
from collections import defaultdict

from lex import lexconfig
from lex.gbn.ngram import Ngram
from lex.lemma import Lemma

DEFAULT_DIR = lexconfig.NGRAMS_TABLES_DIR
DEFAULT_CACHE_SIZE = 5


class NgramFinder(object):

    """
    Find the ngram for a given word
    """

    cache = {}
    cache_size = 5
    call_num = 0

    def __init__(self, **kwargs):
        self.cache_size = int(kwargs.get('cache_size', DEFAULT_CACHE_SIZE))
        self.dir = kwargs.get('dir', DEFAULT_DIR)

    def find_exact(self, word, wordclass=None):
        if wordclass is None:
            wordclass = "ALL"
        for ngram in self.generic_find(word):
            if ngram.lemma == word and ngram.wordclass == wordclass:
                return ngram
        return None

    def find_all(self, word, wordclass=None):
        ngramset = self.generic_find(word)
        if wordclass is not None:
            ngramset = [n for n in ngramset if n.wordclass == wordclass]
        return ngramset

    def generic_find(self, word):
        lemma_manager = Lemma(word)
        initial = lemma_manager.initial()
        prefix = lemma_manager.prefix()
        dsort = lemma_manager.lexical_sort()
        if not prefix in NgramFinder.cache:
            self.update_cache(initial, prefix)
        NgramFinder.call_num += 1
        NgramFinder.cache[prefix]["call_num"] = NgramFinder.call_num
        return NgramFinder.cache[prefix]["grams"].get(dsort, [])

    def update_cache(self, initial, prefix):
        # Find the cache key last used longest ago (i.e. has the lowest
        #  call number), and drop it
        while len(NgramFinder.cache.keys()) >= NgramFinder.cache_size:
            ranking = [(prefix, NgramFinder.cache[prefix]["call_num"])
                       for prefix in NgramFinder.cache]
            ranking.sort(key=lambda z: z[1])
            del(NgramFinder.cache[ranking[0][0]])

        # Create a new cache key for the current prefix
        NgramFinder.cache[prefix] = {
            "call_num": NgramFinder.call_num,
            "grams": defaultdict(list),
        }

        for gram_num in (1, 2, 3):
            fname = "%s-%dgram.txt" % (prefix, gram_num)
            filepath = os.path.join(self.dir, str(gram_num), initial, fname)
            if os.path.isfile(filepath):
                with open(filepath) as filehandle:
                    for line in filehandle:
                        n = Ngram(line, gramCount=gram_num)
                        NgramFinder.cache[prefix]["grams"][n.sortcode].append(n)
