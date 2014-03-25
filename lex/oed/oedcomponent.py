"""
Base class for OED entries and components of OED entries
(quotations, senses, etc.)

Author: James McCracken
"""

from lex.entrycomponent import EntryComponent


class OedComponent(EntryComponent):

    """
    OED component base class
    """

    def __init__(self, node, **kwargs):
        EntryComponent.__init__(self, node, **kwargs)
        self.is_revised = False
        try:
            self.num = int(self.node.get('num', 0))
        except ValueError:
            self.num = 0
