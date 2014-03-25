"""
OdeComponent -- Base class for ODE/NOAD entries and components of entries

@author: James McCracken
"""

from lxml import etree  # @UnresolvedImport

from lex.entrycomponent import EntryComponent
from lex.definition import Definition

# Identifiers for ODE/NOAD used in cross-project links
IDENTIFIERS = set(('Oxford Dictionary of English',
                   'New Oxford American Dictionary',
                   'M-EN_GB-MSDICT-00008',
                   'M-EN_US-MSDICT-00008',))


class OdeComponent(EntryComponent):

    """
    ODE/NOAD component base class.
    """

    def __init__(self, node):
        EntryComponent.__init__(self, node)

    def definition_manager(self):
        """
        Manager for the first definition found in the component.
        """
        try:
            return self._definition_object
        except AttributeError:
            def_node = self.node.find('.//df')
            if def_node is None:
                def_node = self.node.find('.//xrg')
            if def_node is None:
                def_node = etree.Element('df')
            self._definition_object = Definition(def_node)
            return self._definition_object

    def definition(self, length=None):
        """
        Return the text of the first definition.
        """
        return self.definition_manager().text(length=length)

    def cross_project_links(self):
        """
        Return a list of CrossProjectLink objects based in <linkGroup>
        elements found in this component.
        """
        try:
            return self._xp_links
        except AttributeError:
            self._xp_links = [CrossProjectLink(n) for n in
                              self.node.findall('.//crossProject/linkGroup')]
            return self._xp_links

    def paired_link(self):
        """
        Return the first CrossProjectLink object that points from
        ODE to NOAD, or vice versa.

        (Returns None if there's no link.)
        """
        for link in self.cross_project_links():
            if link.is_ode_noad_link() and link.lexid is not None:
                return link
        return None

    def paired_id(self):
        """
        Return the entry ID of the ODE or NOAD entry with which this
        component is linked (if any).

        Returns None if there's no link.
        """
        if self.paired_link() is not None:
            return self.paired_link().entry_id()
        else:
            return None

    def topics(self):
        """
        Return the set of domClass topics found in the component.
        """
        return set([n.text for n in self.node.xpath('.//domClass')
                    if n.text is not None])


class CrossProjectLink(object):

    """
    Cross-project link (typically between ODE and NOAD)
    """

    def __init__(self, node):
        self.project_name = node.get('project')
        xr_node = node.find('./xr')
        if xr_node is not None:
            self.lexid = xr_node.get('targetid')
            self.code = xr_node.get('targetProjectCode')
        else:
            self.lexid = None
            self.project_code = None

    def entry_id(self):
        """
        Return the ID of the target entry.
        """
        if self.lexid is not None:
            return self.lexid.split('.')[0]
        else:
            return None

    def is_ode_noad_link(self):
        """
        Return True if this is a link between ODE and NOAD.
        """
        if self.project_name in IDENTIFIERS:
            return True
        else:
            return False

