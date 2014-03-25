"""
ContentIterator -- Iterator for HTOED content.

@author: James McCracken
"""

import re
import os

from lxml import etree

from lex import lexconfig
from lex.oed.thesaurus.thesaurusclass import ThesaurusClass

PARSER = etree.XMLParser(remove_blank_text=True)
DEFAULT_PATH = lexconfig.HTOED_CONTENT_DIR


class ContentIterator(object):

    """
    Iterator that runs through the HTOED data, yielding one class
    (ThesaurusClass instance) at a time.

    yield_mode argument:
     - If yield_mode is set to 'class' (default), one class will be yielded
        at a time
     - If yield_mode is set to 'file', a file's-worth of classes will be
        yielded at a time (as a list of ThesaurusClass instances).
    """

    def __init__(self, **kwargs):
        self.yield_mode = kwargs.get('yield_mode', 'class')
        self.verbosity = kwargs.get('verbosity', None)
        self.in_dir = kwargs.get('in_dir', DEFAULT_PATH)
        self.out_dir = kwargs.get('out_dir', None)
        self.class_count = 0

        # Probably only used for diagnostics - if you just want to
        # process one or two files in the directory
        file_filter = kwargs.get('file_filter', None)
        if file_filter:
            self._filecheck_pattern = re.compile(file_filter)
        else:
            self._filecheck_pattern = None
        self._files = None

    def files(self):
        """
        Return the list of files that will be processed.
        """
        if self._files is None:
            if isinstance(self.in_dir, list):
                self._files = self.in_dir[:]
            elif os.path.isfile(self.in_dir) and self.in_dir.endswith('.xml'):
                self._files = [self.in_dir, ]
            elif os.path.isdir(self.in_dir):
                self._files = [os.path.join(self.in_dir, fname) for fname in
                               os.listdir(self.in_dir)]
            else:
                self._files = []
            self._files = [f for f in self._files if self._filecheck(f)]
            self._files.sort()
        return self._files

    def _filecheck(self, fname):
        """
        Check whether a given file is usable -- return True if so,
        otherwise return False.
        """
        if not fname.lower().endswith('.xml'):
            return False
        elif (self._filecheck_pattern is not None and
              not self._filecheck_pattern.search(fname)):
            return False
        else:
            return True

    def file_count(self):
        """
        Return the number of files to be processed.
        """
        return len(self.files())

    def iterate(self):
        self.class_count = 0
        for filepath in self.files():
            if self.verbosity is not None:
                print('Reading %s...' % filepath)
            doc = etree.parse(filepath, PARSER)
            classes = [ThesaurusClass(tnode) for tnode in doc.findall('class')]
            if self.yield_mode == 'class':
                for c in classes:
                    self.class_count += 1
                    yield c
            elif self.yield_mode == 'file':
                self.class_count += len(classes)
                yield classes

            # Print the document to the output directory, if one
            #  has been specified
            if self.out_dir:
                filename = os.path.basename(filepath)
                out_file = os.path.join(self.out_dir, filename)
                with open(out_file, 'w') as filehandle:
                    filehandle.write(etree.tostring(doc,
                                                    pretty_print=True,
                                                    encoding='unicode'))
