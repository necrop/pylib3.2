"""
mainsenses - functions for finding, indexing, and returning the main
sense of each <s1> block in each main entry.
"""

import os
import string
from collections import namedtuple, defaultdict

from lxml import etree  # @UnresolvedImport

from lex import lexconfig
from stringtools import lexical_sort
from lex.oed.mainsensecalculator import calculate_main_sense

DEFAULT_INPUT = lexconfig.OEDLATEST_TEXT_DIR
DEFAULT_OUTPUT = lexconfig.OED_MAIN_SENSES_DIR

LETTERS = string.ascii_lowercase
PARSER = etree.XMLParser(remove_blank_text=True)


class MainSensesCache(object):

    """
    Cache and deliver the main-senses data for OED entries by reading in
    from XML store.
    """

    blocks = {}
    entries = {}
    minor_homographs = defaultdict(set)

    def __init__(self, **kwargs):
        self.dir = kwargs.get('main_senses_dir') or DEFAULT_OUTPUT
        self.with_definitions = kwargs.get('with_definitions', False)
        # Maximum number of senses stored for each block
        self.max_senses = kwargs.get('max_senses', 3)

    def find_block_data(self, entry_id, block_id):
        """
        Return the block corresponding to the entry_id + block_id. Return
        None if there's no corresponding block.

        If block_id is '0', return a list of all the blocks in the entry
        given by the entry ID (there'll usually only be one). Return an
        empty list if the entry ID does not exist.
        """
        if not MainSensesCache.entries:
            self._load_cache()

        entry_id = int(entry_id)
        block_id = int(block_id)
        if not block_id:
            try:
                return MainSensesCache.entries[entry_id]
            except KeyError:
                return []
        else:
            address = (entry_id, block_id)
            try:
                return MainSensesCache.blocks[address]
            except KeyError:
                return None

    def find_main_sense_data(self, entry_id, block_id):
        """
        Return the main sense from within the block corresponding to the
        entry_id + block_id. Return None if there's no corresponding block.
        """
        block_data = self.find_block_data(entry_id, block_id)
        if block_data and block_data.senses:
            return block_data.senses[0]
        else:
            return None

    def main_sense_from_block(self, block):
        """
        Given a lex.oed.S1block instance, returns the main sense
        from within that <s1> block.
        """
        main_sense = None
        if block.tag == 's1':
            # Look up the main-sense data in the cache
            block_data = self.find_block_data(block.entry_id, block.node_id())
            if block_data and block_data.senses:
                main_sense_data = block_data.senses[0]
                # Find the corresponding sense in the block
                for s in block.senses():
                    if int(s.node_id()) == main_sense_data.sense_id:
                        main_sense = s
                        break
        return main_sense

    def is_main_sense(self, entry_id, sense_id):
        """
        Return True if the sense passed (identified by its node ID)
        is recorded as the main sense for its block. Return False otherwise.

        N.b. Tests if this is the main sense for its <s1> block, not
        necessarily the main sense for its *entry*.
        """
        blocks = self.find_block_data(entry_id, 0)
        for block in blocks:
            if block.is_main_sense(entry_id, sense_id):
                return True
        return False

    def is_among_main_senses(self, entry_id, sense_id):
        """
        Return True if the sense passed (identified by its node ID)
        is recorded as one of the main senses for its block.

        Typically this will mean top 3; but may be fewer if
        self.max_senses has been set to a lower value.
        """
        blocks = self.find_block_data(entry_id, 0)
        for block in blocks:
            if block.is_among_main_senses(entry_id, sense_id):
                return True
        return False

    def is_minor_sense(self, entry_id, sense_id, lemma):
        blocks = self.find_block_data(entry_id, 0)
        if not blocks:
            return False

        for block in blocks:
            if not block.is_minor_sense(entry_id, sense_id, lemma):
                return False
        return True

    def is_in_minor_homograph(self, entry_id, lemma, wordclass):
        blocks = self.find_block_data(entry_id, 0)
        for b in blocks:
            if b.wordclass == wordclass:
                block = b
                break
        else:
            try:
                block = blocks[0]
            except IndexError:
                block = None
        if (block and block.matches_headword(lemma) and
                block.entry_id in MainSensesCache.minor_homographs and
                block.block_id in MainSensesCache.minor_homographs[block.entry_id]):
            return True
        else:
            return False

    def _load_cache(self):
        for letter in LETTERS:
            fname = os.path.join(self.dir, letter + '.xml')
            doc = etree.parse(fname, PARSER)
            for entry in doc.findall('e'):
                blocks = _parse_entry(entry,
                                      self.with_definitions,
                                      self.max_senses)
                for block in blocks:
                    address = (block.entry_id, block.block_id)
                    MainSensesCache.blocks[address] = block

        # Index all the blocks by entry ID
        for block in MainSensesCache.blocks.values():
            try:
                MainSensesCache.entries[block.entry_id]
            except KeyError:
                MainSensesCache.entries[block.entry_id] = []
            MainSensesCache.entries[block.entry_id].append(block)

        # Identify minor homographs
        homographs = defaultdict(list)
        for block in MainSensesCache.blocks.values():
            address = (lexical_sort(block.headword), block.wordclass)
            homographs[address].append(block)
        for homograph_set in homographs.values():
            if len(homograph_set) > 1:
                homograph_set.sort(key=lambda b: b.quotations, reverse=True)
                for h in homograph_set[1:]:
                    MainSensesCache.minor_homographs[h.entry_id].add(h.block_id)
                    MainSensesCache.minor_homographs[h.entry_id].add(h.wordclass)


#===============================================================
# Classes representing per-block and per-sense data sets
#===============================================================

# The named tuples store all the data attributes; the classes
#  act as container adding some extra methods
_BlockData = namedtuple('_BlockData', ['entry_id', 'block_id', 'label',
    'headword', 'wordclass', 'num_senses', 'num_current_senses',
    'num_large_senses', 'quotations', 'senses'])
SenseData = namedtuple('SenseData', ['sense_id', 'sense_number',
    'quotations', 'marked', 'definition', 'thesaurus_ids'])


class BlockData(_BlockData):

    # We use slots to prevent consuming more memory than necessary
    __slots__ = ()

    def confidence(self):
        """
        Return a confidence measure (int between 0 and 10) indicating
        confidence that the first sense really is the main current sense
        """
        if not self.senses:
            conf = 0
        elif self.num_senses == 1:
            conf = 10
        elif self.num_current_senses == 1:
            conf = 9
        elif self.senses[0].marked:
            conf = 8
        elif self.num_large_senses == 1:
            conf = 8
        elif self.num_senses == 2:
            conf = 9
        elif self.num_current_senses == 2:
            conf = 8
        elif self.num_large_senses == 2:
            conf = 7
        elif self.num_large_senses >= 15:
            conf = 1
        elif self.num_large_senses >= 8:
            conf = 2
        elif self.num_large_senses >= 5:
            conf = 3
        elif self.num_large_senses >= 3:
            conf = 4
        elif self.num_current_senses >= 15:
            conf = 1
        elif self.num_current_senses >= 8:
            conf = 2
        elif self.num_current_senses >= 5:
            conf = 3
        elif self.num_current_senses >= 3:
            conf = 4
        else:
            conf = 6
        return conf

    def is_main_sense(self, entry_id, sense_id):
        """
        Return True if this is the main sense listed for the block.
        """
        if (self.entry_id == int(entry_id) and
                self.senses and
                self.senses[0].sense_id == int(sense_id)):
            return True
        else:
            return False

    def is_among_main_senses(self, entry_id, sense_id):
        """
        Return True if this is one of the (up to) three main senses
        listed for the block.
        """
        if self.entry_id == int(entry_id):
            for sense in self.senses:
                if sense.sense_id == int(sense_id):
                    return True
        return False

    def matches_headword(self, lemma, exact=False):
        """
        Return True if the lemma matches the entry headword (which would
        indicate that this is a regular sense and not a subentry)
        """
        if exact and lemma == self.headword:
            return True
        elif not exact and lexical_sort(lemma) == lexical_sort(self.headword):
            return True
        else:
            return False

    def is_minor_sense(self, entry_id, sense_id, lemma):
        """
        Return True if this is not among the main senses, and does not
        appear to be a subentry.
        """
        if (not self.is_among_main_senses(entry_id, sense_id) and
                self.matches_headword(lemma)):
            return True
        else:
            return False


def _parse_entry(entry, with_definition, max_senses):
    entry_id = int(entry.get('refentry'))
    label = entry.find('./label').text
    headword = entry.find('./headword').text

    blocks = []
    for s1_node in entry.findall('./s1'):
        block_id = int(s1_node.get('refid'))
        wordclass = s1_node.get('wordclass')
        num_senses = int(s1_node.get('senses'))
        num_current_senses = int(s1_node.get('currentSenses'))
        num_large_senses = int(s1_node.get('largeSenses'))
        num_quotations = int(s1_node.get('quotations'))
        block = BlockData(
            entry_id,
            block_id,
            label,
            headword,
            wordclass,
            num_senses,
            num_current_senses,
            num_large_senses,
            num_quotations,
            [],
        )

        for sense_node in s1_node.findall('./sense'):
            sense_id = int(sense_node.get('refid'))
            quotations = float(sense_node.get('quotations'))
            sense_number = sense_node.get('number')
            thes = sense_node.get('thesaurus')
            if thes:
                thes_ids = [int(t) for t in thes.split('|')]
            else:
                thes_ids = []
            if with_definition:
                definition = sense_node.text
            else:
                definition = None
            marked = bool(sense_node.get('marked'))
            sense = SenseData(
                sense_id,
                sense_number,
                quotations,
                marked,
                definition,
                thes_ids,
            )
            block.senses.append(sense)

        while len(block.senses) > max_senses:
            block.senses.pop()
        blocks.append(block)
    return blocks


#===============================================================
# Functions to compute and store the tables of main-sense data
#===============================================================

def store_main_senses(**kwargs):
    """
    Store main-sense data for OED entries as XML documents.
    """
    from lex.entryiterator import EntryIterator
    oed_dir = kwargs.get('oed_dir') or DEFAULT_INPUT
    out_dir = kwargs.get('out_dir') or DEFAULT_OUTPUT

    for letter in LETTERS:
        print('Collecting main-sense data in %s...' % letter)
        filter_pattern = 'oed_%s.xml' % letter.upper()
        iterator = EntryIterator(path=oed_dir,
                                 dictType='oed',
                                 fixLigatures=True,
                                 fileFilter=filter_pattern,
                                 verbosity=None)

        doc = etree.Element('entries')
        for entry in iterator.iterate():
            entry.check_revised_status()
            entry_node = etree.SubElement(doc, 'e',
                                          refentry=entry.id,)
            label_node = etree.SubElement(entry_node, 'label')
            label_node.text = entry.label()
            hw_node = etree.SubElement(entry_node, 'headword')
            hw_node.text = entry.headword

            for block in entry.s1blocks():
                ranking, num_current, num_large, num_quotations =\
                    calculate_main_sense(block)

                if ranking:
                    wordclass = block.primary_wordclass().penn or 'null'
                    num_senses = len(block.senses())
                    s1_node = etree.SubElement(entry_node, 's1',
                        wordclass=wordclass,
                        refid=block.node_id(),
                        senses=str(num_senses),
                        currentSenses=str(num_current),
                        largeSenses=str(num_large),
                        quotations=str(num_quotations),)
                    for sense in ranking[0:3]:
                        sense_num = sense.sense_number() or 'null'
                        thes_links = '|'.join(sense.thesaurus_nodes())
                        sense_node = etree.SubElement(
                            s1_node,
                            'sense',
                            refid=sense.node_id(),
                            number=sense_num,
                            quotations=str(sense.qcount),)
                        if sense.marked:
                            sense_node.set('marked', 'true')
                        sense_node.text = sense.definition(length=100)
                        if thes_links:
                            sense_node.set('thesaurus', thes_links)

        with open(os.path.join(out_dir, letter + '.xml'), 'w') as filehandle:
            filehandle.write(etree.tounicode(doc, pretty_print=True))

if __name__ == '__main__':
    store_main_senses()
