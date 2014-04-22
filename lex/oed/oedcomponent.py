"""
Base class for OED entries and components of OED entries
(quotations, senses, etc.)

Author: James McCracken
"""

from lex.entrycomponent import EntryComponent

LEMSECT_MARKERS = {
    'compound': {'compounds', 'special_uses'},
    'derivative': {'derivatives', },
    'phrase': {'phrases', 'phrasal_verbs'},
}


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

    #----------------------------------------------------
    # Methods used to test the position of the component within the entry
    #----------------------------------------------------

    def is_in_sensesect(self):
        """
        Return True if this component is inside the entry's <senseSect>
        Return False otherwise.
        """
        if self.node.iterancestors(tag='senseSect'):
            return True
        else:
            return False

    def is_in_vfsect(self):
        """
        Return True if this component is inside the entry's <vfSect>
        (or <vfSectLoose>)
        Return False otherwise.
        """
        if self.node.iterancestors(tag='vfSect'):
            return True
        if self.node.iterancestors(tag='vfSectLoose'):
            return True
        else:
            return False

    def is_in_revsect(self):
        """
        Return True if this component is inside a <revSect>
        Return False otherwise.
        """
        if self.node.iterancestors(tag='revSect'):
            return True
        else:
            return False

    def is_in_lemsect(self):
        """
        Return True if this component is inside a <lemSect>
        Return False otherwise.
        """
        if self.node.iterancestors(tag='lemSect'):
            return True
        else:
            return False

    def is_in_derivatives_section(self):
        """
        Return True if this component is inside a derivatives <lemSect>
        Return False otherwise.
        """
        return self._is_in_typed_lemsect('derivative')

    def is_in_compounds_section(self):
        """
        Return True if this component is inside a compounds <lemSect>
        Return False otherwise.
        """
        return self._is_in_typed_lemsect('compound')

    def is_in_phrases_section(self):
        """
        Return True if this component is inside a phrases or
        phrasal verbs <lemSect>
        Return False otherwise.
        """
        return self._is_in_typed_lemsect('phrase')

    def _is_in_typed_lemsect(self, ltype):
        """
        Return True if this component is in a lemSect of a given type.
        Return False otherwise.
        """
        for ancestor in self.node.iterancestors(tag='lemSect'):
            if ancestor.get('type', '').lower() in LEMSECT_MARKERS[ltype]:
                return True
        return False
