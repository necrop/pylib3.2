#-------------------------------------------------------------------------------
# Name: Soundfiles
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import os
import csv
import re
from collections import defaultdict

from ...entryiterator import EntryIterator

class SoundfileManager(object):

    def __init__(self, **kwargs):
        self.filemap = {}
        for d in ("ode", "noad"):
            self.filemap[d] = self._parse_file(os.path.join(
                              kwargs.get("dir"), d + ".csv"))

    def find_soundfile(self, lemma, pos=None):
        results = {}
        lemflat = self._lemma_normalizer(lemma, pos=="NP")
        for d in ("ode", "noad"):
            if lemflat in self.filemap[d]:
                if lemma in self.filemap[d][lemflat]:
                    for j in self.filemap[d][lemflat][lemma]:
                        soundfile = j
                else:
                    for proxy in self.filemap[d][lemflat]:
                        for j in self.filemap[d][lemflat][proxy]:
                            soundfile = j
            else:
                soundfile = None
            results[d] = soundfile
        return results

    def _parse_file(self, filepath):
        sf = defaultdict(lambda: defaultdict(set))
        with (open(filepath, "rb")) as fh:
            csvreader = csv.reader(fh)
            for row in csvreader:
                row = [r.decode("utf8") for r in row]
                lemma = row[0]
                lemflat = self._lemma_normalizer(lemma, row[1]=="NP")
                sf[lemflat][lemma].add(row[2])
        return sf

    def _lemma_normalizer(self, lemma, is_np):
        lemflat = lemma.strip()
        if is_np:
            lemflat = lemflat.split(",")[0]
        lemflat = lemflat.replace(" ", "-")
        if re.search(r"[a-z]", lemflat):
            lemflat = lemflat.lower()
        lemflat = re.sub(r"is(e|ed|es|er|ing|ation|ational)$", r"iz\1", lemflat)
        return lemflat



class SoundfileLister(object):

    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.in_file = kwargs.get("inFile")
        self.out_file = kwargs.get("outFile")

    def extract_soundfiles(self):
        self.read()
        self.write()

    def read(self):
        if self.name == "ode":
            attname = "gbSoundFile"
        else:
            attname = "usSoundFile"

        lemlist = []
        EI = EntryIterator(path=self.in_file, dictType="ode")
        for e in EI.iterate():
            if e.posgroups:
                wc = e.posgroups[0].wordclass
            else:
                wc = None

            filerefs = e.node.xpath("./hg/pr/ph/@%s" % attname)
            if filerefs:
                lemlist.append((e.headword, wc, filerefs[0]))

            for s in e.subentries:
                filerefs = s.node.xpath(".//ph/@%s" % attname)
                if filerefs:
                    lemlist.append((s.lemma, None, filerefs[0]))
        self.results = lemlist

    def write(self):
        with (open(self.out_file, "wb")) as fh:
            csvwriter = csv.writer(fh)
            for r in self.results:
                row = (r[0].encode("utf8"), r[1], r[2])
                csvwriter.writerow(row)
