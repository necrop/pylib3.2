"""
VariantsCache - system for retrieving cached XML variant-form lists
to_xml()
from_xml()

@author: James McCracken
"""

import os
from collections import namedtuple, defaultdict

from lxml import etree  # @UnresolvedImport

from lex.oed.variants.variantform import VariantForm
from lex.oed.daterange import DateRange
from lex import lexconfig

DEFAULT_DIR = lexconfig.OED_VARIANTS_DIR
MINIMUM_DATE = 1200
VariantSet = namedtuple('VariantSet', ['entry_id', 'lexid', 'lemma',
                        'wordclass', 'num_quotations', 'date',
                        'revised_status', 'variants'])


class VariantsCache(object):

    """
    System for retrieving variant-form lists that have been parsed
    previously and cached as XML documents (using VariantsLister).

    An example XML tree looks like this:

    <e vfsect="unrevised" id="19532" size="199">
      <hw>bite</hw>
      <dateRange start="1000" end="2006" projected="2050" status="exact"/>
      <s1 wordclass="VB" size="199" lexid="19489644">
        <dateRange start="1000" end="2006" projected="2050" status="exact"/>
        <def>trans. To cut into, pierce, or nip (anything)...</def>
        <variants wordclass="VB">
          <vf start="1150" end="2050">bite</vf>
          <vf start="1500" end="2050">bate</vf>
          <vf start="1500" end="1699">bight</vf>
          <vf start="1150" end="1599">byte</vf>
          <vf start="1500" end="1599">bait</vf>
          <vf start="1000" end="1499" enEnding="true">bítan</vf>
          <vf start="1150" end="1499" enEnding="true">biten</vf>
          <vf start="1150" end="1499">bett</vf>
          <vf start="1150" end="1499">bited</vf>
          <vf start="1150" end="1499">bete</vf>
          <vf start="1150" end="1499" regional="true">bayte</vf>
        </variants>
        <variants wordclass="VBD">
          <vf start="1600" end="2050">bit</vf>
          <vf start="1150" end="1599">bote</vf>
          <vf start="1000" end="1499">bát</vf>
          <vf start="1150" end="1499">bot</vf>
          <vf start="1150" end="1499">boot</vf>
          <vf start="1150" end="1499">boght</vf>
          <vf start="1150" end="1499">biten</vf>
          <vf start="1000" end="1149">biton</vf>
        </variants>
        <variants wordclass="VBN">
          <vf start="1600" end="2050">bitten</vf>
          <vf start="1700" end="1899">bit</vf>
          <vf start="1000" end="1499">biten</vf>
          <vf start="1150" end="1499">byten</vf>
          <vf start="1150" end="1499">bittin</vf>
          <vf start="1150" end="1499">ybite</vf>
          <vf start="1150" end="1499">ibyten</vf>
        </variants>
      </s1>
    </e>
    """

    cache = None

    def __init__(self, **kwargs):
        self.directory = kwargs.get('dir') or DEFAULT_DIR
        self.wordclasses = kwargs.get('wordclasses')

    def load_cache(self, **kwargs):
        files = sorted([f for f in os.listdir(self.directory)
                        if f.endswith('.xml')])
        VariantsCache.cache = defaultdict(list)
        limit = kwargs.get('limit')
        self.num_varsets = 0
        for filename in files:
            filepath = os.path.join(self.directory, filename)
            tree = etree.parse(filepath)
            for entry in tree.findall('./e'):
                entry_id = entry.get('id')
                revised_status = entry.get('vfsect', 'omitted')
                headword = entry.findtext('./hw')
                s1blocks = entry.findall('./s1')
                for block in s1blocks:
                    varset = _varset_factory(headword, entry_id,
                                             block, revised_status)
                    if (self.wordclasses is None or
                        self.contains_wordclasses(varset)):
                        # Index by both headword and ID
                        VariantsCache.cache[headword].append(varset)
                        VariantsCache.cache[entry_id].append(varset)
                        self.num_varsets += 1
                # Bail out once the limit is reached (if any)
                if limit and headword == limit:
                    return

    def contains_wordclasses(self, variant_set):
        if any([wordclass in variant_set.variants
                for wordclass in self.wordclasses]):
            return True
        else:
            return False

    def id_exists(self, entry_id):
        if not VariantsCache.cache:
            self.load_cache()
        if entry_id in VariantsCache.cache:
            return True
        else:
            return False

    def find_all(self, **kwargs):
        lemma = kwargs.get('lemma')
        entry_id = kwargs.get('id')
        wordclass = kwargs.get('wordclass')

        if not VariantsCache.cache:
            self.load_cache()

        variant_sections = []
        if lemma is not None and lemma in VariantsCache.cache:
            variant_sections = VariantsCache.cache[lemma]
        elif entry_id is not None and entry_id in VariantsCache.cache:
            variant_sections = VariantsCache.cache[entry_id]
        else:
            variant_sections = []

        if wordclass is not None:
            return [vs for vs in variant_sections if vs.wordclass == wordclass]
        else:
            return variant_sections[:]

    def find(self, **kwargs):
        candidates = self.find_all(**kwargs)
        # Sort so that the largest is at the top
        candidates.sort(key=lambda varset: varset.num_quotations)
        candidates.reverse()
        try:
            return candidates[0]
        except IndexError:
            return None

def _varset_factory(lemma, entry_id, node, revised_status):
    num_quotations = int(node.get('size', 0))
    lexid = node.get('lexid')
    wordclass = node.get('wordclass')

    # Date-range for the block
    projected_date = node.find('./dateRange').get('projected')
    if projected_date and int(projected_date) > 2000:
        obsolete = False
    else:
        obsolete = True
    date = DateRange(start=node.find('./dateRange').get('start'),
                     end=node.find('./dateRange').get('end'),
                     obs=obsolete)

    # Collect the variants themselves
    variants = {}
    for vblock in node.findall('./variants'):
        var_wordclass, vf_list = from_xml(vblock)
        variants[var_wordclass] = [vf for vf in vf_list
                                   if vf.date.end > MINIMUM_DATE and
                                   not vf.undated]

    return VariantSet(entry_id, lexid, lemma, wordclass, num_quotations,
                      date, revised_status, variants)

def to_xml(wordclass, vf_list):
    """
    Convert a list of VariantForm objects into a <variants> XML variants_node.
    """
    variants_node = etree.Element('variants')
    variants_node.set('wordclass', wordclass)

    for variant_form in vf_list:
        vf_node = etree.SubElement(variants_node, 'vf')
        vf_node.text = variant_form.form
        vf_node.set('start', str(variant_form.date.start))
        vf_node.set('end', str(variant_form.date.end))
        if variant_form.regional:
            vf_node.set('regional', 'true')
        if variant_form.irregular:
            vf_node.set('irregular', 'true')
        if variant_form.undated:
            vf_node.set('undated', 'true')
        if variant_form.has_en_ending:
            vf_node.set('enEnding', 'true')
        variants_node.append(vf_node)
    return variants_node

def from_xml(variants_node):
    """
    Convert a <variants> XML node into a list of VariantForm objects.
    """
    wordclass = variants_node.get('wordclass')
    vf_list = []
    for vf_node in variants_node.findall('./vf'):
        variant_form = VariantForm(vf_node.text,
                                   vf_node.get('start'),
                                   vf_node.get('end'))
        if vf_node.get('regional'):
            variant_form.regional = True
        if vf_node.get('irregular'):
            variant_form.irregular = True
        if vf_node.get('enEnding'):
            variant_form.has_en_ending = True
        if vf_node.get('undated'):
            variant_form.undated = True
        vf_list.append(variant_form)
    return (wordclass, vf_list)


#    @property
#    def variant_classes(self):
#        return self.vars.keys()

#    def variants(self, wordclass):
#        if wordclass == 'base':
#            wordclass = self.wordclass
#        try:
#            return self.vars[wordclass]
#        except KeyError:
#            return []
