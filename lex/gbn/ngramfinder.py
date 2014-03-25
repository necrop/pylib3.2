#-------------------------------------------------------------------------------
# Name: NgramFinder
# Purpose:
#
# Author: James McCracken
#
# Created: 12/01/2012
#-------------------------------------------------------------------------------

import glob
import re
import os
from collections import defaultdict

from .ngram import Ngram
from ..lemma import Lemma

class NgramFinder(object):
    """
    """

    cache = {}
    cache_size = 5
    call_num = 0

    def __init__(self, dir=None, cacheSize=None):
        if cacheSize is not None and isinstance(cacheSize, int):
            NgramFinder.cache_size = cacheSize
        self.dir = dir

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
        lemObj = Lemma(word)
        initial = lemObj.initial
        prefix = lemObj.prefix
        dsort = lemObj.dictionary_sort
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
            file = os.path.join(self.dir, str(gram_num), initial, fname)
            if os.path.isfile(file):
                with open(file, "r") as fh:
                    for line in fh:
                        line = line.decode("utf8")
                        n = Ngram(line, gramCount=gram_num)
                        NgramFinder.cache[prefix]["grams"][n.sortcode].append(n)
