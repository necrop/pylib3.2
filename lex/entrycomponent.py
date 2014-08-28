"""
EntryComponent -- Dictionary component base class

@author: James McCracken
"""

from collections import namedtuple
from lxml import etree  # @UnresolvedImport

LIGATURE_FIXES = (
    ('\u00e6', 'ae'),
    ('\u0153', 'oe'),
    ('\u00c6', 'Ae'),
    ('\u0152', 'Oe'),
)
Ancestor = namedtuple('Ancestor', ['tag', 'lexid'])


class EntryComponent(object):

    """
    Base class for dictionary entries and components of dictionary
    entries (quotations, senses, etc.)

    Subclassed directly by oed.oedcomponent and ode.odecomponent,
    and hence by a series of other subcomponents.
    """

    def __init__(self, node, **kwargs):
        # Test if the node is actually a string at this stage; if so,
        # it needs to be turned into a node
        try:
            node.lower()
        except AttributeError:
            pass
        else:
            fixl = (kwargs.get('fix_ligatures') or
                    kwargs.get('fixLigatures') or False)
            if fixl:
                for before, after in LIGATURE_FIXES:
                    node = node.replace(before, after)
            node = etree.fromstring(node)

        self.node = node
        self.tree = node  # for backwards compatibility
        self.attributes = node.attrib
        self.tag = node.tag

    def serialized(self):
        """
        Return the node serialized in string form.

        (Wrapper for etree.tounicode())
        """
        return etree.tounicode(self.node)

    to_string = serialized

    def as_text(self):
        """
        Return the node serialized as text (with tags removed).
        """
        return etree.tounicode(self.node, method='text')

    def strip_elements(self, elements):
        """
        Remove list of elements (named by tag) from the node.

        (Wrapper for etree.strip_elements())
        """
        etree.strip_elements(self.node, elements)

    def strip_attributes(self, attributes):
        """
        Remove list of attributes from the node.

        (Wrapper for etree.strip_attributes())
        """
        etree.strip_attributes(self.node, attributes)

    def attribute(self, name):
        """
        Return value of the attribute specified, if any;
        otherwise return none.

        Note that this queries the node's *original* set of attributes;
        even if they've subsequently been stripped, changed, etc.,
        on the node.
        """
        try:
            return self.attributes[name]
        except KeyError:
            return None

    def node_id(self):
        """
        Return the ID of the node
        """
        try:
            return self._node_id
        except AttributeError:
            for attribute in ('eid', 'e:id', 'lexid'):
                if self.attribute(attribute) is not None:
                    self._node_id = self.attribute(attribute)
                    break
            else:
                self._node_id = None
            return self._node_id

    lexid = node_id
    eid = node_id
    refid = node_id

    def ancestors(self):
        """
        Return a list of the names/IDs of ancestor nodes, in ascending order.

        Each element in the list is a namedtuple with two attributes:
         -- a.tag (the ancestor node's tag name);
         -- a.lexid (the ancestor node's ID).

        Note that the current node is *not* included as the first element.

        For list of the ancestor nodes themselves, use self.ancestor_nodes()
        """
        try:
            return self._ancestors
        except AttributeError:
            self._ancestors = []
            for node in self.ancestor_nodes():
                node_id = (node.get('eid') or node.get('e:id') or
                           node.get('lexid') or None)
                self._ancestors.append(Ancestor(node.tag, node_id))
            return self._ancestors

    def has_ancestor(self, value):
        """
        Returns True if the current node has an ancestor node whose tag name
        or ID matches the argument. Returns False otherwise.
        """
        value = str(value)
        if any([ancestor.tag == value or ancestor.lexid == value
                for ancestor in self.ancestors()]):
            return True
        else:
            return False

    def ancestor_nodes(self):
        """
        Return a list of ancestor nodes, in ascending order.

        Note that the current node is *not* included as the first element.
        """
        return list(self.node.iterancestors())
