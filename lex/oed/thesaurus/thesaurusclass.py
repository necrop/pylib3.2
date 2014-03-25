"""
ThesaurusClass -- Historical Thesaurus class (taxonomic node + content)
ThesaurusInstance -- Historical Thesaurus instance

@author: James McCracken
"""

from lxml import etree  # @UnresolvedImport

LIGATURE_FIXES = (
    ('\u00e6', 'ae'),
    ('\u0153', 'oe'),
    ('\u00c6', 'Ae'),
    ('\u0152', 'Oe'),
)
BASE_URL = 'http://www.oed.com'
OPEN_DATE = 2020  # End-date used for non-obsolete instances

WORDCLASS_TRANSLATIONS = {'noun': 'NN', 'adjective': 'JJ', 'adverb': 'RB',
                          'verb': 'VB', 'verb (transitive)': 'VB',
                          'verb (intransitive)': 'VB', 'verb (reflexive)': 'VB',
                          'phrase': 'PHRASE', 'preposition': 'IN',
                          'conjunction': 'CC', 'interjection': 'UH'}


class ThesaurusClass(object):

    """
    Historical Thesaurus class (taxonomic node + content)
    """

    def __init__(self, node):
        # Test if the node is actually a string at this stage; if so,
        # it needs to be turned into a node
        try:
            node.lower()
        except AttributeError:
            pass
        else:
            node = etree.fromstring(node)
        self.node = node

    def id(self):
        """
        Return the ID of the thesaurus class.
        """
        return int(self.node.get('id', 0))

    def sortcode(self):
        """
        Numeric code used to sort thesaurus classes into taxonomic order.
        """
        return int(self.node.get('sortCode', 0))

    def path(self):
        """
        Return a list of IDs indicating the full taxonomic path to this
        class (i.e. the IDs of all direct ancestor classes, in
        descending order).

        This is *inclusive*, i.e. the ID of this class is included
        as the last element in the list.
        """
        return [int(p.get('idref', 0)) for p in
                self.node.findall('./fullpath/node')]

    def label(self):
        """
        Return the text string describing this class (or an empty string
        if it has no label).
        """
        label_nodes = self.node.findall('./fullpath/node')
        if label_nodes:
            return label_nodes[-1].text or ''
        else:
            return ''

    def breadcrumb(self):
        """
        Return a string giving the breadcrumb for this class.

        ('>'-separated concatenation of the labels of all its
        ancestor nodes plus its own label.)
        """
        def nodal_text(node):
            text = node.text or ''
            if node.get('pos'):
                text += ' [%s]' % node.get('pos')
            return text.strip()

        return ' > '.join([nodal_text(p) for p in
                           self.node.findall('./fullpath/node')])

    def parent(self):
        """
        Return the ID of this class's parent node (or None, if it's
        a top-level node).
        """
        try:
            return [id for id in self.path() if id != self.id()][-1]
        except IndexError:
            return None

    def ancestor(self, **kwargs):
        """
        Return the ID of an ancestor at a given level.

        e.g. c.ancestor(level=3) returns the ID of the level-3
        ancestor class.

        Defaults to level=1; so c.ancestor() returns the ID of the
        top-level class (equivalent to c.root()).
        """
        level = kwargs.get('level', 1)
        try:
            return self.path()[level - 1]
        except IndexError:
            return None

    def root(self):
        """
        Return the ID of the top-level ancestor class.
        """
        try:
            return self.path()[0]
        except IndexError:
            return None

    def level(self):
        """
        Return an int indicating the level of this class in the
        Historical Thesaurus taxonomy.
        """
        return len(self.path())

    def is_wordclass_level(self):
        """
        Return True if this class is the level at which a wordclass
        is defined (i.e. it has a wordclass, but its parent class does not).
        """
        if not self.wordclass():
            return False
        breadcrumb_nodes = self.node.findall('./fullpath/node')
        breadcrumb_nodes.pop()
        if breadcrumb_nodes[-1].get('pos'):
            return False
        else:
            return True

    def wordclass(self, penn=False):
        """
        Return the wordclass/part-of-speech for this class (or None
        if it's above wordclass-level).

        Note that by default this returns the native wordclass value
        - e.g. 'adjective' rather than 'JJ'. But you can get the Penn
        equivalent by including the keyword argument penn=True:
        >>> c.wordclass()
        >>> 'noun'
        >>> c.wordclass(penn=True)
        >>> 'NN'
        """
        try:
            self._wordclass
        except AttributeError:
            wordclasses = [c.get('pos') for c in
                           self.node.findall('./fullpath/node')
                           if c.get('pos') is not None]
            try:
                self._wordclass = wordclasses[0]
            except IndexError:
                self._wordclass = None

        if penn:
            try:
                return WORDCLASS_TRANSLATIONS[self._wordclass]
            except KeyError:
                return self._wordclass
        else:
            return self._wordclass

    def size(self, **kwargs):
        """
        Return the size (number of instances) of the node.

        If the keyword argument 'branch=True' is supplied, the size
        of the *branch* is returned, i.e. the total number of instances
        in the node plus all its descendants.

        Usage:
        >>> c.size()             # size of node
        >>> c.size(branch=True)  # size of branch
        """
        if kwargs.get('branch'):
            return int(self.node.get('numInstancesDescendant', 0))
        else:
            return int(self.node.get('numInstancesDirect', 0))

    def reset_size(self, size, **kwargs):
        """
        Reset the size (number of instances) of the node
        ('numInstancesDirect' attribute)

        If the keyword argument 'branch=True' is supplied, the size
        of the *branch* is set ('numInstancesDescendant' attribute)
        """
        if kwargs.get('branch'):
            self.node.set('numInstancesDescendant', str(size))
        else:
            self.node.set('numInstancesDirect', str(size))

    def instances(self):
        """
        Return a list of instances (ThesaurusInstance objects) in
        this class.
        """
        try:
            return self._instances
        except AttributeError:
            self.reload_instances()
            return self._instances

    def reload_instances(self):
        self._instances = [Instance(i) for i in
                           self.node.findall('./instance')]

    def child_nodes(self):
        """
        Return a list of child nodes immediately below this now.

        (Returns a list of the nodes' IDs, not the nodes themselves.)
        """
        return [int(c.get('idref', 0)) for c in
                self.node.findall('./childNodes/node')]

    def remove_child(self, target_id):
        """
        Remove pointer to a child node with a give ID
        """
        children = self.node.findall('./childNodes/node')
        for child in children:
            if child.get('idref') == str(target_id):
                child.getparent().remove(child)
                break

    def is_leaf_node(self):
        """
        Return True if this is a leaf node (i.e. has no child nodes).
        """
        if self.child_nodes():
            return False
        else:
            return True

    def url(self):
        """
        Return a URL to this thesaurus class in OED Online.
        """
        return '%s/view/th/class/%d' % (BASE_URL, self.id(),)

    def selfdestruct(self):
        """
        Remove the XML node for this class from its container
        """
        container = self.node.getparent()
        container.remove(self.node)


class Instance(object):

    """
    Historical Thesaurus instance (~ representing an OED sense).
    """

    def __init__(self, node):
        self.node = node

    def lemma(self):
        """
        Return the instance's lemma.
        """
        lem = self.node.findtext('./lemma')
        for subs in LIGATURE_FIXES:
            lem = lem.replace(subs[0], subs[1])
        return lem

    def definition(self):
        """
        Return the instance's definition, as a string (as given in
        the thesaurus data - this may be truncated compared to the
        full version in the OED itself).
        """
        defnode = self.node.find('./def')
        defn = etree.tostring(defnode, method='text', encoding='unicode')
        for subs in LIGATURE_FIXES:
            defn = defn.replace(subs[0], subs[1])
        return defn

    def display_date(self):
        """
        Return the date in string form, as used for display purposes.
        """
        return self.node.findtext('./date')

    def start_date(self):
        """
        Return the numeric version of the date, as used for datewise
        sorting.
        """
        return int(self.node.get('sortDate', 0))

    def end_date(self):
        """
        Return the numeric version of the end date.

        This defaults to 2020 if the instance is not obsolete.
        """
        if not self.is_obsolete():
            return OPEN_DATE
        else:
            return int(self.node.get('endDate', 0))

    def is_obsolete(self):
        """
        Return True if the instance is marked as obsolete, False if not.
        """
        if self.node.get('obsolete', False):
            return True
        else:
            return False

    obsolete = is_obsolete

    def lifespan(self):
        """
        Return the lifespan of the instance, i.e. difference between
        start date and end date (or 2020, if not obsolete).
        """
        if self.end_date() and self.start_date():
            return max(self.end_date() - self.start_date(), 0)
        else:
            return 0

    def num_quotations(self):
        """
        Return the number of quotations in the instance.
        """
        return int(self.node.get('numQuotations', 0))

    def refentry(self):
        """
        Return the ID of the target entry in OED.
        """
        return int(self.node.get('refentry') or 0)

    def refid(self):
        """
        Return the ID of the target node in OED (usually a sense or subentry).
        """
        return int(self.node.get('refid') or 0)

    lexid = refid

    def url(self):
        """
        Return a URL to this instance's sense in OED Online.
        """
        if not self.refentry():
            return BASE_URL
        elif not self.refid():
            return '%s/view/Entry/%d' % (BASE_URL, self.refentry(),)
        else:
            return '%s/view/Entry/%d#eid%d' % (BASE_URL, self.refentry(),
                                               self.refid(),)

    def estimated_frequency(self):
        """
        Return a (very crude) estimate of the sense's frequency.

        This is calculated as the square of the number of quotations.
        """
        if (self.obsolete() or
                self.num_quotations() == 0 or
                800 < self.end_date() < 1700):
            return 1
        else:
            return self.num_quotations() ** 2

    def selfdestruct(self):
        """
        Remove the XML node for this instance from its container class
        """
        container = self.node.getparent()
        container.remove(self.node)
