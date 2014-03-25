#-------------------------------------------------------------------------------
# Name: DbpediaLookup
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import urllib2
import random

from lxml import etree

url_stub = "http://lookup.dbpedia.org/api/search.asmx/KeywordSearch?"


class DbpediaLookup(object):
    CACHE_MAX = 100
    cache = {}

    def __init__(self, maxHits=None, cacheSize=None):
        self.url_stub = url_stub
        if maxHits is not None and isinstance(maxHits, int):
            self.max_hits = maxHits
        else:
            self.max_hits = None
        if cacheSize is not None and isinstance(cacheSize, int):
            DbpediaLookup.cache_max = cacheSize

    def find(self, queryString=None, queryClass=None, maxHits=None):
        sig = str(queryString) + "-" + str(queryClass) + "-" + str(maxHits)
        if not sig in DbpediaLookup.cache:
            results = []
            for round in (1, 2):
                if round == 2 and "(" in queryString:
                    q = re.sub(r" \([^()]+\)$", "", queryString)
                else:
                    q = queryString
                self.uri = self.url_stub + "QueryString=" + urllib2.quote(q)
                if queryClass is not None:
                    self.uri += "&QueryClass=" + urllib2.quote(queryClass)
                if maxHits is not None and isinstance(maxHits, int):
                    self.uri += "&MaxHits=" + str(maxHits)
                elif self.max_hits is not None:
                    self.uri += "&MaxHits=" + str(self.max_hits)
                xml = self.get_response()
                if xml is not None:
                    results = self.parse_xml(xml)
                if results:
                    break
            self.trim_cache()
            DbpediaLookup.cache[sig] = results
        return DbpediaLookup.cache[sig]

    def get_response(self):
        req = urllib2.Request(self.uri)
        response = None
        for i in (1, 2, 3):
            try:
                response = urllib2.urlopen(req)
            except urllib2.HTTPError:
                break
            except urllib2.URLError:
                time.sleep(2)
            if response is not None:
                break
        if response:
            return response.read()
        else:
            return None

    def parse_xml(self, xml):
        xml = xml.replace(' xmlns:', ' xmlnamespace')
        xml = xml.replace(' xmlns=', ' xmlnamespace=')
        root = etree.fromstring(xml)
        return [Result(r) for r in root.findall("Result")]

    def trim_cache(self):
        while self.cache_size() >= DbpediaLookup.cache_max:
            key = random.choice(DbpediaLookup.cache.keys())
            del DbpediaLookup.cache[key]

    def cache_size(self):
        return len(DbpediaLookup.cache)

    def clear_cache(self):
        DbpediaLookup.cache = {}


class Result(object):

    def __init__(self, node):
        self.label = node.findtext("Label")
        self.uri = node.findtext("URI")
        self.resource = urllib2.unquote(self.uri.replace("http://dbpedia.org/resource/", ""))
        self.description = node.findtext("Description")
        self.refcount = node.findtext("Refcount")
        if self.refcount is not None:
            self.refcount = int(self.refcount)
        else:
            self.refcount = 0

        self.classes = [c.text for c in node.findall("Classes/Class/Label")
                        if c.text != "owl#Thing"]
        self.categories = [c.text for c in
                           node.findall("Categories/Category/Label")]

    def has_class(self, class_label):
        for c in self.classes:
            if c.lower() == class_label.lower():
                return True
        return False

    def has_category(self, cat_label):
        for c in self.categories:
            if c.lower() == cat_label.lower():
                return True
        return False

    def category_contains(self, cat_label):
        count = 0
        for c in self.categories:
            if cat_label.lower() in c.lower():
                count += 1
        return count


if __name__ == "__main__":

    j = DbpediaLookup(maxHits=10)
    for label in ("Blessed Virgin Mary (Roman Catholic)",):
        #"Blake", "William Blake"):
        #, "aids", "Oxford", "Paris", "Middlemarch", "Great Expectations", "great expectations",
        #"Germany", "London", "Dublin", "Bristol",
        #"Portugal", "Lisbon", "Surrey", "Germany", "Scotland", "Cassius Clay"):
        z = j.find(label)
        print label
        for result in z:
            print repr(result.label), str(result.refcount)
            print "\t" + result.uri
            print "\t" + result.resource
            for c in result.classes:
                print "\t" + c
            for c in result.categories:
                print "\t\t" + repr(c)
        print "\n\n"

