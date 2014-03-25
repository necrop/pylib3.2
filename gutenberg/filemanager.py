#-------------------------------------------------------------------------------
# Name: FileManager
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import re
import os
import shutil
import zipfile
import codecs

from .gutenbergtext import GutenbergText

class FileManager(object):

    def __init__(self, dir=None, catalog=None):
        self.parent_dir = dir
        self.catalog = catalog

    def directories(self):
        try:
            return self.sub_dirs
        except AttributeError:
            d = sorted([d for d in os.listdir(self.parent_dir) if\
                        os.path.isdir(os.path.join(self.parent_dir, d))])
            self.sub_dirs = d
            return self.sub_dirs

    def texts(self):
        try:
            return self.text_data
        except AttributeError:
            self.text_data = [FileData(os.path.join(self.parent_dir, d),
                              self.catalog.find(d)) for d in self.directories()]
            return self.text_data


class FileData(object):

    def __init__(self, dir, cat_entry):
        self.dir = dir
        self.cat_entry = cat_entry
        if cat_entry is not None:
            self.author = cat_entry.author
            self.title = cat_entry.title
            self.id = cat_entry.id
            self.genre = cat_entry.genre
        else:
            self.author = None
            self.title = None
            self.id = None
        self.deleted = False

    def files(self, extension=None):
        files = [os.path.join(self.dir, f) for f in os.listdir(self.dir)]
        if extension is not None:
            files = [f for f in files if os.path.splitext(f)[1] == extension]
        return [f for f in files if os.path.isfile(f)]

    def subdirectories(self):
        dirs = [os.path.join(self.dir, f) for f in os.listdir(self.dir)]
        return [d for d in dirs if os.path.isdir(d)]

    def filepath(self, type=None):
        f = os.path.join(self.dir, type + ".txt")
        if os.path.isfile(f):
            return f
        else:
            return None

    def filesize(self, type=None):
        if self.filepath(type=type) is not None:
            return os.stat(self.filepath(type=type)).st_size
        else:
            return 0

    def delete(self):
        shutil.rmtree(self.dir)
        self.deleted = True

    def unzip(self, overwrite=None, voluble=None):
        if overwrite is None or not overwrite:
            overwrite = False
        else:
            overwrite = True
        if voluble is None or not voluble:
            voluble = False
        else:
            voluble =True
        if overwrite and self.filepath(type="src") is not None:
            os.unlink(self.filepath(type="src"))
        if self.filepath(type="src") is None:
            if self.files(extension=".zip"):
                zip_path = self.files(extension=".zip")[0]
                if voluble:
                    print "Unzipping " + zip_path + "..."
                z = zipfile.ZipFile(zip_path, "r")
                text_files = [n for n in z.namelist() if\
                              (os.path.splitext(n)[1] == ".txt" or
                               os.path.splitext(n)[1] == ".TXT")]
                for n in text_files:
                    z.extract(n, self.dir)
                    os.rename(os.path.join(self.dir, n),
                              os.path.join(self.dir, "src.txt"))
                    break
                z.close()

    def decruft(self, overwrite=None):
        if overwrite is None or not overwrite:
            overwrite = False
        else:
            overwrite = True
        if (self.filepath(type="src") is not None and
            (overwrite or self.filepath(type="decrufted") is None)):
            gt = GutenbergText(self.filepath(type="src"))
            lines = gt.decruft_lines()
            fo = codecs.open(os.path.join(self.dir, "decrufted.txt"), "w",
                             encoding="iso-8859-1")
            for l in gt.decruft_lines():
                fo.write(l)
                fo.write("\n")
            fo.close()

    def text_object(self):
        if self.filepath(type="decrufted") is not None:
            text_obj = GutenbergText(self.filepath(type="decrufted"))
        elif self.filepath(type="src") is not None:
            text_obj = GutenbergText(self.filepath(type="src"))
        else:
            text_obj = GutenbergText("")
            text_obj.set_lines([])
        text_obj.set_catalog_entry(self.cat_entry)
        return text_obj
