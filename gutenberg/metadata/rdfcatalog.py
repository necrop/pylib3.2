#-------------------------------------------------------------------------------
# Name: RdfCatalog
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import re
import os
from lxml import etree


ns = {"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
      "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
      "xsi": "http://www.w3.org/2001/XMLSchema-instance",
      "dc": "http://purl.org/dc/elements/1.1/",
      "dcterms": "http://purl.org/dc/terms/",
      "dcmitype": "http://purl.org/dc/dcmitype/",
      "cc": "http://web.resource.org/cc/",
      "pgterms": "http://www.gutenberg.org/rdfterms/"}

paths = {
    "a1": "./{%s}creator/{%s}Bag/{%s}li" % (ns["dc"], ns["rdf"], ns["rdf"],),
    "a2": "./{%s}creator" % (ns["dc"],),
    "c1": "./{%s}contributor/{%s}Bag/{%s}li" % (ns["dc"], ns["rdf"], ns["rdf"],),
    "c2": "./{%s}contributor" % (ns["dc"],),
    "t": "./{%s}title" % (ns["dc"],),
    "l": "./{%s}language/{%s}ISO639-2/{%s}value" % (ns["dc"], ns["dcterms"], ns["rdf"],),
    "d": "./{%s}created/{%s}W3CDTF/{%s}value" % (ns["dc"], ns["dcterms"], ns["rdf"],)
}

date_pattern = re.compile(r", (\d{4})\??-(\d{4})\??$")

cat = []
cat_map = {}


class RdfCatalog(object):

    def __init__(self, catalog=None):
        self.cat_file = catalog

    def parse(self):
        global cat, cat_map
        tree = etree.parse(self.cat_file)
        cat = [CatalogEntry(n) for n in\
               tree.findall("./{%s}etext" % (ns["pgterms"],))]
        for e in cat:
            cat_map[e.id] = e
        cat.sort(key=lambda a: a.id)

    def entries(self):
        if not cat:
            self.parse()
        return cat

    def find(self, id):
        if not cat:
            self.parse()
        id = int(id)
        try:
            return cat_map[id]
        except KeyError:
            return None

    def untranslated_english_entries(self, entries=None):
        if entries is None:
            entries = self.entries
        return [e for e in self.filter_for_english(entries=entries) if
                (not e.has_foreign_classification() and
                 not e.has_translator())]

    def filter_for_english(self, entries=None):
        if entries is None:
            entries = self.entries
        return self.filter_by_language(entries=entries, language="en")

    def filter_by_language(self, entries=None, language=None):
        if entries is None:
            entries = self.entries
        return [e for e in entries() if e.language == language]

    def filter_by_date(self, entries=None, start=None, end=None):
        output = []
        if entries is None:
            entries = self.entries
        for e in entries:
            if (start is not None and
                (e.author_dates()[1] is None or
                 e.author_dates()[1] < int(start))):
                continue
            if (end is not None and
                (e.author_dates()[0] is None or
                 e.author_dates()[0] > int(end))):
                continue
            output.append(e)
        return output

    def authors_by_frequency(self, entries=None):
        if entries is None:
            entries = self.entries
        authors = {}
        for e in entries:
            if e.author:
                if e.author in authors:
                    authors[e.author] += 1
                else:
                    authors[e.author] = 1
        afreq = []
        for j in sorted(authors.keys(), key=lambda a: authors[a], reverse=True):
            afreq.append((j, authors[j]))
        return afreq


class CatalogEntry(object):

    def __init__(self, n):
        id = n.get("{" + ns["rdf"] + "}ID").replace("etext", "")
        self.id = int(id)
        self.idpad = "%06d" % (self.id,)

        vals = [n.findtext(paths["a1"]) or n.findtext(paths["a2"]) or "",
                n.findtext(paths["t"]) or "",
                n.findtext(paths["l"]) or "",
                n.findtext(paths["d"]) or ""]
        vals = [char_decode(v) for v in vals]

        self.author = vals[0]
        self.title = vals[1]
        self.language = vals[2]
        self.datestamp = vals[3]

        self.contributors = [k.text for k in n.findall(paths["c1"])] or\
                            [k.text for k in n.findall(paths["c2"])]
        self.contributors = [char_decode(v) for v in self.contributors]

        self.subs = {}
        self.subs["lcsh"] = [k.text for k in\
                             n.xpath("./dc:subject//dcterms:LCSH/rdf:value",
                             namespaces=ns)]
        self.subs["lcc"] = [k.text for k in\
                            n.xpath("./dc:subject//dcterms:LCC/rdf:value",
                            namespaces=ns)]
        for t in self.subs.keys():
            self.subs[t] = [char_decode(v) for v in self.subs[t]]
        self.filepaths = []

    def subjects(self, type=None):
        if type is None:
            j = self.subs["lcsh"][:]
            j.extend(self.subs["lcc"])
            return j
        else:
            type = type.lower()
            try:
                return self.subs[type]
            except KeyError:
                return []

    def has_foreign_classification(self):
        for letter in "ABCDFGHJKLMQT":
            c = "P" + letter
            if c in self.subjects(type="lcc"):
                return True
        return False

    def has_translator(self):
        for contrib in self.contributors:
            if "translator" in contrib.lower():
                return True
        return False

    def is_verse(self):
        if "poems" in self.title.lower() or "poetry" in self.title.lower():
            return True
        for subj in self.subjects(type="lcsh"):
            if "poems" in subj.lower() or "poetry" in subj.lower():
                return True
        return False

    def is_drama(self):
        if "dramatic works" in self.title.lower():
            return True
        for subj in self.subjects(type="lcsh"):
            if "drama" in subj.lower() or "tragedies" in subj.lower():
                return True
        return False

    def is_fiction(self):
        for subj in self.subjects(type="lcsh"):
            if "fiction" in subj.lower():
                return True
        for subj in self.subjects(type="lcsh"):
            if "biography" in subj.lower():
                return False
        if ("PR" in self.subjects(type="lcc") or
            "PS" in self.subjects(type="lcc") or
            "PZ" in self.subjects(type="lcc")):
                return True
        return False

    def author_dates(self):
        m = date_pattern.search(self.author)
        if m is not None:
            return (int(m.group(1)), int(m.group(2)))
        else:
            return (None, None)


def char_decode(chars):
    chars = chars.replace("\n", ": ").replace("  ", " ").replace(": (", " (")
    chars = chars.strip()
    if type(chars) is str:
        chars = chars.decode("utf-8")
    return chars
