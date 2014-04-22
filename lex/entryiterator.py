"""
EntryIterator -- Dictionary entry Iterator for OED and ODE/NOAD

@author: James McCracken
"""

import re
import os

from lex import lexconfig
from lex.oed.entry import Entry as OedEntry
from lex.odo.entry import Entry as OdoEntry

ENTRY_PATTERNS = {'oed': re.compile('^<Entry[ >]'),
                  'ode': re.compile('^<e[ >]')}


class EntryIterator(object):

    """
    Dictionary entry Iterator (suitable for OED and ODE/NOAD)

    Usage:
    >>> iterator = EntryIterator(path='/path/to/data/',
                                 dictType='oed',
                                 verbosity='low',
                                 fixLigatures=True,
                                 fileFilter='[A-J]_oed.xml')
    >>> for entry in iterator.iterate():
            print(entry.label())

    This assumes that the input file(s) has 1 entry per line, i.e. each line
    beginning <Entry> or <e> can be parsed as well-formed XML. This won't work
    well for input files in which entries are broken over multiple lines, or
    in which there are multiple lines per entry; it'll probably mean that
    entries get missed.

    Keyword arguments:

     -- path (required): A directory, a filename, or a list of filenames.
            All filenames should refer to XML files and have a .xml extension;
            any filename in the list without a .xml extension will be skipped.
            - If a directory is supplied, the list of filenames is generated by
            globbing all the .xml files in that directory.
            - If a list of filenames is supplied, the list is processed in its
            original order; it's not re-sorted.

     -- dictType (optional): Either 'oed' (for OED-model dictionary) or 'ode'
            (for ODE-type dictionary, i.e. ODE or NOAD). If no dictType value is
            supplied, the iterator will try to figure this out by sampling
            the first few lines of the first file.

     -- verbosity (optional): None (default), 'low', or 'high'. 'low' prints the
            name of each file as it's opened. 'high' additionally prints the ID
            and headword of each entry as it's reached.

     -- fileFilter (optional): A regular expression matching one or more of
            the files in the directory. Only files matching the regular
            expression will be processed. e.g. fileFilter='[GHI]_oed.xml'

     -- fixLigatures (optional): If True, all 'ae' and 'oe' ligatures will be
            converted to plain 'ae' and 'oe'.

    EntryIterator.iterate() yields a sequence of OED or ODE entry objects
    (lex.oed.entry.Entry or lex.ode.entry.Entry).
    """

    def __init__(self, **kwargs):
        self.verbosity = kwargs.get('verbosity', None)
        self.dict = kwargs.get('dictType') or kwargs.get('dict_type', None)
        self.path = kwargs.get('path') or _default_source(self.dict)
        self.fix_ligatures = kwargs.get('fixLigatures') or kwargs.get('fix_ligatures', False)
        self.entry_count = 0

        if self.dict is not None:
            self.dict = self.dict.lower()
            if self.dict == 'noad':
                self.dict = 'ode'
            if self.dict not in ('oed', 'ode'):
                self.dict = None

        # Probably only used for diagnostics - if you just want to
        # process one or two files in the directory
        file_filter = kwargs.get('fileFilter') or kwargs.get('file_filter', None)
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
        try:
            return self._files
        except AttributeError:
            if isinstance(self.path, list):
                self._files = [fname for fname in self.path if
                               os.path.splitext(fname)[1] == '.xml']
            elif (os.path.isfile(self.path) and
                  os.path.splitext(self.path)[1] == '.xml'):
                self._files = [self.path]
            elif os.path.isdir(self.path):
                self._files = [os.path.join(self.path, fname) for fname in
                               sorted(os.listdir(self.path)) if
                               os.path.splitext(fname)[1] == '.xml']
            else:
                self._files = []
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
        one entry at a time.
        """
        if self.dict is None:
            self.dict = self._deduce_dict()

        self.entry_count = 0
        for filepath in self.files():
            if self.verbosity is not None:
                print('Reading %s...' % (filepath,))
            with open(filepath, encoding='utf-8') as filehandle:
                for line in filehandle:
                    entry = self._parse_line(line)
                    if entry:
                        yield entry

    def _parse_line(self, line):
        """
        Parse each line to determine if it's an entry; if so,
        use it to initialize and return an appropriate entry object.

        Otherwise return None.
        """
        line = line.strip()
        if ENTRY_PATTERNS[self.dict].match(line):
            if self.dict == 'oed':
                entry = OedEntry(line,
                                 fixLigatures=self.fix_ligatures)
            elif self.dict == 'ode':
                entry = OdoEntry(line)
            if self.verbosity == 'high':
                print('\t%s\t%s' % (entry.id, entry.headword,))
            self.entry_count += 1
            return entry
        else:
            return None

    def _deduce_dict(self):
        """
        Sample the start of the first file to determine whether
        this is ODE or OED.
        """
        ode_count, oed_count = (0, 0)
        for fname in self.files():
            with open(fname) as filehandle:
                for line in filehandle:
                    line = line.decode('utf8').strip()
                    if ENTRY_PATTERNS['oed'].match(line):
                        oed_count += 1
                    if ENTRY_PATTERNS['ode'].match(line):
                        ode_count += 1
                    if ode_count == 5 or oed_count == 5:
                        break
            if ode_count == 5 or oed_count == 5:
                break
        if ode_count > oed_count:
            return 'ode'
        else:
            return 'oed'


def _default_source(dict_type):
    """
    Return a default directory to use for input, if none has been
    explicitly supplied.

    Default directories use the settings in lex.lexconfig.
    """
    if dict_type.lower() == 'oed':
        source = lexconfig.OEDLATEST_TEXT_DIR
    elif dict_type.lower() == 'ode':
        source = lexconfig.ODE_TEXT_DIR
    elif dict_type.lower() == 'noad':
        source = lexconfig.NOAD_TEXT_DIR
    else:
        source = ''
    return source
