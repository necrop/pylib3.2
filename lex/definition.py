"""
OED/ODE/NOAD Definition

@author: James McCracken
"""

import re
import copy

from lxml import etree  # @UnresolvedImport

import stringtools
from regexcompiler import ReplacementListCompiler
from lex.oed.crossreference import CrossReference


ELEMENT_REMOVER = re.compile(
    r'<(lm|xr|la|gg|sy|cf|w|dat|datEnd|gr|vf|lemUnit|labels|xrg)[ >].*?</\1>'
)

EQUALS_XREF = re.compile(
    r'(=|error|short|shortenings?|form|abbrev\.|abbreviations?|variants?|'
    r'misreadings?|synonyms?) <xr'
)

XREF_STRIPPER = ReplacementListCompiler((
    (r'<xrg [^<>]*>', ''),
    (r'senses? <xr', '<xr'),
    (r'(of|for|to) ', ''),
    (r'(opposite|opposed)', 'opp.'),
))
DATE_STRIPPER = ReplacementListCompiler((
    (r'[()]', ''),
    (r'^(circa|ante|b\.|d\.|fl\. circa) ?', ''),
    ('(\u2013|-).*$', ''),
))
SUBDEF_SPLIT = re.compile(
    r'^(.*)( Also:| Hence:| Hence also:|; \((also|hence|hence also)\)) (.*)$')
ANAPHORA_MARKERS = re.compile(r'(^|[ (])(this|these|such)([,);: ]|$)')
STOPWORDS = {'a', 'an', 'the', 'and', 'to', 'of'}


class Definition(object):

    """
    OED/ODE/NOAD Definition

    Initialized with the definition node.

    If initialized with the keyword argument 'omitList', most functions
    use a version of the definition node from which various elements have
    been removed. The value of omitList should be a list of tag names;
    these elements will all be removed.
    """

    def __init__(self, node, **kwargs):
        self.node = node
        self.header = kwargs.get('headerNode')
        self.omit_list = kwargs.get('omitList')
        self._text_versions = {}

    def serialized(self, stripped=True):
        """
        Serialized version of the definition node.
        """
        if stripped:
            return etree.tounicode(self.node_stripped())
        else:
            return etree.tounicode(self.node)

    def node_stripped(self):
        """
        Return a copy of the definition node from which various
        unwanted elements (mostly non-displaying) have been
        stripped out.
        """
        try:
            return self._node_stripped
        except AttributeError:
            if self.omit_list is None:
                self._node_stripped = self.node
            else:
                self._node_stripped = _strip_elements_from_node(
                    self.node,
                    self.omit_list,)
            return self._node_stripped

    def subdefinition_nodes(self, **kwargs):
        """
        Where applicable, return multiple subdefinition nodes from the
        original definition.

        These may be explicit <subDef>s, or may be
        subdefinitions created by splitting the definition text at
        a suitable place.

        Keyword arguments are:
         -- split_text (True/False - defaults to False). If False, only
            explicit <subDef> subdefinitions will be returned.
         -- allow_anaphora (True/False - defaults to True). If False,
            subdefinitions won't be returned if they depend on
            anaphora ('this', 'such').

        Returns a list of two (occasionally three) etree.Element nodes,
        each constituting a subdefinition.

        Returns an empty list if the definition does not divide
        into subdefinitions.
        """
        split_text = kwargs.get('split_text', False)
        allow_anaphora = kwargs.get('allow_anaphora', True)
        # First try splitting on explicit <subDef> elements...
        subdefs = self.node_stripped().findall('.//subDef')
        # ... then try splitting at breaks indicated in the text
        # (This requires serializing then deserializing the XML, to make
        #  sure we've not been left with mismatched tags.)
        if not subdefs and split_text:
            match = SUBDEF_SPLIT.search(self.serialized(stripped=True))
            if match is not None:
                subdefs = [re.sub(r'^<def[^<>]*>|</def>$', '', subdef)
                           for subdef in (match.group(1), match.group(4),)]
                try:
                    subdefs = [etree.XML('<def>%s</def>' % subdef)
                               for subdef in subdefs]
                except etree.XMLSyntaxError:
                    # Bail out if the two new subdefinitions have failed
                    #  to deserialize cleanly - which probably means that
                    #  we've split the definition somewhere stupid.
                    subdefs = []

        # Watch out for anaphora in the second subdefinition -
        #  we nix the split if there's any anaphora going on, since
        #  the second definition won't be meaningful in isolation.
        if (subdefs and not allow_anaphora and len(subdefs) > 1 and
                ANAPHORA_MARKERS.search(etree.tounicode(subdefs[1]))):
            subdefs = []
        return subdefs

    def text(self, **kwargs):
        """
        Return the text of the definition, truncated to a given length.

        If no length is passed, or length='complete', or length is higher
        than the actual length of the definition string, then the full
        definition is returned.

        If kwarg 'with_header' is True (default), any header node passed
        to __init__ will be prepended to the main definition.
        (E.g. in OED, this is used to prepend a <s4> definition stub
        to the main <s6> definition for a given sense).
        """
        length = kwargs.get('length', 'complete')
        with_header = kwargs.get('with_header', True)
        if self.header is None:
            with_header = False

        # Compute the complete version of the definition text
        if not with_header in self._text_versions:
            # Prepare the header definition (which will be prepended)
            if with_header and self.header is not None:
                header_stripped = _strip_elements_from_node(
                    self.header,
                    self.omit_list,)
                header_text = etree.tounicode(header_stripped,
                                              method='text')
            else:
                header_text = None

            # Prepare the main definition
            full_def = etree.tounicode(self.node_stripped(),
                                       method='text')
            full_def = re.sub(r'^[, .:;]+', '', full_def)

            # Prepend the header definition
            if header_text:
                full_def = header_text + ' ' + full_def
            # Store this in self._text_versions
            self._text_versions[with_header] = full_def.strip()

        # Substring from the complete version to get the length we want
        if not length or length == 'complete':
            return self._text_versions[with_header]
        else:
            return _truncate(self._text_versions[with_header], length)

    def text_start(self, with_header=False):
        """
        Just the first 30 characters of the definition
        """
        return self.text(length=30, with_header=with_header)

    def is_truncated(self, length=None, with_header=True):
        """
        Return True if the given length means that the definition will
        be truncated; False otherwise.
        """
        if length is None or length == 'complete':
            return False
        elif len(self.text(with_header=with_header)) > length:
            return True
        else:
            return False

    def is_cross_reference(self):
        """
        Return True if the definition consists solely or mainly
        of a cross-reference.
        """
        if re.search(r'^=', self.text()):
            return True
        if (re.search('^[Ss]ee ', self.text()) and
            self.node.find('xr') is not None):
            return True
        return False

    def biodate(self):
        """
        For encyclopedic entries in ODE/NOAD - finds the date of birth,
        inside <dg>, which should be the first node in the definition.
        """
        try:
            return self._biodate
        except AttributeError:
            self._biodate = None
            if (self.node is not None and
                len(self.node) > 0 and
                self.node[0].tag == 'dg'):
                date_nodes = self.node[0].findall('date')
                if date_nodes:
                    date_string = etree.tounicode(date_nodes[0],
                                                  method='text',
                                                  with_tail=False)
                    date_string = DATE_STRIPPER.edit(date_string)
                    if re.search(r'^\d{4}$', date_string):
                        self._biodate = int(date_string)
            return self._biodate

    def tokens(self):
        """
        Return a list of tokens from the definition (words only,
        no punctuation, numbers, etc.

        The list is lower-cased, Porter-stemmed, and alpha-sorted.
        """
        try:
            return self._tokens
        except AttributeError:
            self._tokens = set()
            serialized = etree.tounicode(self.node_stripped())
            serialized = ELEMENT_REMOVER.sub('', serialized)
            serialized = re.sub(r'<[^<>]*>', ' ', serialized)
            tokens = stringtools.word_tokens(serialized)
            for text in [t for t in tokens if re.search(r'[a-zA-Z]{3}', t)
                         and t.lower() not in STOPWORDS]:
                text = text.lower().strip('.,;: -()')
                self._tokens.add(stringtools.porter_stem(text))
            self._tokens = sorted(list(self._tokens))
            return self._tokens

    def cross_references(self):
        """
        Return a list of CrossReference objects representing any
        cross-references found in the definition.
        """
        try:
            return self._xrefs
        except AttributeError:
            self._xrefs = [CrossReference(xref_node) for xref_node in
                           self.node_stripped().findall('.//xr')]
            if self._xrefs:
                # Add a 'type' attribute to each cross-reference,
                # determined by the preceding text
                for xref in self._xrefs:
                    xref.type = None  # default value
                # Split definitions into sections, one section per xref,
                #  with the xref at the end of the section. The 'sections'
                #  list should then be aligned with the self._xrefs list.
                serialized = etree.tounicode(self.node_stripped())
                sections = []
                for section in serialized.split('</xr>'):
                    section = XREF_STRIPPER.edit(section.lower())
                    sections.append(section)
                for section, xref in zip(sections, self._xrefs):
                    if EQUALS_XREF.search(section):
                        xref.type = 'equals'
                    elif 'see <xr' in section:
                        xref.type = 'see'
                    elif 'also <xr' in section or 'cf. <xr' in section:
                        xref.type = 'cf'
                    elif 'opp. <xr' in section:
                        xref.type = 'opposite'
            return self._xrefs

    def lemmas(self):
        """
        Return a list of all lemmas (contents of <lm> elements) found
        in the definition (as text strings).
        """
        try:
            return self._lemmas
        except AttributeError:
            self._lemmas = [l.text for l in
                            self.node_stripped().findall('.//lm')]
            return self._lemmas


    #=======================================================
    # Taxonomic stuff
    #=======================================================

    def genera(self):
        """
        Return a set of genus terms found in the definition.

        These are taken either from <txg> elements, or from the
        first part of <txb> elements (where the first part is not
        abbreviated or has been expanded - see self.binomials()).
        """
        try:
            return self._genera
        except AttributeError:
            self._parse_binomials()
            return self._genera

    def binomials(self):
        """
        Return a set of binomial terms found in the definition.

        These are taken from <txb> elements. Where possible, abbreviated
        genus terms are expanded by checking for the full version in
        neighbouring <txg> and <txb> elements.
        """
        try:
            return self._binomials
        except AttributeError:
            self._parse_binomials()
            return self._binomials

    def _parse_binomials(self):
        """
        Find and expand any binomial and genus terms.
        """
        raw_binomials = set([tx.text for tx in
                             self.node_stripped().findall('.//txb')
                             if tx.text is not None])
        raw_genera = set([tx.text for tx in
                          self.node_stripped().findall('.//txg')
                          if tx.text is not None])
        # also include the first word of any binomials
        for binomial in raw_binomials:
            if len(binomial.split()) == 2:
                genus = binomial.split()[0]
                if re.search(r'^[A-Z][a-z]+$', genus):
                    raw_genera.add(genus)

        # Try to expand any abbreviated binomials using the full forms
        #  in raw_genera (which should now include any full forms
        #  found elsewhere in raw_binomials).
        additions = set()
        for binomial in raw_binomials:
            match = re.search(r'^([A-Z])\. ', binomial)
            if match is not None:
                for genus in raw_genera:
                    if genus.startswith(match.group(1)):
                        binomial = re.sub(r'^[A-Z]\.', genus, binomial)
                        additions.add(binomial)
        for addition in additions:
            raw_binomials.add(addition)

        self._binomials = raw_binomials
        self._genera = raw_genera
        return

    def families(self):
        """
        Return a set of family terms found in the definition.

        These are taken from <txf> elements.
        """
        return set([tx.text for tx in self.node_stripped().findall('.//txf')
                    if tx.text is not None])


def _strip_elements_from_node(node, omit_list):
    node_stripped = copy.deepcopy(node)
    for tag in omit_list:
        etree.strip_elements(node_stripped,
                             tag,
                             with_tail=False)
    return node_stripped


def _truncate(full_definition, length):
    """
    Truncate a complete definition down to a given length (number of
    characters) - neatening the end to avoid broken words.
    """
    if len(full_definition) <= length:
        return full_definition
    else:
        full_definition += '     '
        for i in range(5):
            if full_definition[length-i] == ' ':
                index = length - i
                break
        else:
            for i in range(5):
                if full_definition[length+i] == ' ':
                    index = length + i
                    break
            else:
                index = length
        truncated = full_definition[0:index]
        truncated = truncated.rstrip('(,;:. ') + '...'
        return truncated
