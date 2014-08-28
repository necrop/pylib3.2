"""
ArticleIterator -- Iterate through Wikipedia dump files, yielding
one article at a time
"""

import re
import os

from lxml import etree

from wikipedia import wikipediaconfig
from wikipedia.article import Article

DEFAULT_DIR = wikipediaconfig.DUMP_SEGMENTED_DIR
PARSER = etree.XMLParser(remove_blank_text=True)


class ArticleIterator(object):

    """
    Iterate through Wikipedia dump files, yielding
    one article at a time
    """

    def __init__(self, **kwargs):
        self.verbose = kwargs.get('verbose', False)
        self.in_dir = kwargs.get('in_dir') or DEFAULT_DIR
        self.out_dir = kwargs.get('out_dir')
        self.article_count = 0
        self._files = None
        self.current_file = None
        self.current_doc = None

        # Probably only used for diagnostics - if you just want to
        # process one or two files in the directory
        file_filter = kwargs.get('file_filter', None)
        if file_filter is not None:
            self._filecheck_pattern = re.compile(file_filter)
        else:
            self._filecheck_pattern = None

    def files(self):
        """
        Return a list of files from the directory or directories listed
        in self.path.

        These are the files that self.iterate() will parse in turn.
        """
        if not self._files:
            self._files = [os.path.join(self.in_dir, fname) for fname in
                           sorted(os.listdir(self.in_dir)) if
                           fname.endswith('.xml')]
            self._files = [f for f in self._files if self._filecheck(f)]
        return self._files

    def _filecheck(self, filename):
        """
        Check that the filename matches the filecheck pattern (if any).
        """
        if (self._filecheck_pattern is not None and
                not self._filecheck_pattern.search(filename)):
            return False
        else:
            return True

    def file_count(self):
        """
        Return the number of files found in self.files().
        """
        return len(self.files())

    def iterate(self):
        """
        Iterate over the set of XML files, parsing each file and yielding
        one article at a time.
        """
        self.article_count = 0
        for filepath in self.files():
            self.current_file = filepath
            if self.verbose:
                print('Reading %s...' % self.current_file)
            self.current_doc = etree.parse(self.current_file, PARSER)
            for article_node in self.current_doc.findall('./page'):
                article = Article(article_node)
                if article.wikicode_parses():
                    yield article

            if self.out_dir:
                self.write_output()

    def file_number(self):
        """
        Return the number of the file currently being processed.
        """
        filename = os.path.basename(self.current_file)
        return int(os.path.splitext(filename)[0])

    def write_output(self):
        """
        Write a (version of) the current file to the output directory.
        """
        filename = os.path.basename(self.current_file)
        filepath = os.path.join(self.out_dir, filename)
        with open(filepath, 'w') as filehandle:
            filehandle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            filehandle.write(etree.tounicode(self.current_doc,
                                             pretty_print=True))