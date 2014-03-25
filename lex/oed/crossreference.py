"""
CrossReference -- OED cross-reference class

@author: James McCracken
"""

import re

from lex.oed.oedcomponent import OedComponent


class CrossReference(OedComponent):

    """
    OED cross-reference class.
    """

    def __init__(self, node):
        OedComponent.__init__(self, node)

    def target_type(self):
        """
        Return the type of element being targeted. One of:
         -- 'quotation'
         -- 'lemma'
         -- 'sense'
         -- 'entry'
         -- 'unknown'
        """
        if self.node.find('.//xd') is not None:
            return 'quotation'
        elif self.node.find('.//xlem') is not None:
            return 'lemma'
        elif self.node.find('.//xs') is not None:
            return 'sense'
        elif self.node.find('.//xhw') is not None:
            return 'entry'
        else:
            return 'unknown'

    def is_internal(self):
        """
        Return True if this is an internal cross-reference, i.e. pointing
        elsewhere in the same entry.
        """
        if self.node.find('.//xhw') is None:
            return True
        else:
            return False

    def lemma(self):
        """
        Return the headword or lemma being targeted.
        """
        return self.node.findtext('.//xlem') or self.node.findtext('.//xhw')

    def date(self):
        """
        Return the date of the quotation being targeted (if any).

        Returns a 4-digit integer or None.
        """
        xd_text = self.node.findtext('.//xd')
        if xd_text is not None:
            match = re.search(r'(\d{4})', xd_text)
            if match is not None:
                return int(match.group(1))
        return None

    def refentry(self):
        """
        Return the entry ID of the target.
        """
        try:
            return int(self.node.get('refentry'))
        except (ValueError, TypeError):
            return None

    entry_id = refentry
    target_id = refentry

    def refid(self):
        """
        Return the node ID of the target.
        """
        try:
            return int(self.node.get('refid'))
        except (ValueError, TypeError):
            return None

    node_id = refid

