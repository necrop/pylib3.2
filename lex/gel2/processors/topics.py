#-------------------------------------------------------------------------------
# Name: Topics
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import os
import csv
import re

from ...entryiterator import EntryIterator


class TopicManager(object):

    def __init__(self, **kwargs):
        self.odo_tax = self._parse_taxonomy("odo", kwargs.get("odoTaxonomy"))
        self.oed_tax = self._parse_taxonomy("oed", kwargs.get("oedTaxonomy"))
        self._build_mapping()

    def find_mapping(self, name, type):
        if name in self.hash[type]:
            return self.hash[type][name].map
        else:
            return None

    def taxonomy(self):
        return [t for t in self.odo_tax if t.level in (0, 1, 2)]

    def _parse_taxonomy(self, type, filepath):
        tax = []
        with (open(filepath, "r")) as fh:
            lines = [l.strip("\n").decode() for l in fh.readlines()]
        last = {-1: None, 0: None, 1: None, 2: None, 3: None, 4: None}
        for l in lines:
            m = re.search(r"^(\t*)([A-Z][a-z].*)$", l)
            level = len(m.group(1))
            content = re.sub(r"\t+", "=", m.group(2))
            if len(content.split("=")) == 2:
                content, equiv = content.split("=")
            else:
                equiv = None
            parent = last[level-1]
            rec = TaxElement(content, level, equiv, parent, type)
            tax.append(rec)
            last[level] = rec.id
        return tax

    def _build_mapping(self):
        self.hash = {"odo": {}, "oed": {}}
        for t in self.odo_tax:
            self.hash["odo"][t.id] = t
            self.hash["odo"][t.name] = t
        for t in self.oed_tax:
            self.hash["oed"][t.id] = t
            self.hash["oed"][t.name] = t

        for t in self.odo_tax:
            if t.parent_id is not None:
                t.parent = self.hash["odo"][t.parent_id]
            else:
                t.parent = None
        for t in self.oed_tax:
            if t.parent_id is not None:
                t.parent = self.hash["oed"][t.parent_id]
            else:
                t.parent = None

        for t in self.odo_tax:
            if t.level in (0, 1, 2):
                j = t.id
            elif t.parent.level in (0, 1, 2):
                j = t.parent.id
            elif t.parent.parent.level in (0, 1, 2):
                j = t.parent.parent.id
            elif t.parent.parent.parent.level in (0, 1, 2):
                j = t.parent.parent.parent.id
            elif t.parent.parent.parent.parent.level in (0, 1, 2):
                j = t.parent.parent.parent.parent.id
            t.map = self.hash["odo"][j]

        for t in self.oed_tax:
            t.map = None
            equiv = None
            if t.equivalent is not None:
                equiv = t.equivalent
            elif t.parent is not None:
                if t.parent.equivalent is not None:
                    equiv = t.parent.equivalent
                elif t.parent.parent is not None:
                    if t.parent.parent.equivalent is not None:
                        equiv = t.parent.parent.equivalent
                    elif t.parent.parent.parent is not None:
                        if t.parent.parent.parent.equivalent is not None:
                            equiv = t.parent.parent.parent.equivalent
                        elif t.parent.parent.parent.parent is not None:
                            if t.parent.parent.parent.parent.equivalent is not None:
                                equiv = t.parent.parent.parent.parent.equivalent
            if equiv is not None:
                for t2 in self.odo_tax:
                    if t2.name == equiv:
                        t.map = t2

    def load_entry_data(self, dir):
        self.entry_data = {"odo": {}, "oed": {}}
        for d in ("ode", "noad", "oed"):
            filepath = os.path.join(dir, d + "_topics.csv")
            if d == "oed":
                dtype = "oed"
            else:
                dtype = "odo"
            with (open(filepath, "rb")) as fh:
                csvreader = csv.reader(fh)
                for row in csvreader:
                    row = [r.decode("utf8") for r in row]
                    topics = [r for r in row[3:]]
                    nodes = set()
                    for t in topics:
                        taxnode = self.find_mapping(t, dtype)
                        if taxnode is not None:
                            nodes.add(taxnode.id)
                    if nodes:
                        sig = row[0] + "#" + (row[1] or "0")
                        self.entry_data[dtype][sig] = nodes

    def find_entry_data(self, entry_id, node_id, type):
        sig = entry_id + "#" + (node_id or "0")
        try:
            return self.entry_data[type][sig]
        except KeyError:
            return set()


class TaxElement(object):
    id = 0

    def __init__(self, name, level, equiv, parent, type):
        TaxElement.id += 1
        self.id = TaxElement.id
        self.name = name
        self.parent_id = parent
        self.level = level
        self.equivalent = equiv
        self.type = type




class TopicListerBase(object):

    def write(self):
        with (open(self.out_file, "wb")) as fh:
            csvwriter = csv.writer(fh)
            for r in self.results:
                row = [r[0], r[1], r[2].encode("utf8")]
                row.extend(sorted([t.encode("utf8") for t in r[3]]))
                csvwriter.writerow(row)


class OdoTopicLister(TopicListerBase):
    """Extract domClass topic data from full ODE or NOAD data
    """

    def __init__(self, **kwargs):
        self.in_file = kwargs.get("inFile")
        self.out_file = kwargs.get("outFile")

    def extract_topics(self):
        self.read_topics()
        self.write()

    def read_topics(self):
        lemlist = []
        EI = EntryIterator(path=self.in_file, dictType="ode")
        for e in EI.iterate():
            topix = set()
            for p in e.posgroups:
                core = [s for s in p.senses if s.type == "core"]
                for s in core[:3]:
                    topix = topix.union(s.topics())
            if topix:
                lemlist.append((e.id, None, e.headword, topix,))
            for sub in [sub for sub in e.subentries if sub.topics()]:
                lemlist.append((e.id, sub.nodeID, sub.lemma, sub.topics(),))
        self.results = lemlist



class OedTopicLister(TopicListerBase):
    """Extract subject data from full OED
    """

    def __init__(self, **kwargs):
        self.in_dir = kwargs.get("inDir")
        self.out_file = kwargs.get("outFile")

    def extract_topics(self):
        self.read_topics()
        self.write()

    def read_topics(self):
        lemlist = []
        EI = EntryIterator(path=self.in_dir, dictType="oed")
        for e in EI.iterate():
            if e.senses:
                s = e.senses[0]
                topix = s.characteristic_list("subject")
                topix = set([re.sub(r"^.*/", "", t) for t in topix])
                if topix:
                    lemlist.append((e.id, None, e.headword, topix))
            for s in [s for s in e.senses if s.is_subentry() or s.is_subentry_like()]:
                topix = s.characteristic_list("subject")
                topix = set([re.sub(r"^.*/", "", t) for t in topix])
                if topix:
                    lemlist.append((e.id, s.nodeID, s.lemma, topix))
        self.results = lemlist


