"""
DataIterator -- iterate through all the data in the GEL files.
OedContentIterator -- yield OED-linked content only.

@author: James McCracken
"""

import string
import os

from lex import lexconfig
from lex.gel.fileiterator import FileIterator

LETTERS = string.ascii_lowercase


class DataIterator(object):

    """
    Iterate through all the data in the GEL files, yielding
    one entry at a time.
    """

    def __init__(self, in_dir):
        self.in_dir = in_dir or lexconfig.GEL_DATA_DIR

    def iterate(self, **kwargs):
        if kwargs.get('letter'):
            alphabet = [kwargs.get('letter').lower(), ]
        else:
            alphabet = LETTERS
        for letter in alphabet:
            directory = os.path.join(self.in_dir, letter)
            iterator = FileIterator(in_dir=directory,
                                    out_dir=None,
                                    verbosity='low')
            for file_contents in iterator.iterate():
                for entry in file_contents.entries:
                    yield entry


class OedContentIterator(object):

    """
    Wrapper for DataIterator, but returns OED-linked items only.

    Note that this returns individual wordclass-set objects,
    not entries - and is therefore better aligned with OED entries,
    which tend to cover a single wordclass.
    """

    def __init__(self, **kwargs):
        self.in_dir = kwargs.get('in_dir')
        self.letter = kwargs.get('letter')
        self.include_entries = kwargs.get('include_entries', True)
        self.include_subentries = kwargs.get('include_subentries', False)

    def iterate(self):
        iterator = DataIterator(self.in_dir)
        for entry in iterator.iterate(letter=self.letter):
            for wordclass_set in entry.wordclass_sets():
                if wordclass_set.link(target='oed') is None:
                    continue
                if ((wordclass_set.oed_entry_type() == 'entry' and
                        self.include_entries) or
                        (wordclass_set.oed_entry_type() == 'subentry' and
                        self.include_subentries)):
                    yield wordclass_set
