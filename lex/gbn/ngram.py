"""
Ngram
"""

import re

from lex.gbn.frequency import Frequency, range_parser
from stringtools import lexical_sort

frequency_manager = Frequency()

DECADE_PATTERN = re.compile(r'^(1[5-9]\d0|20\d0):\d+$')
LONGS_RATIO = 0.1
LONGS_RATIO_CAP = 0.05

WORDCLASS_MAPS = {
    'NOUN': {'NN', 'NNS', 'NP', 'NOUN'},
    'VERB': {'VB', 'VBZ', 'VBD', 'VBN', 'VBG', 'MD', 'VERB'},
    'ADJ': {'JJ', 'JJR', 'JJS', 'ADJ', 'ADJECTIVE'},
    'ADV': {'RB', 'RBR', 'RBS', 'WRB', 'ADV', 'ADVERB'},
    'PRON': {'PP', 'PP$', 'WP$', 'PRON', 'PRONOUN'},
    'CONJ': {'CC', 'CONJ', 'CONJUNCTION'},
    'DET': {'DT', 'PDT', 'WDT', 'DETERMINER'},
    'ADP': {'IN',},
    'NUM': {'CD',},
    'X': {'UH',},
}
WORDCLASS_TO_PENN = {
    'NOUN': 'NN',
    'VERB': 'VB',
    'ADJ': 'JJ',
    'ADV': 'RB',
    'PRON': 'PP',
    'CONJ': 'CC',
    'DET': 'DT',
    'ADP': 'IN',
    'NUM': 'CD',
    'X': 'UH',
}


class Ngram(object):

    """
    Class for individual ngrams from the Google Books data.

    To save on memory, the Ngram class is really just a container for
    a list of data (self.data). Data is stored as follows:
        0: line
        1: source_lemma
        2: working_lemma
        3: sortcode
        4: decades [dict of decade:value pairs]
        5: gram_count
        6: wordclass
        7: ratio (not usually populated - only used when arbitrating
            between homographs)
    """

    __slots__ = ['data', 'ranges']

    def __init__(self, line, gramCount=1):
        self.data = _parse_line(line, int(gramCount))
        self.ranges = {}

    @property
    def line(self):
        return self.data[0]

    @line.setter
    def line(self, value):
        self.data[0] = value

    @property
    def source_lemma(self):
        return self.data[1]
    # No setter for source_lemma - this is kept unchanged as a record
    #  of what was originally passed in

    @property
    def lemma(self):
        return self.data[2]

    @lemma.setter
    def lemma(self, value):
        self.data[2] = value
        self.recompute_sortcode()

    @property
    def sortcode(self):
        return self.data[3]

    @sortcode.setter
    def sortcode(self, value):
        self.data[3] = value

    def recompute_sortcode(self):
        self.sortcode = lexical_sort(self.lemma)

    @property
    def gram_count(self):
        return self.data[5]

    @property
    def wordclass(self):
        return self.data[6]

    @wordclass.setter
    def wordclass(self, value):
        self.data[6] = value

    def is_unclassified(self):
        return self.wordclass == 'ALL' or not self.wordclass

    def signature(self):
        return self.lemma, self.wordclass

    @property
    def ratio(self):
        return self.data[7]

    @ratio.setter
    def ratio(self, value):
        self.data[7] = value

    @property
    def decades(self):
        return self.data[4]

    def decade_count(self, year):
        try:
            return self.decades[year]
        except KeyError:
            return 0

    def total_count(self):
        return sum(self.decades.values())

    def range_count(self, range_string):
        if not range_string in self.ranges:
            start, end = range_parser(range_string)
            total = 0
            if start and not end:
                dec = (start//10) * 10
                total = self.decade_count(dec)
            elif start and end and end > start:
                for k in self.decades:
                    if k >= start and k <= end:
                        total += self.decades[k]
            self.ranges[range_string] = total
        return self.ranges[range_string]

    def frequency(self, range):
        return frequency_manager.frequency_per_million(
            count=self.range_count(range),
            range=range,
            gram=self.gram_count,
        )

    def decade_frequency(self, year):
        return frequency_manager.frequency_per_million(
            count=self.decade_count(year),
            decade=year,
            gram=self.gram_count,
        )

    def merge(self, other):
        for decade in other.decades:
            if not decade in self.decades:
                self.decades[decade] = 0
            self.decades[decade] += other.decades[decade]
        self.refresh_line()

    def refresh_line(self):
        decades_string = '\t'.join(['%d:%d' % (dec, value) for dec, value
                                    in sorted(self.decades.items())])
        self.line = '%s\t%s\t%s\t%s' % (self.sortcode,
                                        self.lemma,
                                        self.wordclass,
                                        decades_string)

    def has_longs_signature(self):
        tmp = self.lemma + ' '
        tmp = re.sub(r'\'s? ', ' ', tmp)
        tmp = tmp.replace('f ', ' ').strip()
        if (tmp.count('s') == 0 and
                tmp.count('f') > 0 and
                self.frequency('1820-1869') < self.frequency('1740-1789')):
            ratio = self.frequency('1820-1869') / self.frequency('1740-1789')
            if (ratio < LONGS_RATIO_CAP or
                    (re.search(r'^[A-Z][a-z]+( |$)', self.lemma) and
                     ratio < LONGS_RATIO)):
                return True
        return False

    @property
    def initial(self):
        if self.sortcode:
            return self.sortcode[0]
        else:
            return 'z'

    @property
    def prefix(self):
        if len(self.sortcode) >= 3:
            return self.sortcode[0:3]
        elif len(self.sortcode) == 2:
            return self.sortcode + '0'
        elif len(self.sortcode) == 1:
            return self.sortcode + '00'
        else:
            return 'zzz'

    def matches_wordclass(self, penn):
        if (self.wordclass and
                self.wordclass in WORDCLASS_MAPS and
                penn.upper() in WORDCLASS_MAPS[self.wordclass]):
            return True
        else:
            return False

    def penn_wordclass(self):
        try:
            return WORDCLASS_TO_PENN[self.wordclass]
        except KeyError:
            return None


def _parse_line(line, gram_count):
    line = line.strip()
    parts = line.split('\t')

    decades = {}
    while parts and DECADE_PATTERN.search(parts[-1]):
        p = parts.pop()
        decade, score = p.split(':')
        decades[int(decade)] = int(score)

    if len(parts) == 3:
        sortcode = parts[0]
        source_lemma = parts[1]
        wordclass = parts[2]
    elif len(parts) == 1:
        sortcode = None
        source_lemma = parts[0]
        wordclass = 'ALL'
    elif len(parts) == 2 and gram_count != 3:
        sortcode = None
        source_lemma = parts[0]
        wordclass = parts[1]
    elif len(parts) == 2:
        sortcode = parts[0]
        source_lemma = parts[1]
        wordclass = 'ALL'
    if gram_count >= 3:
        source_lemma = source_lemma.replace(' - ', '-')

    if not sortcode:
        sortcode = lexical_sort(source_lemma)

    return [line, source_lemma, source_lemma, sortcode, decades,
            gram_count, wordclass, None]
