"""
Quotation -- OED quotation class.

@author: James McCracken
"""

import re

from lex.oed.oedcomponent import OedComponent
from lex.oed.quotation.citation import Citation
from lex.oed.quotation.quotationtext import QuotationText


class Quotation(OedComponent):

    """
    OED quotation class.
    """

    def __init__(self, node):
        OedComponent.__init__(self, node)
        self._citation = None
        self._text = None

    @property
    def citation(self):
        """
        Return the Citation object for this quotation
        """
        if self._citation is None:
            self._citation = Citation(self.node.find('./cit'))
        return self._citation

    @property
    def year(self):
        """
        Return the quotation date, as an integer.
        """
        return self.citation.year

    @property
    def date(self):
        """
        Return the quotation date, as an integer (same as Quotation.year).
        """
        return self.citation.year

    @property
    def text(self):
        """
        Return the QuotationText object for this quotation
        """
        if self._text is None:
            self._text = QuotationText(self.node.find('.//qt'), self.year)
        return self._text

    #==========================================================
    # Test attributes and characteristic of the quotation
    #==========================================================

    def is_textless(self):
        return self.text.is_empty()

    def is_suppressed(self):
        """
        Return True if this is a suppressed quotation
        """
        if self.node.get('supp') or self.node.get('suppressed'):
            return True
        else:
            return False

    def is_bracketed(self):
        """
        Return True if this is a square-bracketed quotation
        """
        info_text = self.node.get('info', 'no').lower()
        if info_text in ('yes', 'intro'):
            return True
        else:
            return False

    def is_modernized_text(self):
        """
        Return True if this is a marked as being modernized text
        """
        return self.citation.is_modernized_text()

    def is_electronic_text(self):
        """
        Return True if this is a marked as being electronic text
        """
        return self.citation.is_electronic_text()

    def is_title_quotation(self):
        """
        Return true if the quotation is the title of the text
        (i.e. citation contains <tt>title</tt>)
        """
        return self.citation.is_title_quotation()
