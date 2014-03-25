"""
Etymology -- ODE/NOAD etymology

@author: James McCracken
"""

import re

from lxml import etree  # @UnresolvedImport

from lex.odo.odecomponent import OdeComponent


DATE_PATTERNS = (
    ('year', re.compile(r'^(\d{4})[s :]')),
    ('century', re.compile(r'^(\d\d)th cent')),
    ('part-century', re.compile(r'^(early|mid|late) (\d\d)th cent')),
    ('ME', re.compile(r'^Middle English', re.I)),
    ('OE', re.compile(r'^(early |late |)Old English', re.I)),
    ('ME period', re.compile(r'^(early|late) Middle English', re.I)),)


class Etymology(OdeComponent):

    """
    ODE/NOAD etymology.
    """

    def __init__(self, node):
        OdeComponent.__init__(self, node)

    def text(self):
        try:
            return self._text
        except AttributeError:
            self._text = etree.tostring(self.node,
                                        method='text',
                                        encoding='unicode')
            return self._text

    def date(self):
        try:
            return self._date
        except AttributeError:
            self._date = None
            for name, pattern in DATE_PATTERNS:
                match = pattern.search(self.text())
                if match is not None:
                    self._date = _parse_date_match(name, match)
                    break
            return self._date


def _parse_date_match(name, match):
    year = None
    if name == 'year':
        year = int(match.group(1))
    elif name == 'century':
        year = (int(match.group(1)) - 1) * 100
        year += 50
    elif name == 'part-century':
        year = (int(match.group(2)) - 1) * 100
        if match.group(1) == 'early':
            year += 25
        elif match.group(1) == 'mid':
            year += 50
        elif match.group(1) == 'late':
            year += 75
    elif name == 'ME':
        year = 1300
    elif name == 'OE':
        year = 1100
    elif name == 'ME period':
        if match.group(1).lower() == 'early':
            year = 1200
        elif match.group(1).lower() == 'late':
            year = 1400
    return year
