"""
LinkManager

@author: James McCracken
"""

import os
import re
from collections import defaultdict, namedtuple

from lxml import etree

from stringtools import lexical_sort
from lex import lexconfig
from lex.odo.distiller import Distiller
from lex.oed.resources.vitalstatistics import VitalStatisticsCache

LINKS_DIR = lexconfig.ODO_LINKS_DIR
CandidateLink = namedtuple('CandidateLink', ['lexid', 'oed_headword', 'odo_headword'])


class LinkManager(object):

    """
    Class to manage links from ODE/NOAD to OED.
    """

    def __init__(self, **kwargs):
        self.dict_name = kwargs.get('dictName', 'ode').lower()
        self.oed_file = os.path.join(LINKS_DIR, 'oed_to_%s.xml' % self.dict_name)
        self.link_files = [os.path.join(LINKS_DIR, '%s_to_oed.xml' % self.dict_name),]

        if self.dict_name == 'ode' and kwargs.get('includeAdditions', True):
            self.link_files.append(os.path.join(LINKS_DIR, 'ode_to_oed_additions.xml'))

        self.links = {}
        self.links_reversed = {}
        self.entry_content = {}
        self.derivatives = {}

    def parse_link_file(self):
        def parse_hw(node):
            text = etree.tostring(node, method='text', encoding='unicode')
            text = text.split('|')[0]
            return text.split(',')[0].strip()

        # Create mappings from OED to ODE
        multilinks = defaultdict(list)
        for filepath in self.link_files:
            tree = etree.parse(filepath)
            for entry in tree.findall('./e'):
                lexid = entry.get('lexid')
                linknode = entry.find('./linkSet/link')
                if linknode is not None:
                    oed_id = linknode.get('refentry')
                    sub_id = linknode.get('refid')
                    if sub_id is not None and sub_id != '0':
                        oed_id = oed_id + '#' + sub_id
                    oed_hw = parse_hw(linknode)
                    ode_hw = parse_hw(entry.find('label'))
                    multilinks[oed_id].append(CandidateLink(lexid, oed_hw, ode_hw))

        for oed_id, linklist in multilinks.items():
            # If there's only one possible ODO link for this OED ID, we accept that.
            #  But if there's more than one competing link, we look for the one where
            #  the headwords match; or failing that, the one where the headwords
            #  fuzzily match.
            if len(linklist) == 1:
                winner = linklist[0]
            else:
                # Exact match
                z = [l for l in linklist if l.oed_headword == l.odo_headword]
                try:
                    winner = z[0]
                except IndexError:
                    # Fuzzy match
                    z = [l for l in linklist if
                         lexical_sort(l.oed_headword) == lexical_sort(l.odo_headword)]
                    try:
                        winner = z[0]
                    except IndexError:
                        # Give up
                        winner = linklist[0]
            self.links[oed_id] = winner.lexid

        # Create the inverse mapping (from ODE to OED)
        for oed_id, lexid in self.links.items():
            self.links_reversed[lexid] = oed_id

        self.parse_oed_file()

    def parse_distilled_file(self):
        distilled = Distiller(dictName=self.dict_name)
        distilled.load_distilled_file()
        for entry in distilled.entries:
            self.entry_content[entry.lexid] = entry

    def parse_oed_file(self):
        tree = etree.parse(self.oed_file)
        for entry in tree.findall('./link'):
            oed_id = entry.get('sourceID')
            lexid = entry.get('targetID')
            if lexid and not oed_id in self.links:
                self.links[oed_id] = lexid

    def translate_id(self, id):
        if not self.links:
            self.parse_link_file()
        try:
            return self.links[id]
        except KeyError:
            try:
                return self.links_reversed[id]
            except KeyError:
                return None

    def find_content(self, lexid):
        if not self.entry_content:
            self.parse_distilled_file()
        if lexid in self.entry_content:
            return self.entry_content[lexid]
        else:
            lexid2 = self.translate_id(lexid)
            if lexid2 is not None and lexid2 in self.entry_content:
                return self.entry_content[lexid2]
        return None

    def find_lemma(self, lexid, locale=None):
        entry = self.find_content(lexid)
        if entry is not None:
            if locale is None or locale in ('uk', 'default'):
                return entry.headword
            elif locale == 'us' and entry.headword_us:
                return entry.headword_us
        return None

    def find_definition(self, lexid, wordclass=None):
        entry = self.find_content(lexid)
        if entry is not None:
            if wordclass is None:
                return entry.wordclass_blocks[0].definition
            else:
                for posg in entry.wordclass_blocks:
                    if posg.wordclass == wordclass:
                        return posg.definition
                if wordclass in ('NN', 'NP'):
                    for posg in entry.wordclass_blocks:
                        if posg.wordclass in ('NN', 'NP'):
                            return posg.definition
        return None


    #===========================================================
    # Methods to test whether an OED lemma is included in ODE/NOAD as a
    # derivative; needs special handling since these aren't explicitly linked.
    #===========================================================

    def index_derivatives(self):
        if not self.entry_content:
            self.parse_distilled_file()
        self.derivatives = {}
        for lexid in self.entry_content:
            e = self.entry_content[lexid]
            for sub in e.subentries:
                j = sub[2].replace('-', '')
                self.derivatives[j] = (lexid, sub[0], sub[1])

    def find_derivative(self, lemma, wordclass, end_date):
        if not self.derivatives:
            self.index_derivatives()
        lemma = lemma.replace('-', '')
        lemma = lemma.replace('~', '')
        if (lemma in self.derivatives and
            end_date is not None and
            end_date > 1850 and
            wordclass == self.derivatives[lemma][2]):
            return (self.derivatives[lemma][0], self.derivatives[lemma][1])
        return (None, None)


class LinkInferrer(object):

    """
    Infers links from OED to NOAD, based on links from OED to ODE and
    from ODE to NOAD.
    """

    def __init__(self, **kwargs):
        self.in_file = kwargs.get('inFile')
        self.out_file = kwargs.get('outFile')

    def infer(self):
        noad_map = {}
        dst = Distiller(dictName='ode')
        dst.load_distilled_file()
        for e in dst.entries:
            noad_id = None
            for p in e.wordclass_blocks:
                if p.complement is not None:
                    noad_id = p.complement
            if noad_id is not None:
                noad_map[e.lexid] = noad_id

        tree = etree.parse(self.in_file)
        entries = tree.findall('./link')
        for e in entries:
            e.attrib.pop('targetHref')
            oed_id = e.get('sourceID')
            lexid = e.get('targetID')
            if lexid in noad_map:
                e.set('targetID', noad_map[lexid])
            else:
                e.getparent().remove(e)
        tree.getroot().set('type', 'noad')

        with open(self.out_file, 'w') as filehandle:
            filehandle.write(etree.tostring(tree,
                                            pretty_print=True,
                                            encoding='unicode'))


class LinkUpdater(object):
    error_message = '!ERROR entry not found'

    def __init__(self, **kwargs):
        self.dict_name = kwargs.get('dictName')
        self.oed_in = kwargs.get('oedIn', None)
        self.oed_out = kwargs.get('oedOut', None)
        self.odo_in = kwargs.get('odoIn', None)
        self.odo_out = kwargs.get('odoOut', None)

        self.oed_index = VitalStatisticsCache()

        self.odo_index = Distiller(dictName=self.dict_name)
        self.odo_index.load_distilled_file()

    def update_odo(self, **kwargs):
        valid_links_only = kwargs.get('validLinksOnly', False)
        tree = etree.parse(self.odo_in)
        for entry in tree.findall('./e'):
            lexid = entry.get('lexid', None)
            odo_label = entry.find('./label')
            odo_label_text = self.odo_index.headword_by_id(lexid) or LinkUpdater.error_message
            etree.strip_tags(odo_label, 'i', 'sup', 'sub', 'hm')
            odo_label.text = odo_label_text
            link = entry.find('./linkSet/link')

            if link is not None:
                refentry = link.get('refentry', '0')
                refid = link.get('refid', '0')
                oed_label_text = self.oed_index.find(refentry, field='label') or LinkUpdater.error_message
                etree.strip_tags(link, 'i', 'sup', 'sub', 'hm')
                link.text = oed_label_text

            if (valid_links_only and
                (link is None or
                 link.text == LinkUpdater.error_message or
                 odo_label.text == LinkUpdater.error_message or
                 not check_match(link.text, odo_label.text))):
                entry.getparent().remove(entry)

        with open(self.odo_out, 'w') as filehandle:
            filehandle.write(etree.tostring(tree,
                                            pretty_print=True,
                                            encoding='unicode'))

    def update_oed(self, **kwargs):
        valid_links_only = kwargs.get('validLinksOnly', False)
        tree = etree.parse(self.oed_in)
        for entry in tree.findall('./link'):
            oed_id = entry.get('sourceID', None)
            oed_label_text = self.oed_index.find(oed_id, field='label') or LinkUpdater.error_message
            source_label = entry.find('./sourceLabel')
            etree.strip_tags(source_label, 'i', 'sup', 'sub', 'hm')
            source_label.text = oed_label_text

            lexid = entry.get('targetID', None)
            ode_label_text = self.odo_index.headword_by_id(lexid) or LinkUpdater.error_message
            target_label = entry.find('./targetLabel')
            etree.strip_tags(target_label, 'i', 'sup', 'sub', 'hm')
            target_label.text = ode_label_text

            if (valid_links_only and
                (oed_id is None or
                 lexid is None or
                 source_label.text == LinkUpdater.error_message or
                 target_label.text == LinkUpdater.error_message or
                 not check_match(source_label.text, target_label.text))):
                entry.getparent().remove(entry)

        with open(self.oed_out, 'w') as filehandle:
            filehandle.write(etree.tostring(tree,
                                            pretty_print=True,
                                            encoding='unicode'))

def check_match(label1, label2):
    """
    Confirm that the source and the target really do represent
    the same lemma (to avoid cases where the mapping tables are in error
    or map heterogeneous lemmas, e.g. 'hog-nosed' to 'hog-nosed bat')
    """
    normalized = []
    for label in (label1, label2):
        label = re.sub(r', .*$', '', label)
        hw_set = set()
        for headword in label.split(' | '):
            headword = headword.strip()
            for sub in (
                (r'\|.*$', ''),
                (r'\'s[ -]', ' '),
                (r'\'s *$', ''),
                (r'^(a|an|the) ', ''),
                (r' & ', ' and '),
            ):
                headword = re.sub(sub[0], sub[1], headword)
            headword = lexical_sort(headword)
            for sub in (
                ('ian', 'ean'),
                ('draft', 'draught'),
                ('plow', 'plough'),
                ('gray', 'grey'),
                ('ae', 'e'),
                ('oe', 'e'),
                ('re', 'er'),
                ('qu', 'c'),
            ):
                headword = headword.replace(sub[0], sub[1])
            for sub in (
                (r'[aeiouy]+$', ''),
                (r'[aeiouy]+', 'V'),
                (r'(.)\1', r'\1'),
                (r'^(h|ch)', ''),
                (r'([dszcrtfklvbnm])h', r'\1'),
            ):
                headword = re.sub(sub[0], sub[1], headword)
            for sub in (
                ('z', 's'),
                ('sch', 's'),
                ('sk', 's'),
                ('sc', 's'),
                ('ph', 'f'),
                ('j', 'g'),
                ('ck', 'c'),
                ('ch', 'c'),
                ('k', 'c'),
            ):
                headword = headword.replace(sub[0], sub[1])
            hw_set.add(headword)
        normalized.append(hw_set)

    if normalized[0].intersection(normalized[1]):
        return True
    for hw1 in normalized[0]:
        for hw2 in normalized[1]:
            if (abs(len(hw1) - len(hw2)) <= 1 and
                hw1 and
                hw2 and
                hw1[0] == hw2[0] and
                hw1[-1] == hw2[-1]):
                return True
            if (len(hw1) == len(hw2) and
                hw1 and
                hw2 and
                hw1[-1] == hw2[-1]):
                mismatches = [pair for pair in zip(hw1, hw2)
                              if pair[0] != pair[1]]
                if len(mismatches) <= 1:
                    return True

    return False
