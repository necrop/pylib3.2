#-------------------------------------------------------------------------------
# Name: catalog
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import re
import os
import csv

from linkeddata.dbpedia import DBpedia

filenames = {"authors": "authors.csv", "titles": "titles.csv"}
dir = None
titles = {}
authors = []
dbp = DBpedia()

class TitleSet(object):

    def __init__(self, path=None):
        global dir
        if path is not None:
            if ".csv" in os.path.basename(path):
                self.path = path
                dir = os.path.dirname(path)
            else:
                self.path = os.path.join(path, filenames["titles"])
                dir = path
        if not titles:
            self.load_data()

    def load_data(self):
        global titles
        columns = []
        reader = csv.reader(open(self.path, "rb"))
        for row in reader:
            row = [col.decode("utf8") for col in row]
            if row[0].lower() == "id":
                columns = [col.lower() for col in row]
            else:
                t = Title(row, columns)
                titles[t.id] = t

    def find(self, id):
        id = int(id)
        if id in self.titles:
            return self.titles[id]
        else:
            return None

    def titles(self):
        return [titles[id] for id in sorted(titles.keys())]

    def num(self):
        return len(titles.keys())



class AuthorSet(object):

    def __init__(self, path=None):
        global dir
        if path is not None:
            if ".csv" in os.path.basename(path):
                self.path = path
                dir = os.path.dirname(path)
            else:
                self.path = os.path.join(path, filenames["authors"])
                dir = path
        if not authors:
            self.load_data()

    def load_data(self):
        global authors
        columns = []
        reader = csv.reader(open(self.path, "rb"))
        for i, row in enumerate(reader):
            row = [col.decode("utf8") for col in row]
            if row[0].lower() == "id":
                columns = [col.lower() for col in row]
            else:
                a = Author(row, columns)
                authors.append(a)
        authors.sort(key=lambda a: a.gutenberg_name.lower())

    def find(self, id):
        for a in authors:
            if a.id == id or a.gutenberg_name == id:
                return a
        return None

    def authors(self):
        return authors

    def num(self):
        return len(authors)


class CatalogItem(object):

    def __init__(self, row, column_headers):
        for i, c in enumerate(column_headers):
            self.__dict__[c.lower()] = row[i]
        for c in column_headers:
            if not self.__dict__[c.lower()]:
                self.__dict__[c.lower()] = None

    def dbpedia_graph(self):
        try:
            return self.dbp_graph
        except AttributeError:
            if self.dbpedia_id is not None:
                self.dbp_graph = dbp.load_graph(self.dbpedia_id)
            else:
                self.dbp_graph = None
            return self.dbp_graph

    def dbpedia_properties(self, predicate=None, position=None):
        if self.dbpedia_graph() is not None:
            return dbp.property_list(graph=self.dbpedia_graph(),
                                     predicate=predicate,
                                     position=position)
        else:
            return []


class Title(CatalogItem):

    integers = ("id", "composition_date_start", "composition_date_end",
                "pub_date_start", "pub_date_end")

    def __init__(self, row, column_headers):
        CatalogItem.__init__(self, row, column_headers)
        for c in Title.integers:
            if self.__dict__[c] is not None:
                self.__dict__[c] = int(self.__dict__[c])
        if not self.composition_date_end:
            self.composition_date_end = self.composition_date_start
        if not self.pub_date_end:
            self.pub_date_end = self.pub_date_start
        self.dbpedia_id = self.dbpedia

    def authorObject(self):
        try:
            return self.author_object
        except AttributeError:
            self.author_object = AuthorSet().find(self.author)
            return self.author_object

    def author_age(self):
        return self.date(type="estimated") - self.authorObject().biodate("birth")

    def date(self, type=None):
        if type is None:
            type = "estimated"
        type = type.lower()

        if type == "publication" or type == "pub":
            if self.pub_date_start is None:
                return None
            else:
                return mean_average((self.pub_date_start, self.pub_date_end))
        elif type == "composition" or type == "comp":
            if self.composition_date_start is None:
                return None
            else:
                return mean_average((self.composition_date_start,
                                     self.composition_date_end))
        elif type == "actual":
            if self.date("pub") is not None and self.date("comp") is not None:
                if self.date("pub") > self.authorObject().biodate("death"):
                    return self.date("comp")
                elif self.date("pub") > self.date("comp") + 10:
                    return self.date("comp")
                else:
                    return self.date("pub")
            elif (self.date("pub") is not None and
                  self.date("pub") <= self.authorObject().biodate("death")):
                return self.date("pub")
            elif self.date("comp") is not None:
                return self.date("comp")
            else:
                return None
        else:
            return self.date(type="actual") or\
                   self.authorObject().average_date() or\
                   self.authorObject().working_dates_midpoint()


class Author(CatalogItem):

    def __init__(self, row, column_headers):
        CatalogItem.__init__(self, row, column_headers)
        self.dbpedia_id = self.id

    def unreverse_name(self):
        try:
            src = self.gutenberg_name
        except AttributeError:
            try:
                src = self.gutenbergname
            except AttributeError:
                src = ""
        m = re.search(r"^(.*), \d.*$", src)
        if m is not None:
            unrev = m.group(1)
        else:
            unrev = src
        m = re.search(r"^(.*) \(.*\)$", unrev)
        if m is not None:
            unrev = m.group(1)
        m = re.search(r"^(.*), (.*), (.*)$", unrev)
        if m is not None:
            unrev = m.group(2) + " " + m.group(1)
        else:
            m = re.search(r"^(.*), (.*?)$", unrev)
            if m is not None:
                unrev = m.group(2) + " " + m.group(1)
        return unrev

    def surname(self):
        return re.sub(r", .*$", "", self.gutenberg_name)

    def biodate(self, type):
        type = type.lower().strip()
        date_string = None
        if type and type[0] == "b":
            date_string = self.birthdate
        else:
            date_string = self.deathdate
        if date_string is not None:
            return int(date_string[0:4])
        else:
            return None

    def biodates(self):
        return (self.biodate("b"), self.biodate("d"))

    def age(self):
        if self.biodate("b") is not None and self.biodate("d") is not None:
            return self.biodate("d") - self.biodate("b")
        else:
            return None

    def age_in(self, year):
        if self.biodate("b") is not None:
            return self.biodate("d") - year
        else:
            return None

    def working_dates(self):
        d1, d2 = self.biodates()
        if d1 is None or d2 is None:
            return (None, None)
        else:
            lifespan = d2 - d1
            if lifespan > 60:
                return (d1 + 30, d2)
            elif lifespan > 50:
                return (d1 + 25, d2)
            elif lifespan > 30:
                return (d1 +20, d2)
            else:
                return (d1, d2)

    def working_dates_midpoint(self):
        return mean_average(self.working_dates())

    def titles(self):
        try:
            return self.title_objects
        except AttributeError:
            self.title_objects = [t for t in TitleSet().titles() if\
                                  t.author == self.gutenberg_name]
            return self.title_objects

    def num_titles(self):
        return len(self.titles())

    def average_date(self):
        dates = [t.date("actual") for t in self.titles()
                 if t.date("actual") is not None]
        if dates:
            return mean_average(dates)
        else:
            return mean_average(self.working_dates())

def mean_average(dates):
    if dates:
        av = sum(dates) / float(len(dates))
        return int(av + 0.5)
    else:
        return 0