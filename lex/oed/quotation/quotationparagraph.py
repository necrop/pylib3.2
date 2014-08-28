"""
QuotationParagraph -- OED quotation paragraph class

@author: James McCracken
"""

from lex.oed.oedcomponent import OedComponent
from lex.oed.quotation.quotation import Quotation

OBS_CUTOFF = 1800
END_DATE = 2020
GAPCHECKER_START = 1650


class QuotationParagraph(OedComponent):

    """
    OED quotation paragraph class.

    Container for a list of quotations grouped in a <qp> element.
    """

    def __init__(self, node):
        OedComponent.__init__(self, node)
        self.obs = None
        self._quotations = None

    def quotations(self, **kwargs):
        if self._quotations is None:
            self._quotations = [Quotation(q) for q in self.node.findall('./q')]
            self._quotations.sort(key=lambda q: q.year)

        quotations = self._quotations[:]
        if kwargs.get('strip_suppressed', True):
            quotations = [q for q in quotations if not q.is_suppressed()]
        if kwargs.get('strip_undated'):
            quotations = [q for q in quotations if q.year > 0]
        if kwargs.get('strip_bracketed'):
            quotations = [q for q in quotations if not q.is_bracketed()]
        if kwargs.get('thinned') or kwargs.get('thin'):
            quotations = _thin_quotations(quotations)
        return quotations

    def is_obsolete(self):
        if self.obs is not None:
            return self.obs
        elif (self.quotations(strip_undated=True) and
                self.quotations(strip_undated=True)[-1] < OBS_CUTOFF):
            return True
        else:
            return False

    def set_obsolete(self, val):
        self.obs = bool(val)

    def is_all_glossary(self):
        if not self.quotations():
            return False
        elif any([q.citation.is_glossary() for q in self.quotations()]):
            return False
        else:
            return True

    def label(self):
        return self.node.findtext('./qla')

    def lifespan(self, **kwargs):
        if not self.quotations(dated=True):
            return 0
        elif kwargs.get('projected') and not self.is_obsolete():
            return END_DATE - self.quotations(strip_undated=True)[0].year
        elif len(self.quotations(strip_undated=True)) == 1:
            return 1
        else:
            return (self.quotations(strip_undated=True)[-1] -
                    self.quotations(strip_undated=True)[0])

    def largest_gap(self, **kwargs):
        start = kwargs.get('start', GAPCHECKER_START)
        quotations = [q for q in self.quotations() if q.year >= start]
        if len(quotations) > 1:
            pass
        else:
            return None

    def contains_quote_from(self, **kwargs):
        """
        Test whether the quotation paragraph contains a quotation
        by a given author or from a given title.

        Keyword arguments:
            author: author name or list of author names
            title: title or list of titles
            firstOnly (optional): if True, causes the function to check
                only the *first* (non-bracketed) quotation in the qp

        At least only the keyword arguments 'author' or 'title' must
        be provided. If both are provided, they are ANDed, i.e. the
        function will only return True if the qp contains a quotation
        in which both conditions are met.

        Returns the first matching quotation (if any); otherwise
        returns False.
        """
        quotations = self.quotations(strip_bracketed=True)[:]
        if kwargs.get('start'):
            start_year = int(kwargs.get('start'))
            quotations = [q for q in quotations if q.year >= start_year]
        if (kwargs.get('firstOnly') or kwargs.get('first_only')) and quotations:
            quotations = quotations[0:1]

        if kwargs.get('author'):
            try:
                kwargs.get('author').lower()
            except AttributeError:
                authors = list(kwargs.get('author'))
            else:
                authors = list([kwargs.get('author'), ])
        else:
            authors = []
        if kwargs.get('title'):
            try:
                kwargs.get('title').lower()
            except AttributeError:
                titles = list(kwargs.get('title'))
            else:
                titles = list([kwargs.get('title'), ])
        else:
            titles = []

        matches = [q for q in quotations if
                   q.citation.contains(authors=authors, titles=titles)]
        try:
            return matches[0]
        except IndexError:
            return False


def _thin_quotations(quotations):
    """
    Thin out quotations by removing any which are less than
    ten years apart.
    """
    quotations_thinned = []
    for quotation in quotations:
        if (quotations_thinned and
                abs(quotations_thinned[-1].year - quotation.year) < 10):
            pass
        else:
            quotations_thinned.append(quotation)
    return quotations_thinned
