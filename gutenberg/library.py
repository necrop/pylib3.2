"""
Library - class for managing the library of Gutenberg texts
"""

import os
import csv

from gutenberg import gutenbergconfig
from gutenberg.textmanager import TextManager


class Library:

    def __init__(self):
        self.directory = gutenbergconfig.TEXT_DIR
        self.catalogue = Catalogue(self.directory)
        self._texts = None

    @property
    def texts(self):
        if self._texts is None:
            ids = []
            for id in [f for f in os.listdir(self.directory) if
                       os.path.isdir(os.path.join(self.directory, f))]:
                try:
                    id = int(id)
                except ValueError:
                    pass
                else:
                    ids.append(id)
            ids.sort()
            self._texts = [TextManager(idnum) for idnum in ids]
        return self._texts

    def text(self, idnum):
        idnum = int(idnum)
        for t in self.texts:
            if t.id == idnum:
                return t
        return None

    def update(self):
        for text in self.texts:
            if text.convert_source(check_first=True):
                print('Converted %d to text.' % text.id)
        self.catalogue.update(self.texts)


class Catalogue:

    def __init__(self, dir):
        self.file = os.path.join(dir, 'catalogue.csv')

    def update(self, texts):
        rows = []
        for text in texts:
            md = text.metadata
            row = [text.id, md.author, md.title, md.year]
            rows.append(row)
        with open(self.file, 'w') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerows(rows)
