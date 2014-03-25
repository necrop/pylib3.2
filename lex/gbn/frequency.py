"""
Frequency
"""

import os
import re
from collections import defaultdict

LINE_PARSER = re.compile(r'^([12]\d\d\d)\t(\d+)\t(\d+)\t(\d+)$')
RANGE_PATTERNS = (
    re.compile(r'^(\d{4})-(\d{1,4})$'),
    re.compile(r'^\d{4}$'),
    re.compile(r'^\d{4}-$'),
    re.compile(r'^-\d{4}$'),
)


class Frequency(object):

    """
    Frequency class.
    """

    map = {}
    counts = {}
    ranges = defaultdict(lambda: defaultdict(dict))

    def __init__(self):
        if not Frequency.counts:
            self._parse_files()

    def total(self, **kwargs):
        id, type = self._argparser(**kwargs)
        total = sum([Frequency.counts[id][type][yr] for yr in
                     Frequency.counts[id][type].keys()])
        return total

    def count(self, **kwargs):
        id, type = _argparser(**kwargs)
        year = kwargs.get('year', None)
        if (year is not None and
                year in Frequency.counts[id][type]):
            return Frequency.counts[id][type][year]
        return 0

    def range_count(self, **kwargs):
        id, type = _argparser(**kwargs)
        range = kwargs.get('range', None)
        decade = kwargs.get('decade', None)
        if range is None and decade is None:
            return 0
        else:
            if decade is not None:
                decade = (decade//10) * 10
                start, end = (decade, decade + 9)
            else:
                start, end = range_parser(range)
            range_tuple = (start, end)
            if not range_tuple in Frequency.ranges[id][type]:
                if ((start and not end) or
                        (start and start == end)):
                    total = self.count(year=start, **kwargs)
                elif start and end and end > start:
                    total = 0
                    year = start
                    while year <= end:
                        total += self.count(year=year, **kwargs)
                        year += 1
                else:
                    total = 0
                Frequency.ranges[id][type][range_tuple] = total
            return Frequency.ranges[id][type][range_tuple]

    def millions(self, **kwargs):
        return self.range_count(**kwargs) / 1000000

    def billions(self, **kwargs):
        return self.millions(**kwargs) / 1000

    def frequency_per_million(self, **kwargs):
        count = kwargs.get('count', 0)
        if self.millions(**kwargs) == 0:
            return 0
        else:
            return count / self.millions(**kwargs)

    def decade_frequency(self, **kwargs):
        return self.frequency_per_million(**kwargs)

    def _parse_files(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data')

        with open(os.path.join(data_dir, 'totalsmap.txt')) as filehandle:
            for line in filehandle:
                if line.startswith('#') or not ':' in line:
                    continue
                parts = [p.strip() for p in line.split(':')]
                if len(parts) == 2:
                    Frequency.map[parts[0]] = parts[1]

        files = [f for f in os.listdir(data_dir)
                 if f.startswith('totalcounts_') and f.endswith('.txt')]
        for filename in files:
            id = filename.replace('.txt', '').replace('totalcounts_', '')
            Frequency.counts[id] = {'tokens': {}, 'pages': {}, 'books': {},}
            with open(os.path.join(data_dir, filename)) as filehandle:
                for line in filehandle:
                    m = LINE_PARSER.search(line)
                    if m is None:
                        continue
                    year = int(m.group(1))
                    Frequency.counts[id]['tokens'][year] = int(m.group(2))
                    Frequency.counts[id]['pages'][year] = int(m.group(3))
                    Frequency.counts[id]['books'][year] = int(m.group(4))


def _argparser(**kwargs):
    idref = str(kwargs.get('gram', 'default'))
    mode = kwargs.get('type', 'tokens')
    if not idref in Frequency.map:
        idref = 'default'
    id = Frequency.map[idref]
    if not mode in Frequency.counts[id]:
        mode = 'tokens'
    return id, mode


def range_parser(range):
    """
    Parse a range string (something like '1730-50') into
    a (start, end) tuple.

    '1730-50' -> (1730, 1750)
    """
    if not range:
        return None, None

    if isinstance(range, int):
        return range, None
    elif isinstance(range, str):
        rangematch = RANGE_PATTERNS[0].search(range)
        if rangematch is not None:
            start = int(rangematch.group(1))
            end = int(rangematch.group(2))
            if end < 10:
                decade = (start//10) * 10
                end += decade
            elif end < 100:
                century = (start//100) * 100
                end += century
            return start, end
        if RANGE_PATTERNS[1].search(range):
            return int(range), None
        if RANGE_PATTERNS[2].search(range):
            return int(range.strip('-')), 2020
        if RANGE_PATTERNS[3].search(range):
            return 1500, int(range.strip('-'))
    return None, None

