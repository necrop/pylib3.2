"""
FileIterator -- Iterate over the GEL data files

@author: James McCracken
"""

import os
import re
import string

from lxml import etree

from lex import lexconfig
from lex.gel.gelcomponents import GelEntry

GEL_DATA_DIR = lexconfig.GEL_DATA_DIR
PARSER = etree.XMLParser(remove_blank_text=True)


def entry_iterator(**kwargs):
    """
    Wrapper to FileIterator which yields individual entries rather
    than complete file objects.

    Optional keyword argument 'letters' allows you to specify
    a particular letter or group of letters, e.g. letters='abc'.
    If no argument is supplied, all letters are processed.
    """
    letters = (kwargs.get('letters') or kwargs.get('letter')
               or string.ascii_lowercase)
    for letter in letters.lower():
        directory = os.path.join(GEL_DATA_DIR, letter)
        iterator = FileIterator(in_dir=directory)
        for filecontent in iterator.iterate():
            for entry in filecontent.entries:
                yield(entry)


class FileIterator(object):

    """
    Iterator yielding a GelFileContent object for every GEL XML
    file in the directory specified
    """

    def __init__(self, **kwargs):
        self.in_dir = kwargs.get('in_dir')
        self.out_dir = kwargs.get('out_dir')
        self.verbosity = kwargs.get('verbosity')
        self.file_filter = kwargs.get('fileFilter') or kwargs.get('file_filter')
        self.first_file = kwargs.get('start')
        self.last_file = kwargs.get('end')
        self.clear_output = kwargs.get('clearOutput') or kwargs.get('clear_output')
        self.files = sorted([f for f in os.listdir(self.in_dir)
                             if os.path.splitext(f)[1] == '.xml'])

    def clear_outdir(self):
        """
        Empty the output directory (if out_dir has been specified). 
        """
        for filename in os.listdir(self.out_dir):
            os.unlink(os.path.join(self.out_dir, filename))

    def iterate(self):
        """
        Iterate over the list of files in the directory, yielding
        each as a GelFileContent object.
        """
        if self.clear_output and self.out_dir:
            self.clear_outdir()
        for i, in_file in enumerate(self.files):
            self.in_file = in_file
            if (self.file_filter and
                    not re.search(self.file_filter, self.in_file)):
                continue
            if (self.first_file and
                    self.file_number() < int(self.first_file)):
                continue
            if (self.last_file and
                    self.file_number() > int(self.last_file)):
                continue

            if self.verbosity:
                print('Doing %s from %s (%d/%d)' % (self.in_file,
                                                    self.in_dir,
                                                    i + 1,
                                                    len(self.files)))
            fpath = os.path.join(self.in_dir, self.in_file)
            node = etree.parse(fpath, PARSER)
            self.filecontent = GelFileContent(node, fpath)
            yield self.filecontent
            if self.out_dir:
                self.write_output()

    def file_number(self):
        """
        Return the number of the file currently being processed.
        """
        full = os.path.basename(self.in_file)
        return int(os.path.splitext(full)[0])

    def write_output(self):
        """
        Write a (version of) the current file to the output directory.
        """
        filepath = os.path.join(self.out_dir, self.in_file)
        with open(filepath, 'w') as filehandle:
            filehandle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            filehandle.write(etree.tounicode(self.filecontent.node,
                                             pretty_print=True))


class GelFileContent(object):

    def __init__(self, node, filepath):
        self.node = node
        self.filepath = filepath
        self.entries = [GelEntry(n, filepath) for n in self.node.findall('./e')]

    def file_letter(self):
        if self.filepath:
            path = os.path.split(self.filepath)[0]
            return os.path.basename(path)
        else:
            return None

    def file_number(self):
        if self.filepath:
            fname = os.path.basename(self.filepath)
            return int(os.path.splitext(fname)[0])
        else:
            return None

    def entry_by_id(self, id):
        results = []
        for entry in self.entries:
            if entry.id == id:
                results.append(entry)
        if not results:
            for entry in self.entries:
                if entry.oed_id() == id:
                    results.append(entry)
        if not results:
            for entry in self.entries:
                if entry.oed_lexid() == id:
                    results.append(entry)
        return results
