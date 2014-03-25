"""
MorphSet -- corresponds to <MorphSet> element in ODE/NOAD.
MorphGroup -- corresponds to <MorphGroup> element in ODE/NOAD.
MorphUnit -- corresponds to <MorphUnit> element in ODE/NOAD.

@author: James McCracken
"""

import copy
from collections import defaultdict

from lxml import etree  # @UnresolvedImport

from lex.odo.odecomponent import OdeComponent
from lex.lemma import Lemma
from lex.wordclass.wordclass import Wordclass

WORDCLASS_SORT_ORDER = ('NN', 'NNS', 'VB', 'VBZ', 'VBG', 'VBD', 'VBN',
                        'JJ', 'JJR', 'JJS', 'RB', 'RBR', 'RBS', 'NP')
VARIANTS_SORT_ORDER = ('default', 'uk', 'ize', 'us', 'ise', 'deprecated')


class MorphSet(OdeComponent):

    """
    ODE/NOAD morphSet class.
    """

    def __init__(self, node):
        OdeComponent.__init__(self, node)
        self.strip_elements('ph')
        self.strip_attributes('noteid')
        self.id = node.get('id')

    def reference(self):
        return self.node.get('ref')

    def is_empty(self):
        if not self.morphunits():
            return True
        else:
            return False

    def morphunits(self):
        try:
            return self._morphunits
        except AttributeError:
            self._morphunits = []
            for node in self.node.findall('./morphUnit'):
                unit = MorphUnit(node)
                if (unit.form and unit.wordclass and
                    Wordclass(unit.wordclass).penn is not None):
                    self._morphunits.append(unit)
            return self._morphunits

    def morphgroups(self):
        try:
            return self._morphgroups
        except AttributeError:
            temp_groups = defaultdict(list)
            for unit in self.morphunits():
                temp_groups[unit.variant_type].append(unit)
            temp_groups = reassign_defaults(temp_groups)

            self._morphgroups = [MorphGroup(group) for group in
                                 temp_groups.values()]
            self._morphgroups.sort(key=lambda g: _variant_sort(g.variant_type))
            for morph_group in self._morphgroups:
                morph_group.parent_id = self.id
            return self._morphgroups


class MorphGroup(object):

    """
    ODE/NOAD morphgroup class.
    """

    def __init__(self, morph_units):
        self.morphunits = morph_units
        self.morphunits.sort(key=lambda unit: _wordclass_sort(unit.wordclass))
        self.score = 0
        self.parent_id = 0
        self.signature = '%'.join([unit.wordclass + '-' + unit.form
                                   for unit in self.morphunits])

    @property
    def lemma(self):
        return self.morphunits[0].form

    @property
    def baseclass(self):
        return self.morphunits[0].wordclass

    @property
    def variant_type(self):
        return self.morphunits[0].variant_type

    def to_node(self, serialized=False):
        node = etree.Element('morphSet', pos=self.baseclass)
        for unit in self.morphunits:
            child = unit.to_node()
            node.append(child)
        etree.strip_attributes(node, 'variantType')
        node.set('variantType', self.variant_type)
        node.set('score', str(self.score))
        node.set('sort', self.lexical_sort())

        if serialized:
            return etree.tostring(node)
        else:
            return node

    def to_node_lite(self):
        node = etree.Element('morphSet', pos=self.baseclass)
        for unit in self.morphunits:
            child = etree.SubElement(node, 'unit', pos=unit.wordclass)
            child.text = unit.form
        node.set('variantType', self.variant_type)
        node.set('score', str(self.score))
        return node

    def lexical_sort(self):
        try:
            return self._lexical_sort
        except AttributeError:
            self._compose_sort_values()
            return self._lexical_sort

    def initial(self):
        try:
            return self._initial
        except AttributeError:
            self._compose_sort_values()
            return self._initial

    def prefix(self):
        try:
            return self._prefix
        except AttributeError:
            self._compose_sort_values()
            return self._prefix

    def _compose_sort_values(self):
        lemma_manager = Lemma(self.morphunits[0].form)
        self._lexical_sort = lemma_manager.lexical_sort()
        self._initial = lemma_manager.initial()
        self._prefix = lemma_manager.prefix()


class MorphUnit(object):

    """
    ODE/NOAD morphUnit class.
    """

    def __init__(self, node):
        self.form = node.findtext('./wordForm')
        self.wordclass = node.get('pos')
        self.variant_type = node.get('variantType', 'default')

        if self.wordclass in ('NNM',):
            self.wordclass = 'NN'
        elif self.wordclass in ('NNP', 'NNPS', 'NPS'):
            self.wordclass = 'NP'

    def to_node(self, serialized=False):
        node = etree.Element('morphUnit',
                             variantType=self.variant_type,
                             pos=self.wordclass)
        child = etree.SubElement(node, 'wordForm')
        child.text = self.form

        if serialized:
            return etree.tostring(node)
        else:
            return node


def _variant_sort(variant_type):
    variant_type = variant_type.lower()
    try:
        score = VARIANTS_SORT_ORDER .index(variant_type)
    except ValueError:
        score = 20
    return score

def _wordclass_sort(wordclass):
    wordclass = wordclass.upper()
    try:
        score = WORDCLASS_SORT_ORDER.index(wordclass)
    except ValueError:
        score = 20
    return score

def reassign_defaults(groups):
    if 'default' in groups and 'uk' in groups and 'us' in groups:
        for variant_type in ('us', 'uk'):
            groups = _copy_defaults(groups, variant_type)
        del groups['default']
    elif 'default' in groups:
        for variant_type in ('us', 'deprecated'):
            if variant_type in groups:
                groups = _copy_defaults(groups, variant_type)
    return groups

def _copy_defaults(groups, variant_type):
    for unit in groups['default']:
        if any([unit.wordclass == prior_unit.wordclass
                for prior_unit in groups[variant_type]]):
            pass
        else:
            unit_new = copy.deepcopy(unit)
            unit_new.variant_type = variant_type
            groups[variant_type].append(unit_new)
    return groups
