"""
TableIterator: iterates over tables of Google Ngrams data
"""

import re
import os

from lex import lexconfig
from lex.gbn.ngram import Ngram

DIRECTORY = lexconfig.NGRAMS_TABLES_DIR


class TableIterator(object):

    """
    Iterate over tables of Google Ngrams data
    """

    def __init__(self, **kwargs):
        self.verbose = kwargs.get('verbose', False)
        self.gram_count = kwargs.get('gramCount', 1)

        letter = kwargs.get('letter')
        self.path = os.path.join(DIRECTORY, str(self.gram_count), letter)

        # Probably only used for diagnostics - if you just want to
        # process one or two files in the directory
        file_filter = kwargs.get('fileFilter')
        if file_filter:
            self.filecheck_pattern = re.compile(file_filter)
        else:
            self.filecheck_pattern = None

    def files(self):
        try:
            return self._files
        except AttributeError:
            files = [os.path.join(self.path, fname) for fname in
                     os.listdir(self.path) if
                     os.path.splitext(fname)[1] == '.txt']
            self._files = [f for f in files if self.filecheck(f)]
            return self._files

    def filecheck(self, filepath):
        if (self.filecheck_pattern and
            not self.filecheck_pattern.search(filepath)):
            return False
        else:
            return True

    def file_count(self):
        return len(self.files())

    def iterate(self):
        for filepath in self.files():
            if self.verbose:
                print('Reading %s...' % filepath)
            with open(filepath, 'r') as filehandle:
                lines = filehandle.readlines()
            for line in lines:
                n = Ngram(line, gramCount=self.gram_count)
                yield n
