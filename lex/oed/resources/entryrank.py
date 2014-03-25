"""
EntryRank
"""

import os
import csv
from math import log, log10
from collections import deque

from lex import lexconfig
from lex.oed.resources.frequencyiterator import FrequencyIterator

DEFAULT_FILE = os.path.join(lexconfig.OED_RESOURCES_DIR, 'entry_rank.csv')


class EntryRank(object):
    entries = []
    index = {}

    def __init__(self, **kwargs):
        self.ranking_file = kwargs.get('ranking_file') or DEFAULT_FILE

    def rank_list(self):
        if not EntryRank.entries:
            self._load()
        return EntryRank.entries

    def rank_list_sample(self):
        sample = []
        stack = deque([], 10)
        for e in self.rank_list():
            stack.appendleft(e)
            if (not e.rank % 1000 or
                    (e.rank < 20000 and not e.rank % 200) or
                    (e.rank < 5000 and not e.rank % 100) or
                    (e.rank < 1000 and not e.rank % 50) or
                    (e.rank < 500 and not e.rank % 10) or
                    (e.rank < 100 and not e.rank % 5) or
                    (e.rank < 20 and not e.rank % 2) or
                    e.rank < 10):
                sample.append((e, list(stack)[:]))
        return sample

    def entry(self, xrid):
        if not EntryRank.entries:
            self._load()
        xrid = int(xrid)
        try:
            return EntryRank.index[xrid]
        except KeyError:
            return None

    def _load(self):
        with (open(self.ranking_file, 'r')) as filehandle:
            csv_reader = csv.reader(filehandle)
            for row in csv_reader:
                EntryRank.entries.append(Entry(row))
        EntryRank.index = {e.id: e for e in EntryRank.entries}


class Entry(object):
    count = 0
    min_frequency = 5e-07

    def __init__(self, row):
        Entry.count += 1
        self.label = row[0]
        self.lemma = row[1]
        self.id = int(row[2])
        self.frequency = float(row[3])
        self.rank = Entry.count

    def limited_frequency(self):
        return max(self.frequency, Entry.min_frequency)

    def log_e(self):
        return log(self.limited_frequency())

    def log_10(self):
        return log10(self.limited_frequency())

    def num_entries(self):
        return Entry.count

    def percentile(self):
        return int(100 * (float(self.rank) / Entry.count))


def store_rankings(**kwargs):
    in_dir = kwargs.get('in_dir')
    out_file = kwargs.get('out_file') or DEFAULT_FILE

    iterator = FrequencyIterator(in_dir=in_dir,
                                 letters=None,
                                 message='Compiling frequency ranking')

    entryrank = []
    for e in iterator.iterate():
        if e.has_frequency_table():
            entryrank.append((
                e.label,
                e.lemma,
                e.xrid,
                e.frequency_table().frequency(),
            ))

    entryrank = sorted(entryrank, key=lambda e: e[3], reverse=True)
    with (open(out_file, 'w')) as filehandle:
        csv_writer = csv.writer(filehandle)
        for row in entryrank:
            csv_writer.writerow(row)


if __name__ == '__main__':
    store_rankings()
