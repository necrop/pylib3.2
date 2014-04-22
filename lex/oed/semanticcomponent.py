"""
SemanticComponent -- OED semantic component base class

@author: James McCracken
"""

import string
import copy

from lxml import etree

from lex.oed.oedcomponent import OedComponent
from lex.oed.quotationparagraph import QuotationParagraph
from lex.oed.daterange import DateRange
from lex.oed.resources.mainsenses import MainSensesCache
from lex.wordclass.wordclass import Wordclass
from lex.definition import Definition

DEFINITION_STRIP = ('n', 'etym', 'qp', 'q', 'lemVersions')
THIN_DISTANCE = 15  # Used to thin out quotations for weighted size

MAIN_SENSE_FINDER = MainSensesCache(max_senses=1, with_definitions=False)


class SemanticComponent(OedComponent):

    """
    OED semantic component base class

    This is intended as a base class primarily for entries and senses,
    i.e. XML nodes that have characteristics embedded as attributes on
    the root element.
    """

    def __init__(self, node, **kwargs):
        OedComponent.__init__(self, node, **kwargs)
        self._shared_quotations = False

    def main_current_sense(self):
        """
        Return a sense within the current block that looks like a
        good candidate for the (or a) main current sense.
        """
        if self.tag == 'Entry':
            # If this is an entry, we return the current sense for the
            #  first non-obs <s1> block (or just the first block, if all
            #  are obs).
            if not self.s1blocks():
                return None
            else:
                if (len(self.s1blocks()) == 1 or
                        not self.s1blocks()[0].is_marked_obsolete()):
                    block = self.s1blocks()[0]
                elif not self.s1blocks()[1].is_marked_obsolete():
                    block = self.s1blocks()[1]
                else:
                    block = self.s1blocks()[0]
                return block.main_current_sense()

        elif self.tag == 's1':
            try:
                return self._main_current_sense
            except AttributeError:
                main_sense = MAIN_SENSE_FINDER.main_sense_from_block(self)
                if not main_sense:
                    try:
                        # Default to the first sense
                        main_sense = self.senses()[0]
                    except IndexError:
                        main_sense = None
                self._main_current_sense = main_sense
                return self._main_current_sense
        else:
            # No other kind of block is viable
            return None

    def definition_manager(self, **kwargs):
        try:
            return self._definition_object
        except AttributeError:
            current = kwargs.get('current', False)
            dnode = None
            if current:
                current_sense = self.main_current_sense()
                if current_sense:
                    dnode = current_sense.node.find('.//def')
            if dnode is None:
                dnode = self.node.find('.//def')
            if dnode is None:
                dnode = etree.Element('def')  # Make a dummy element

            # If this is a definition from a <s6> or <s7> sense, we also
            #  grab any definition from its parent <s4> (so that this can
            #  be tacked on the front)
            s4_dnode = None
            if dnode is not None:
                try:
                    parent_tag = dnode.getparent().tag
                except AttributeError:
                    pass
                else:
                    if parent_tag in ('s6', 's7'):
                        for ancestor in dnode.iterancestors():
                            if ancestor.tag == 's4':
                                s4_dnode = ancestor.find('./def')
                                break

            self._definition_object = Definition(dnode,
                                                 omitList=DEFINITION_STRIP,
                                                 headerNode=s4_dnode)
            return self._definition_object

    def reset_definition(self, new_node):
        if isinstance(new_node, Definition):
            self._definition_object = new_node
        else:
            self._definition_object = Definition(new_node,
                                                 omitList=DEFINITION_STRIP,)

    def definition(self, **kwargs):
        """
        Return the first definition (as a string, without tagging).

        Truncates to the number of characters specified by optional
        'length' length.
        """
        return self.definition_manager(**kwargs).text(**kwargs)

    def subdefinitions(self, **kwargs):
        try:
            return self._subdefinitions
        except AttributeError:
            subdefs = self.definition_manager().subdefinition_nodes(**kwargs)
            self._subdefinitions = [Definition(s) for s in subdefs]
            return self._subdefinitions

    def internal_lemmas(self):
        """
        Return a list of nodes for lemmas (<lm>) within the block
        (excluding lemVersions)
        """
        node_stripped = copy.deepcopy(self.node)
        etree.strip_elements(node_stripped, 'lemVersions')
        return node_stripped.findall('.//lm')

    def lemma_id(self):
        """
        Return the e:id of the first lemma in the block (if any).

        Useful for resolving cross-references, since cross-references
        often point to the <lm> element, not to the parent sense
        or subentry.
        """
        try:
            first_lemma = self.internal_lemmas()[0]
        except IndexError:
            return None
        else:
            if first_lemma.get('eid'):
                return int(first_lemma.get('eid'))
            elif first_lemma.get('e:id'):
                return int(first_lemma.get('e:id'))
            else:
                return None

    #==============================================
    # Functions relating to quotations and quotation paragraphs
    #==============================================

    def quotation_paragraphs(self):
        try:
            return self._quotation_paragraphs
        except AttributeError:
            self._quotation_paragraphs = [QuotationParagraph(node)
                                          for node in
                                          self.node.findall('.//qp')]
            return self._quotation_paragraphs

    def quotations(self):
        """
        Return a list of quotation objects.

        Every quotation in the component, in document order.
        """
        try:
            return self._quotations
        except AttributeError:
            self._quotations = []
            for qpara in self.quotation_paragraphs():
                self._quotations.extend(qpara.quotations())
            if self.tag == 'e':
                self._quotations = [q for q in self._quotations
                                    if not q.is_in_vfsect()]
            return self._quotations

    def quotations_sorted(self):
        """
        Return a list of quotation objects, sorted by year.
        """
        try:
            return self._quotations_sorted
        except AttributeError:
            self._quotations_sorted = sorted(self.quotations(),
                                             key=lambda q: q.year())
            return self._quotations_sorted

    def first_quotation(self):
        """
        Return the (chronologically) first quotation, if any;
        return None if not quotations.
        """
        try:
            return self.quotations_sorted()[0]
        except IndexError:
            return None

    def last_quotation(self):
        """
        Return the (chronologically) last quotation, if any;
        return None if not quotations.
        """
        try:
            return self.quotations_sorted()[-1]
        except IndexError:
            return None

    def num_quotations(self, force_recount=False, include_derivatives=True):
        """
        Return a count of all the quotations in the component.
        """
        if not force_recount:
            try:
                return self._num_quotations
            except AttributeError:
                pass

        num = 0
        # To save time, we first try taking the value
        #  from the ch_numQuotations characteristic
        if self.characteristic_first('numQuotations') and not force_recount:
            num = int(self.characteristic_first('numQuotations'))
        # If we've got a zero value so far, re-check by actually
        #  counting the quotations
        if not num and include_derivatives:
            num = len([q for q in self.quotations()
                       if not q.is_bracketed()])
        elif not num:
            num = len([q for q in self.quotations()
                       if not q.is_bracketed() and
                       not q.is_in_derivatives_section()])
        self._num_quotations = num
        return self._num_quotations

    def insert_quotations(self, new_qparas):
        self._quotation_paragraphs = new_qparas
        self._shared_quotations = True
        # Unset any attributes that will now be stale
        for has_feature in ('_quotations', '_quotations_sorted',
                            '_num_quotations'):
            try:
                del self.__dict__[has_feature]
            except KeyError:
                pass

    def has_shared_quotations(self):
        return bool(self._shared_quotations)

    # def quotation_collocates(self, **kwargs):
    #    min_date = kwargs.get('minimum_date', 1600)

        # Collect collocates from each quotation
        # collocates = []
        # for q in [q for q in self.quotations() if q.year >= min_date]:
        #    collocates.extend(q.ranked_collocates(self.lemma))

        # Uniq any duplicates
        # coll_uniq = defaultdict(list)
        # for token, distance in collocates:
        #    coll_uniq[token].append(distance)
        # collrank = [(t, min(distances), len(distances)) for t, distances in
        #    collocates.items()]

        # collrank.sort(key=lambda c: c[1], reverse=True)
        # return collrank

    def quotations_binomials(self):
        """
        Return a set of any binomials/genus terms found in quotations
        """
        binomials = set()
        for quotation in [quotation for quotation in self.quotations()
                          if quotation.year() > 1800]:
            for binomial in quotation.binomials():
                binomials.add(binomial)
        try:
            self.lemma
        except AttributeError:
            pass
        else:
            binomials = set([binomial for binomial in binomials if
                binomial.lower() != self.lemma.lower()])
        return binomials

    #==============================================
    # Functions relating to characteristics
    #==============================================

    def characteristics(self):
        """
        Return a dictionary of characteristics ('ch_' attributes)
        """
        try:
            return self._characteristics
        except AttributeError:
            self._characteristics = {}
            for att in [a for a in self.attributes if a.startswith('ch_')]:
                self._characteristics[att.lower()] = \
                    self.attributes[att].split('|')
            return self._characteristics

    def characteristic_list(self, att):
        """
        Return the list of pipe-separated values for a characteristic.

        Arguments:
         - Name of the has_feature (with or without the 'ch_' prefix)

        Returns a list (empty if the characteristic does not exist)
        """
        att = att.lower()
        try:
            return self.characteristics()[att]
        except KeyError:
            try:
                return self.characteristics()['ch_' + att]
            except KeyError:
                return []

    def characteristic_first(self, att):
        """
        Return the *first* set of pipe-separated values for a characteristic.

        Arguments:
         - Name of the has_feature (with or without the 'ch_' prefix)

        Returns a string (null if the characteristic does not exist)
        """
        try:
            return self.characteristic_list(att)[0]
        except IndexError:
            return ''

    def characteristic_leaves(self, att):
        """
        Return the end-/leaf-nodes from a set of characteristic.

        Arguments:
         - Name of the has_feature (with or without the 'ch_' prefix)

        Returns a list (empty if the characteristic does not exist)
        """
        return [c.split('/')[-1] for c in self.characteristic_list(att)]

    def characteristic_nodes(self, att):
        """
        Return all the nodes from a set of characteristics.

        Arguments:
         - Name of the has_feature (with or without the 'ch_' prefix)

        Returns a set (empty if the characteristic does not exist)
        """
        nodes = set()
        for c in self.characteristic_list(att):
            for node in c.split('/'):
                nodes.add(node)
        return nodes

    def characteristic_heads(self, att):
        """
        Return the head nodes from a set of characteristic.

        Arguments:
         - Name of the has_feature (with or without the 'ch_' prefix)

        Returns a list (empty if the characteristic does not exist)
        """
        return [c.split('/')[0] for c in self.characteristic_list(att)]

    #==============================================
    # Functions relating to wordclass
    #==============================================

    def wordclasses(self):
        try:
            return self._wordclasses
        except AttributeError:
            self._wordclasses = [Wordclass(w) for w in
                                 self.characteristic_list('wordclass')]
            if not self._wordclasses and self.tag == 's1':
                self._wordclasses = [Wordclass(n.get('type')) for n in
                                     self.node.findall('./ps')
                                     if n.get('type') and
                                     not n.get('occasional')]
            if not self._wordclasses:
                self._wordclasses = [Wordclass('null')]
            return self._wordclasses

    def primary_wordclass(self):
        try:
            return self.wordclasses()[0]
        except IndexError:
            return None

    #==============================================
    # Functions relating to date-range (first and last date)
    #==============================================

    def date(self):
        """
        Return the start or end date for the entry or sense.
        """
        try:
            return self._date
        except AttributeError:
            date1 = self.characteristic_first('firstdatesort')
            date2 = self.characteristic_first('lastdatesort')
            if not date1 or not date2:
                date1, date2 = self.recompute_dates()
            self._date = DateRange(start=date1,
                                   end=date2,
                                   obs=self.is_marked_obsolete())
            return self._date

    def set_dates(self, new_daterange):
        """
        Replace the existing DateRange object with a new DateRange object.
        """
        self._date = DateRange(start=new_daterange.start,
                               end=new_daterange.end,
                               obs=new_daterange.is_marked_obsolete())

    def recompute_dates(self):
        start = None
        end = None
        for quotation in [q for q in self.quotations_sorted() if
                          not q.is_bracketed() and
                          not q.is_suppressed()]:
            if quotation.year():
                if not start:
                    start = quotation.year()
                end = quotation.year()
        return start, end

    def is_marked_obsolete(self):
        """
        Return True if the sense is marked as obsolete.

        Note that this is based on explicit st=obs marking, not
        on the date of the last quotation.
        """
        try:
            return self._obs_marker
        except AttributeError:
            if (self.characteristic_first('obsolete') == 'true' or
                    self.node.get('st') == 'obs'):
                self._obs_marker = True
            else:
                self._obs_marker = False
            return self._obs_marker

    def set_obsolete_marker(self, value):
        """
        Set an explicit marker to indicate whether this is obsolete
        or not.

        Argument should be boolean True or False.

        This is necessary because obsoleteness is often not indicated
        within the node itself, but in an element higher up the tree.
        So we need to be able to set flag this manually.
        """
        self._obs_marker = value

    def merge(self, other):
        """
        Merge in quotations from another sense or block.
        """
        self.quotations.extend(other.quotations)
        try:
            del self._quotations_sorted
        except AttributeError:
            pass
        date1, date2 = self.recompute_dates()
        self.date.reset('start', date1)
        self.date.reset('end', date2)
        # Recalculate obsoleteness
        if not other.is_marked_obsolete():
            self.set_obsolete_marker(False)
        return

    def is_cross_reference(self):
        if (self.num_quotations() == 0 and
                self.definition_manager().is_cross_reference()):
            return True
        else:
            return False

    def is_initial_letter(self):
        if (self.lemma in string.ascii_uppercase and
                self.primary_wordclass() and
                self.primary_wordclass().penn == 'NN'):
            return True
        else:
            return False

    def thinned_year_list(self, **kwargs):
        """
        List of quotation years, used by self.weighted_size() below.

        Adjusted from actual list of years, (a) to thin out clustering
        and (b) to infer C20 years in the case of unrevised blocks.

        Returns list of ints (each int being a year)
        """
        try:
            return self._year_list
        except AttributeError:
            revised = kwargs.get('revised', False)

            senses = []
            for qpara in self.quotation_paragraphs():
                date_list = [q.year() for q in qpara.quotations()
                             if q.year() and q.year() > 0 and
                             not q.is_bracketed()]
                date_list.sort()
                if date_list:
                    senses.append(date_list)

            years = []
            for date_list in senses:
                # Thin out to avoid artificial clustering: if two consecutive
                #  quotations are within x years of each other, skip the second
                date_list_modified = []
                for year in date_list:
                    if not date_list_modified:
                        pass
                    elif year < date_list_modified[-1] + 5:
                        continue
                    elif 1550 < year < date_list_modified[-1] + THIN_DISTANCE:
                        continue
                    date_list_modified.append(year)

                # Add 'fake' C20 years if it's unrevised and has no C20 quotes
                if not revised and 1840 < date_list_modified[-1] < 1915:
                    if len(date_list_modified) <= 2:
                        pass
                    elif len(date_list_modified) <= 4:
                        date_list_modified.extend((1960,))
                    elif len(date_list_modified) <= 7:
                        date_list_modified.extend((1940, 1990))
                    else:
                        date_list_modified.extend((1935, 1965, 1990))

                # Take the midpoint between consecutive dates (to avoid
                # clustering around last dates, e.g. 1890 or 2000)
                if len(senses) == 1 or len(date_list_modified) == 1:
                    date_list_middled = date_list_modified
                else:
                    date_list_middled = []
                    for i, year in enumerate(date_list_modified):
                        if i == 0:
                            continue
                        midpoint = (year + date_list_modified[i-1]) / 2
                        date_list_middled.append(int(midpoint))
                years.extend(date_list_middled)

            # sort into date order
            years.sort()
            self._year_list = years
            return self._year_list

    def weighted_size(self, **kwargs):
        """
        Calculate the weighted size of the block.

        The size metric is based on number of quotations, but weighted
        towards the modern period: more recent quotations count
        for more than older quotations. Hence it's useful for heuristics
        relating to likely frequency.

        Also takes into account whether the block is revised or not;
        since this will affect how many modern quotations (esp. C20) it has.

        Keyword arguments:
        - 'currentYear': int indicating the year for which the measurement
        should be taken (defaults to 2000). E.g. if currentYear=1800, returns
        the weighted size of the block at 1800 (ignoring all post-1800 quotes)

        Returns float.
        """
        current_year = kwargs.get('currentYear', 2000)
        total = float(0)
        if self.is_marked_obsolete() and current_year > self.date().end + 25:
            pass
        elif not self.thinned_year_list(**kwargs):
            pass
        else:
            for year in self.thinned_year_list(**kwargs):
                if year <= current_year:
                    delta = max([current_year - year, 50])
                    delta = min([delta, 400])
                    total += 100 / delta
            # Reduce the score if the word has not been around for long.
            #  'baseline' gives us a sliding scale; longevity matters less the
            #  nearer we are to 2010 (so that e.g. 'blog' is not penalized
            #  too harshly).
            startyear = self.thinned_year_list(**kwargs)[0]
            baseline = min([2010 - startyear, 250])
            lifespan = max([current_year - startyear, (baseline / 5)])
            if lifespan < baseline:
                total *= (lifespan / baseline)
        return total

    def labels(self):
        """
        Return a set of all the label text (text contained in <la>
        elements) in this sense and in any parent headers.
        """
        try:
            return self._labels
        except AttributeError:
            labels = set([la.text for la in self.node.findall('.//la')
                if la.text is not None])
            for header in self.header_nodes():
                for label in [la.text for la in header[0].findall('.//la')
                              if la.text is not None]:
                    labels.add(label)
            if 'esp.' in labels:
                labels.remove('esp.')
            self._labels = labels
            return self._labels

    #===================================================
    # Functions related to parent elements/headers
    #===================================================

    def header_nodes(self):
        """
        Returns a list of any <header> or <def> elements
        attached to parent nodes. The list is in ascending order, i.e.
        going upwards from the current node.

        Each element in the list is a 2-ple consisting of
        (header_node, parent_tag), where 'parent_tag' is the tag name
        of the parent element, e.g. 's4'.
        """
        nodes = []
        is_outside_sensesect = False
        for ancestor in self.ancestor_nodes():
            header = ancestor.find('./header')
            if header is None:
                header = ancestor.find('./def')
            if header is not None:
                nodes.append((header, ancestor.tag))
            if ancestor.tag in ('lemSect', 'revSect'):
                is_outside_sensesect = True

        # If this is a lemSect or a revision section, it won't be
        #   directly under the main senseSect, but should still inherit
        #   the senseSect's header.
        if is_outside_sensesect:
            enode = self.ancestor_nodes()[-1]
            sensesect_header = enode.find('./senseSect/header')
            if sensesect_header is not None:
                nodes.append((sensesect_header, 'senseSect'))

        return nodes

    def header_strings(self):
        """
        Return a list of any strings from <header> or <def> elements
        attached to parent nodes. The list is in ascending order, i.e.
        going upwards from the current node
        """
        headers = [etree.tostring(n[0], method='text', encoding='unicode')
                   for n in self.header_nodes()]
        headers = [h.strip() for h in headers if h.strip()]
        return headers

    def parent_definition_manager(self):
        """
        If this is a <s6> or <s7> sense, return the definition object
        for the parent <s4> or <s6>, if any; otherwise returns None.
        """
        try:
            return self._parent_def
        except AttributeError:
            self._parent_def = None
            if self.tag in ('s6', 's7'):
                headers = [n[0] for n in self.header_nodes()
                    if n[1] in ('s4', 's6')]
                try:
                    self._parent_def = Definition(headers[0],
                        omitList=DEFINITION_STRIP)
                except IndexError:
                    pass
            return self._parent_def
