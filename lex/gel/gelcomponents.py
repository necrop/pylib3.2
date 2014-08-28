"""
gelcomponents: Components used in GEL data:

GelEntry --
WordclassSet --
MorphSet --
TypeUnit --

@author: James McCracken
"""

import os
import re

from lxml import etree  # @UnresolvedImport

from lex.oed.daterange import DateRange
from lex.frequencytable import FrequencyTable
from lex.lemma import Lemma

DEFINITION_PREFERENCES = ('ode', 'noad', 'oed', 'oed_rev', 'oed_unrev')


class _GelComponent(object):

    def __init__(self, **kwargs):
        self.node = kwargs.get('node')
        if self.node is None:
            self.node = kwargs.get('tree')
        self.filepath = kwargs.get('file')
        self.id = self.node.get('id')

    def file_letter(self):
        if self.filepath is not None:
            path = os.path.split(self.filepath)[0]
            return os.path.basename(path)
        else:
            return None

    def file_number(self):
        if self.filepath is not None:
            fname = os.path.basename(self.filepath)
            return int(os.path.splitext(fname)[0])
        else:
            return None

    def attribute(self, key):
        return self.node.get(key, None)

    def lexical_sort(self):
        return self.attribute('sort')

    dictionary_sort = lexical_sort

    def date(self):
        try:
            return self._date
        except AttributeError:
            date_node = self.node.find('./dateRange')
            self._date = DateRange(node=date_node, hardEnd=True)
            return self._date

    def fuzz_dates(self):
        if self.date() is not None:
            fuzzed_date_node = self.date().xml(fuzzed=True,
                                               omitProjected=True)
            old_date_node = self.node.find('./dateRange')
            if old_date_node is not None:
                self.node.replace(old_date_node, fuzzed_date_node)

    def wordclass(self):
        try:
            return self._wordclass
        except AttributeError:
            wnode = self.node.find('./wordclass')
            if wnode is not None:
                self._wordclass = wnode.get('penn')
            else:
                self._wordclass = None
            return self._wordclass

    def tostring(self):
        return etree.tostring(self.node)

    def is_computed(self):
        if self.attribute('computed'):
            return True
        else:
            return False

    def has_frequency_table(self):
        """
        Return True if this component includes a frequency table.
        """
        if self.frequency_table() is not None:
            return True
        else:
            return False

    def frequency_table(self):
        """
        Return a FrequencyTable object for this component's
        table of frequency data.
        """
        try:
            return self._frequency_table
        except AttributeError:
            n = self.node.find('./frequency')
            if n is not None:
                self._frequency_table = FrequencyTable(node=n)
            else:
                self._frequency_table = None
            return self._frequency_table

    def frequency(self):
        """
        Return the modern frequency for this component.
        """
        if not self.has_frequency_table():
            return 0
        else:
            return self.frequency_table().frequency()


class GelEntry(_GelComponent):

    def __init__(self, node, filename):
        _GelComponent.__init__(self, node=node, file=filename)

    def oed_id(self):
        return self.attribute('oedId')

    def oed_lexid(self):
        return self.attribute('oedLexid')

    def tag(self):
        return self.attribute('tag')

    def wordclass_sets(self):
        try:
            return self._wordclass_sets
        except AttributeError:
            self._wordclass_sets = [WordclassSet(n, self.filepath) for n in
                                    self.node.findall('./wordclassSet')]
            return self._wordclass_sets

    def definition(self, **kwargs):
        """
        Return the definition from the first wordclass block.
        """
        return self.wordclass_sets()[0].definition(**kwargs)

    def primary_wordclass(self):
        """
        Return the Penn wordclass from the first wordclass block.
        """
        return self.wordclass_sets()[0].wordclass()

    def lemma_manager(self):
        try:
            return self._lemma_manager
        except AttributeError:
            self._lemma_manager = Lemma(self.node.findtext('./lemma'))
            return self._lemma_manager

    @property
    def lemma(self):
        return self.lemma_manager().lemma

    @property
    def headword(self):
        return self.lemma_manager().lemma

    @property
    def sort(self):
        return self.lemma_manager().lexical_sort()

    def lemmas(self):
        return [Lemma(l.text) for l in self.node.findall('./lemma')]

    def us_variant(self):
        for l in self.node.findall('./lemma'):
            if l.get('locale') == 'us':
                return l.text
        return None

    def frequency(self):
        """
        Return the modern frequency for this entry.
        """
        # Entries don't have their own frequency tables; so we sum
        # the frequencies of its component wordclasses
        return sum([block.frequency() for block in self.wordclass_sets()])

    def date(self):
        """
        Return a DateRange object for this entry.
        """
        # Entries don't have their own date ranges; so we compile this
        # from the date ranges of its component wordclasses
        try:
            return self._date
        except AttributeError:
            start = min(block.date().start for block in self.wordclass_sets())
            end = max(block.date().end for block in self.wordclass_sets())
            exact_start = min(block.date().exact('start')
                              for block in self.wordclass_sets())
            exact_end = min(block.date().exact('end')
                            for block in self.wordclass_sets())
            self._date = DateRange(start=start, end=end)
            self._date.set_exact('start', exact_start)
            self._date.set_exact('end', exact_end)
            return self._date

    def types(self):
        types_list = []
        for block in self.wordclass_sets():
            types_list.extend(block.types())
        return types_list

    def morphsets(self):
        morphset_list = []
        for block in self.wordclass_sets():
            morphset_list.extend(block.morphsets())
        return morphset_list

    def oed_entry_type(self):
        for block in self.wordclass_sets():
            etype = block.oed_entry_type()
            if etype is not None:
                return etype
        return None


class WordclassSet(_GelComponent):

    def __init__(self, node, filename):
        _GelComponent.__init__(self, node=node, file=filename)

    def morphset_block(self):
        return self.node.find('./morphSetBlock')

    def morphsets(self):
        try:
            return self._morphsets
        except AttributeError:
            self._morphsets = [MorphSet(n, self.filepath) for n in
                               self.node.findall('./morphSetBlock/morphSet')]
            return self._morphsets

    def types(self):
        types_list = []
        for morphset in self.morphsets():
            types_list.extend(morphset.types())
        return types_list

    def size(self):
        try:
            return self._size
        except AttributeError:
            self._size = self.node.get('size', None)
            if self._size is not None:
                self._size = int(self._size)
            return self._size

    def set_size(self, size):
        self._size = int(size)

    def oed_entry_type(self):
        try:
            return self._oed_entry_type
        except AttributeError:
            self._oed_entry_type = None
            for rnode in self.node.findall('./resourceSet/resource'):
                if rnode.get('code') == 'oed':
                    self._oed_entry_type = rnode.get('type')
        return self._oed_entry_type

    def oed_revision_status(self):
        if 'oed_unrev' in self.definitions:
            return 'unrevised'
        elif 'oed_rev' in self.definitions:
            return 'revised'
        elif 'oed' in self.definitions:
            return 'revised'
        else:
            return None

    def lemma_manager(self):
        try:
            return self._lemma_manager
        except AttributeError:
            self._lemma_manager = Lemma(self.node.findtext('.//form'))
            return self._lemma_manager

    @property
    def lemma(self):
        return self.lemma_manager().lemma

    def definitions(self):
        try:
            return self._definitions
        except AttributeError:
            self._definitions = {}
            for dnode in self.node.findall('./definitions/definition'):
                self._definitions[dnode.get('src')] = dnode.text

            # Make sure there's a key for plain 'oed'
            oed_val = None
            for key, val in self._definitions.items():
                if key.startswith('oed_'):
                    oed_val = val
            if oed_val:
                self._definitions['oed'] = oed_val

            return self._definitions

    def definition(self, src=None):
        if src is not None:
            try:
                return self.definitions()[src]
            except KeyError:
                return None
        else:
            for dictionary in DEFINITION_PREFERENCES:
                if dictionary in self.definitions():
                    return self.definitions()[dictionary]
            return None

    def definition_source(self):
        for src in DEFINITION_PREFERENCES:
            if src in self.definitions:
                return src
        return None

    def link(self, **kwargs):

        def _split_components(target):
            components = target.split('#')
            if len(components) == 1:
                return (components[0], None)
            else:
                return (components[0], components[1].replace('eid', ''))

        target = kwargs.get('target', None)
        defragment = kwargs.get('defragment', False)
        return_as_tuple = kwargs.get('asTuple') or kwargs.get('as_tuple', False)
        target_type = kwargs.get('targetType') or kwargs.get('target_type', False)

        if target is None:
            return None
        else:
            target = target.lower()

        try:
            self._links_set
        except AttributeError:
            self._links_set = {}
            self._link_target_types = {}
            for rnode in self.node.findall('./resourceSet/resource'):
                id = rnode.get('xrid') or rnode.get('xid')
                if rnode.get('xnode'):
                    if target == 'oed':
                        id = id + '#eid' + rnode.get('xnode')
                    else:
                        id = id + '#' + rnode.get('xnode')
                self._links_set[rnode.get('code')] = id
                self._link_target_types[rnode.get('code')] = rnode.get('type') or 'entry'
        if target in self._link_target_types and target_type:
            return self._link_target_types[target]
        elif target in self._links_set and return_as_tuple:
            return _split_components(self._links_set[target])
        elif target in self._links_set and not defragment:
            return self._links_set[target]
        elif target in self._links_set:
            return re.sub(r'#.*$', '', self._links_set[target])
        elif return_as_tuple:
            return None, None
        else:
            return None


class MorphSet(_GelComponent):

    def __init__(self, node, filename):
        _GelComponent.__init__(self, node=node, file=filename)

    def types(self):
        try:
            return self._types
        except AttributeError:
            self._types = [TypeUnit(n, self.filepath)
                           for n in self.node.findall('./type')]
            for i, morph_type in enumerate(self._types):
                if i == 0:
                    morph_type.is_base = True
                else:
                    morph_type.is_base = False
            return self._types

    @property
    def form(self):
        return self.types()[0].form

    @property
    def sort(self):
        return self.types()[0].sort

    def is_irregular(self):
        return self.attribute('irregular') == 'true'

    is_nonstandard = is_irregular

    def is_regional(self):
        return self.attribute('regional') == 'true'

    def is_oed_headword(self):
        return self.attribute('oedHeadword') == 'true'

    def wordclass(self):
        try:
            return self.types()[0].wordclass()
        except IndexError:
            return None


class TypeUnit(_GelComponent):

    def __init__(self, node, filename):
        _GelComponent.__init__(self, node=node, file=filename)
        self.form = self.node.findtext('./form')
        self.is_base = False

    @property
    def sort(self):
        return self.lexical_sort() or self.lemma_manager().lexical_sort()

    def lemma_manager(self):
        try:
            return self._lemma_manager
        except AttributeError:
            self._lemma_manager = Lemma(self.form)
            return self._lemma_manager
