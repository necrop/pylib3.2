"""
Wordclass -- Class for managing and translating lexical wordclasses

@author: James McCracken
"""

import os
import csv

from lxml import etree  # @UnresolvedImport


WORDCLASS_FILE = 'wordclass_map.csv'
INFLECTION_FILE = {'inflections_max': 'inflection_map_max.csv',
                   'inflections_min': 'inflection_map_min.csv'}


class Wordclass(object):

    """
    Class for managing and translating lexical wordclasses (parts of speech).
    """

    wordclass_map = dict()

    def __init__(self, wclass):
        if not Wordclass.wordclass_map:
            self._load_map()
        wclass = sanitize(wclass)
        self.source = wclass
        self.penn = self.map_to_penn()

    def map_to_penn(self):
        """
        Return the Penn equivalent of self.source
        """
        try:
            return Wordclass.wordclass_map[self.source]['penn']
        except KeyError:
            try:
                return Wordclass.wordclass_map[self.source.upper()]['penn']
            except KeyError:
                try:
                    return Wordclass.wordclass_map[self.source.lower()]['penn']
                except KeyError:
                    return None

    def equivalent(self, style, default=None):
        style = style.lower()
        try:
            return Wordclass.wordclass_map[self.penn][style]
        except KeyError:
            return default

    def inflections_max(self):
        return self._inflections('max')

    def inflections_min(self):
        return self._inflections('min')

    def _inflections(self, mode):
        try:
            return Wordclass.wordclass_map[self.penn]['inflections_%s' % mode]
        except KeyError:
            return tuple()

    def to_xml(self):
        return etree.Element('wordclass',
                             penn=self.penn,
                             claws=self.equivalent('claws'),
                             description=self.equivalent('description'))

    def _load_map(self):
        filepath = os.path.dirname(__file__)

        infmap = dict()
        for itype in ('inflections_max', 'inflections_min'):
            infmap[itype] = dict()
            reader = csv.reader(open(os.path.join(
                    filepath, INFLECTION_FILE[itype])))
            for row in reader:
                row = [i for i in row if i]
                infmap[itype][row[0]] = row

        reader = csv.reader(open(os.path.join(filepath, WORDCLASS_FILE)))
        headers = None
        for row in reader:
            if row[0] == 'Penn':
                headers = row[:]
            else:
                local_dict = {field.lower(): value for field, value
                              in zip(headers, row)}
                local_dict['claws'] = local_dict['claws5']

                for itype in ('inflections_max', 'inflections_min'):
                    try:
                        local_dict[itype] = infmap[itype][row[0]]
                    except KeyError:
                        local_dict[itype] = [row[0]]
                for i in (0, 2, 3, 4, 5, 6, 7):
                    if row[i]:
                        Wordclass.wordclass_map[row[i]] = local_dict


def sanitize(wclass):
    """
    Sanitize the input wordclass code to Penn standards.
    """
    wclass = wclass.strip()
    if wclass == 'NNP' or wclass == 'NNPS' or wclass == 'NPS':
        wclass = 'NP'
    return wclass
