"""
FormsList -- OED forms list (<vfSect>)

@author: James McCracken
"""

import re

from lxml import etree  # @UnresolvedImport

from lex.oed.oedcomponent import OedComponent
from lex.oed.variants.parsers.parserrevised import ParserRevised
from lex.oed.variants.parsers.parserunrevised import ParserUnrevised
from lex.oed.variants.detruncator import Detruncator, TruncationChecker
from lex.oed.variants.variantform import VariantFormFromParser

VFSECT_SECTIONS = ('v1', 'v1sub', 'v2', 'v3')
SKIP_LABELS_PATTERN = re.compile(r'in early use', re.I)


class FormsList(OedComponent):

    """
    OED forms list (<vfSect>).

    Allows for loose and revised types.
    """

    def __init__(self, node, hw_manager):
        OedComponent.__init__(self, node)
        self.strip_elements('qp')
        self.headword_manager = hw_manager
        self._vf_list = {}
        self._revised_status = None
        self.__structural_nodes = None
        self.__section_headers = None
        self.__section_labels = None

    def __bool__(self):
        if self.num_forms('base') > 0:
            return True
        else:
            return False

    def __len__(self):
        return self.num_forms('base')

    def __getitem__(self, i):
        return self.formslist('base')[i]

    def revised_status(self):
        """
        Return 'revised' if this is a revised forms list (<vfSect>),
        or 'unrevised' if this is an unrevised forms list (<vfSectLoose),
        or 'omitted' if there's no forms list at all.

        This is used mainly to decide which parser to use when parsing
        the forms list.
        """
        if self._revised_status is None:
            if self.node.find('.//vfUnit') is not None:
                self._revised_status = 'revised'
            elif self.node.find('.//vf') is not None:
                self._revised_status = 'unrevised'
            else:
                self._revised_status = 'omitted'
        return self._revised_status

    def formslist(self, mode):
        """
        Return the parsed forms list in a given mode. Mode can be:
         -- 'base': basic list representing the source variant forms section.
           There should be one item for each <vf> in the source.
         -- 'detruncated': like 'base', but truncated variant are expanded to
           to the full form (wherever possible).
         -- 'uniqued': like 'detruncated', but filtered to deduplicate identical
           forms which have the same grammatical attributes.
         -- 'unmarked': like 'uniqued', but filtered to include only those
           variants which are grammatically neutral (not plurals, past
           tenses, etc.) - everything in 'unmarked' should be a variant
           of the base form.
         -- 'marked': the complement of 'unmarked'.
        """
        if not mode in self._vf_list:
            self._vf_list[mode] = _version_forms_list(self, mode)
        try:
            return self._vf_list[mode]
        except KeyError:
            return []

    def sortlist(self, mode):
        """
        Sort a given version of the forms list so that the most
        salient are first (based on VariantForm.sort_score()).
        """
        comparator = self.headword_manager.lemma
        self._vf_list[mode].sort(key=lambda vf: vf.sort_score(comparator))

    def num_forms(self, mode):
        """
        Return a count of the number of forms in a forms list.
        """
        return len(self.formslist(mode))

    def num_truncated_forms(self, mode):
        """
        Return a count of the number of truncated forms in a forms list.
        """
        return len([vf for vf in self.formslist(mode) if vf.is_truncated()])

    def append(self, mode, lemma_manager, start_date, end_date):
        """
        Create a new VariantForm object, add it to the end of a forms list.

        Note that the form will not be appended if it's already in the list.

        Arguments:
         --mode: specify which forms list to add it to. (See list of valid
                modes in the formslist method.)
         -- lemma_manager: a lemma object for the new form.
         -- start_date (int): start date for the form.
         -- end_date (int): end date for the form (2050 if not obs.).

        Returns True if the form was appended to the list, False if it was
            already found in the list.
        """
        # Check if the lemma is already covered in the forms list
        for variant_form in self.formslist(mode):
            if variant_form.form == lemma_manager.lemma:
                return False
        new_variant_form = VariantFormFromParser(lemma_manager.node,
                                                 start_date,
                                                 end_date)
        self.formslist(mode).append(new_variant_form)
        return True

    def _structural_nodes(self):
        """
        Return a dictionary of all the structural elements in the
        forms list (indexed by the element's ID).
        """
        if self.__structural_nodes is None:
            self.__structural_nodes = {}
            for tag in VFSECT_SECTIONS:
                for node in self.node.xpath('.//%s' % tag):
                    strnode = OedComponent(node)
                    self.__structural_nodes[strnode.node_id()] = strnode
        return self.__structural_nodes

    def _compile_headers(self):
        """
        Create dictionaries of any header text and labels found at
        the start of structural elements (indexed by the
        structural element's ID).
        """
        self.__section_headers = {}
        self.__section_labels = {}
        for lexid, strnode in self._structural_nodes().items():
            if len(strnode.node) > 0 and strnode.node[0].tag == 'header':
                header_node = strnode.node[0]
                header_txt = etree.tostring(header_node,
                                            encoding='unicode',
                                            method='text')
                header_txt = _massage_header(header_txt)
                labels = header_node.findall('./la')
                label_txt = ' '.join([l.text for l in labels])
                self.__section_headers[lexid] = header_txt
                if not SKIP_LABELS_PATTERN.search(header_txt):
                    self.__section_labels[lexid] = label_txt

    def _section_headers(self):
        """
        Dictionary of section headers, with the section's eid as key.

        This is used to associate headers with individual VariantForm objects.
        """
        if self.__section_headers is None:
            self._compile_headers()
        return self.__section_headers

    def _section_labels(self):
        """
        Dictionary of labels in section headers, with the section's
        eid as key.

        This is used to associate labels with individual VariantForm objects.
        """
        if self.__section_labels is None:
            self._compile_headers()
        return self.__section_labels

    def list_headers(self, variant_form):
        """
        Return a list of any header text applying to a given variant form.
        """
        headers = []
        for ancestor in variant_form.node.ancestors():
            try:
                text = self._section_headers()[ancestor.lexid]
                headers.append(text)
            except KeyError:
                pass
        return headers

    def list_labels(self, variant_form):
        """
        Return a list of any labels applying to a given variant form.
        """
        labels = []
        for ancestor in variant_form.node.ancestors():
            try:
                text = self._section_labels()[ancestor.lexid]
                labels.append(text)
            except KeyError:
                pass
        return labels

    def find_structural_id(self, variant_form):
        """
        Return the lexid of any parent structural node above a
        given variant form.
        """
        for ancestor in variant_form.node.ancestors():
            if ancestor.lexid in self._structural_nodes():
                return ancestor.lexid
        return 0


def _massage_header(header_text):
    """
    Clean up header text from the start of a section.
    """
    header_text = re.sub(r'Eng\. Dial\. Dict\.', '', header_text)
    if len(header_text) > 80:
        header_text = ''
    return header_text


def _check_dating(vf_list, headword_manager):
    """
    Check whether the majority of variant forms appear to have associates
    dates. If not we assumed that it's an undated forms list, and set all
    of its VariantForm objects to
    """
    undated, dated = (0, 0)
    for variant_form in vf_list:
        if variant_form.date.start == 0:
            undated += 1
        else:
            dated += 1
    if dated > undated and dated >= 4:
        for variant_form in vf_list:
            if (variant_form.date.start == 0 and
                variant_form.lemma_manager().lexical_sort() !=
                headword_manager.lexical_sort()):
                variant_form.undated = True


def _version_forms_list(formslist_object, mode):
    """
    Return a list of VariantForm instances representing a
    variant forms section.

    mode must be one of the following:
     -- 'base': basic list representing the source variant forms section.
           There should be one item for each <vf> in the source.
     -- 'detruncated': like 'base', but truncated variant are expanded to
           to the full form (wherever possible).
     -- 'uniqued': like 'detruncated', but filtered to deduplicate identical
           forms which have the same grammatical attributes.
     -- 'unmarked': like 'uniqued', but filtered to include only those variants
           which are grammatically neutral, i.e. not plurals, past tenses,
           participles, etc. - everything in 'unmarked' should be a variant
           of the base form.
     -- 'marked': the complement of 'unmarked'.

    Returns a list of VariantForm objects.
    """
    if mode == 'base':
        vf_list = _parse_forms_list(formslist_object)

    elif mode == 'detruncated':
        tcheck = TruncationChecker(formslist_object.headword_manager,
                                   formslist_object.formslist('base'))
        vf_list = tcheck.check_truncation()
        if formslist_object.num_truncated_forms('base') > 0:
            vf_list = _detruncate(vf_list, formslist_object.headword_manager)

    elif mode == 'uniqued':
        vf_list = []
        idx = dict()
        for variant_form in formslist_object.formslist('detruncated'):
            signature = '%s#%s' % (variant_form.form,
                                   variant_form.grammar_signature())
            if not signature in idx:
                vf_list.append(variant_form)
                idx[signature] = len(vf_list) - 1
            else:
                i = idx[signature]
                vf_list[i].merge(variant_form)

    elif mode == 'unmarked':
        vf_list = [x for x in formslist_object.formslist('uniqued') if
                   x.is_unmarked()]
        _check_dating(vf_list, formslist_object.headword_manager)

    elif mode == 'marked':
        vf_list = [x for x in formslist_object.formslist('uniqued') if
                   not x.is_unmarked()]

    else:
        vf_list = [x for x in formslist_object.formslist('marked') if
                   x.is_grammar_type(mode) and
                   not x.is_grammar_type('compound') and
                   not x.is_grammar_type('negative')]

    return vf_list


def _parse_forms_list(formslist_object):
    """
    Return a list of VariantForm instances representing a
    variant forms section.
    """
    vf_list = []
    if formslist_object.revised_status() == 'revised':
        vf_list = ParserRevised(formslist_object.node).parse()
    elif formslist_object.revised_status() == 'unrevised':
        vf_list = ParserUnrevised(formslist_object.node).parse()

    for variant_form in vf_list:
        variant_form.set_headers(formslist_object.list_headers(variant_form))
        variant_form.header_labels = formslist_object.list_labels(variant_form)
        variant_form.structural_id = formslist_object.find_structural_id(variant_form)
        variant_form.determine_regionality()
        variant_form.determine_irregularity()
    return vf_list


def _detruncate(vf_list, headword_manager):
    """
    Remove truncation from the forms list; return the detruncated version.
    """
    if not headword_manager.is_affix() and len(vf_list) > 0:
        detrunk = Detruncator()
        detrunk.set_comparator(headword_manager)
        previous_structural_id = 0
        for variant_form in vf_list:
            if variant_form.structural_id != previous_structural_id:
                detrunk.set_comparator(headword_manager)

            if variant_form.is_truncated():
                detrunk.set_truncation(variant_form.lemma_manager())
                detrunk.set_feature('plural',
                                    variant_form.is_grammar_type('plural'))
                detrunk.set_feature('compound',
                                    variant_form.is_grammar_type('compound'))
                full_form = detrunk.detruncate()
                if full_form is not None:
                    variant_form.reset_form(full_form)
            else:
                detrunk.set_comparator(variant_form.lemma_manager())

            previous_structural_id = variant_form.structural_id

    return vf_list
