#-------------------------------------------------------------------------------
# Name: Lexicalizations
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import csv
import re
import os
import random
import MySQLdb

from stringsimplifier import StringSimplifier
from dbpedia import DBpedia
from dbpedialookup import DbpediaLookup


table_name = "lexicalization"
fields = ("sort", "surface", "resource", "pUri", "pSfGivenUri", "pUriGivenSf", "pmi")
query = "select " + ", ".join(fields) + """ from lexicalization where sort = %s"""
predicates = fields[3:]
dbp = DBpedia()
dbp_lookup = DbpediaLookup()

credentials = {"user": "root",
               "passwd": "shapo1MYSQL",
               "db": "dbpedia",
               "charset": "utf8",
               "use_unicode": True}


class LexicalizationFinder(object):

    def __init__(self):
        con = MySQLdb.connect(**credentials)
        self.cursor = con.cursor()

    def find(self, string):
        sort_key = StringSimplifier(string).dictionary_sort
        self.cursor.execute(query, (sort_key,))
        #row = [i.decode("utf-8") for i in row]
        return SurfaceSet(sort_key, self.cursor.fetchall())


class SurfaceSet(object):

    def __init__(self, sort_key, lex_list):
        self.sort_key = sort_key
        self.lex = []
        for row in lex_list:
            j = Lexicalization(row)
            if j.disambiguations():
                for da in j.disambiguations():
                    k = Lexicalization(row)
                    k.resource_src = da.replace("http://dbpedia.org/resource/", "")
                    self.lex.append(k)
            else:
                self.lex.append(j)
        self.reorder("label")

    def deduplicate(self):
        self.reorder("pUri")
        seen = {}
        tmp = []
        for l in self.lex:
            if not l.resource in seen:
                tmp.append(l)
                seen[l.resource] = 1
        self.lex = tmp
        self.reorder("label")

    def key(self):
        return self.sort_key

    def lexicalizations(self, order=None, exact=None):
        if order is None:
            order = "label"
        if order != self.sort_order:
            self.reorder(order)
        if exact is None:
            return self.lex
        else:
            return [l for l in self.lex if l.label == exact]

    def reorder(self, order):
        if self.lex:
            if not order in self.lex[0].__dict__:
                order = "label"
            self.lex.sort(key=lambda a: a.__dict__[order])
            if order[0] == "p":
                self.lex.reverse()
        self.sort_order = order

    def size(self):
        return len(self.lex)


class Lexicalization(object):
    CACHE_MAX = 100
    graph_cache = {}

    def __init__(self, tup):
        row = list(tup)
        for i in (3, 4, 5, 6):
            if row[i] is not None:
                row[i] = float(row[i])
        self.key = row[0]
        self.label = row[1]
        self.resource_src = row[2]
        self.pUri = row[3]
        self.pSfGivenUri = row[4]
        self.pUriGivenSf = row[5]
        self.pmi = row[6]

    def dbpedia_lookup(self):
        try:
            return self.dbpedia_lookup_att
        except AttributeError:
            self.dbpedia_lookup_att = None
            results = dbp_lookup.find(self.label_redirected)
            for r in results:
                if r.resource == self.resource:
                    self.dbpedia_lookup_att = r
            return self.dbpedia_lookup_att

    @property
    def refcount(self):
        if self.dbpedia_lookup() is not None:
            return self.dbpedia_lookup().refcount
        else:
            return 0

    def graph(self):
        if not self.resource_src in Lexicalization.graph_cache:
            self.trim_cache()
            g = dbp.load_graph(self.resource_src, redirect=True)
            Lexicalization.graph_cache[self.resource_src] = g
            if g is not None:
                Lexicalization.graph_cache[g.resource_name] = g
        return Lexicalization.graph_cache[self.resource_src]

    def trim_cache(self):
        while len(Lexicalization.graph_cache) >= Lexicalization.cache_max:
            key = random.choice(Lexicalization.graph_cache.keys())
            del Lexicalization.graph_cache[key]

    @property
    def resource(self):
        if self.graph() is None:
            return ""
        else:
            return self.graph().resource_name

    @property
    def label_redirected(self):
        if self.graph() is None:
            return self.label
        else:
            return self.graph().label

    def num_triples(self):
        if self.graph() is None:
            return 0
        else:
            return len(self.graph())

    def abstract(self):
        return dbp.abstract(self.graph())

    def abstract_short(self, length):
        if (self.abstract() is not None and
            len(self.abstract()) > length + 10):
            return self.abstract()[0:length]
        else:
            return self.abstract()

    def types(self):
        return dbp.types(self.graph())

    def is_type(self, type):
        type = type.lower().replace("_", "").replace(" ", "")
        for t in self.types():
            t = t.replace("http://dbpedia.org/ontology/", "")
            t = t.replace("http://dbpedia.org/class/yago/", "")
            if type == t.lower():
                return True
        return False

    def types_contain(self, string):
        string = string.lower()
        for t in self.types():
            t = t.replace("http://dbpedia.org/ontology/", "")
            t = t.replace("http://dbpedia.org/class/yago/", "")
            if string in t.lower():
                return True
        return False

    def disambiguations(self):
        return dbp.disambiguations(self.graph())


class DbaseBuilder(object):

    def __init__(self, csv_file):
        self.in_file = csv_file

    def initialize(self):
        self.null_table()
        self.template = self.construct_template()

    def null_table(self):
        self.cursor.execute("truncate table lexicalization")
        self.cursor.execute("delete from lexicalization")
        self.cursor.execute("alter table lexicalization modify surface varchar(150) character set utf8")
        self.cursor.execute("alter table lexicalization modify resource varchar(150) character set utf8")

    def process(self):
        con = MySQLdb.connect(**credentials)
        self.cursor = con.cursor()

        self.initialize()

        count = 0
        self.reader = csv.reader(open(self.in_file, "rb"))
        for row in self.reader:
            row = [i.decode("utf-8") for i in row]
            srt = StringSimplifier(row[0]).dictionary_sort
            if len(srt) < 100 and len(row[0]) < 100 and len(row[1]) < 100:
                values = (srt,
                          row[0],
                          row[1],
                          float(row[2]),
                          float(row[3]),
                          float(row[4]),
                          float(row[5]))
                self.cursor.execute(self.template, values)
                count +=1
                if count > 1000:
                    print repr(row[0])
                    con.commit()
                    count = 0

        con.commit()
        con.close()

    def construct_template(self):
        t = "INSERT INTO " + table_name + " ("
        t += ", ".join(fields)
        t += ") VALUES (%s, %s, %s, %s, %s, %s, %s)"
        return t


class CsvBuilder(object):

    def __init__(self, in_file, out_file):
        self.in_file = in_file
        self.out_file = out_file
        self.unichar = re.compile(r"\\u([0-9A-F]{4})")

    def process(self):
        label_regex = re.compile(r"^<([^<>]*)> <http://lexvo.org/ontology#label> (.*?)@en <([^<>]*)>")
        triple_regex = re.compile(r"^<([^<>]*)> +<([^<>]*)> +(.*)$")

        self.writer = csv.writer(open(self.out_file, "wb"))
        self.signatures = {}
        self.buffer = {}
        for line in open(self.in_file, "r"):
            line = line.decode().strip()
            line = line.split("^^<http")[0]
            match = label_regex.search(line)
            if match is not None:
                if len(self.signatures) >= 100:
                    self.flush_buffer()
                resource, label, signature = match.groups()
                label = self.clean_label(label)
                print repr(label) + "\t" + repr(resource)
                resource = resource.replace("http://dbpedia.org/resource/", "")
                self.signatures[signature] = (resource, label)
            else:
                match = triple_regex.search(line)
                if match is not None:
                    signature, predicate, value = match.groups()
                    predicate = predicate.replace("http://spotlight.dbpedia.org/vocab/", "")
                    if not signature in self.buffer:
                        self.buffer[signature] = {}
                    self.buffer[signature][predicate] = float(value.strip(" \""))

        self.flush_buffer()

    def flush_buffer(self):
        for signature in self.buffer.keys():
            if signature in self.signatures:
                resource, label = self.signatures[signature]
                row = [label.encode("utf-8"), resource.encode("utf-8")]
                for predicate in predicates:
                    if predicate in self.buffer[signature]:
                        row.append(self.buffer[signature][predicate])
                    else:
                        row.append(None)
                self.writer.writerow(row)
        self.buffer = {}
        self.signatures = {}

    def clean_label(self, string):
        string = string.strip(" \"")
        while self.unichar.search(string):
            match = self.unichar.search(string)
            char = unichr(int(match.group(1), 16))
            string = self.unichar.sub(char, string, count=1)
        string = re.sub(u"([a-z])\u2019s", r"\1's", string)
        string = string.replace("&nbsp;", " ")
        string = string.replace("&ndash;", u"\u2013")
        return string





if __name__ == "__main__":
    #source_file = "C:/j/work/gutenberg/dbpedia/lexicalizations_en.nq"
    #csv_file = "C:/j/work/gutenberg/dbpedia/lexicalizations.csv"
    #j = CsvBuilder(source_file, csv_file)
    #j.process()
    #j = DbaseBuilder(csv_file)
    #j.process()

    test_set = ("Our Lady of the Visitation", "William Somerset Maugham",
                "Cassius Clay", "Oxford", "Paris", "Germany", "London", "Dublin", "Bristol",
                "Blake", "Portugal", "Lisbon", "Surrey", "Germany",
                "Scotland", "Bleak House")

    j = LexicalizationFinder()
    for label in (test_set):
        print label
        surface_set = j.find(label)
        for lex in surface_set.lexicalizations():
            if True or lex.resource_src != lex.resource:
                print repr(lex.label), lex.resource, str(lex.pUriGivenSf), str(lex.pmi), str(lex.refcount)
                print repr(lex.label_redirected)

    #tot = 0
    #for l in k.lexicalizations(order="pUriGivenSf"):
    #    print repr(l.label), l.resource, str(l.pUriGivenSf), str(l.pmi)
    #    if l.label == "Bleak House":
    #        tot += l.pUriGivenSf
    #print str(tot)
