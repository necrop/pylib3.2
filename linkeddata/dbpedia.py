#-------------------------------------------------------------------------------
# Name:  DBpedia
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import re
import time

from rdflib import Graph, URIRef
from SPARQLWrapper import SPARQLWrapper, JSON

sparql = SPARQLWrapper("http://dbpedia.org/sparql")
sparql_prefixes = """
    PREFIX resource: <http://dbpedia.org/resource/>
    PREFIX ontology: <http://dbpedia.org/ontology/>
    PREFIX property: <http://dbpedia.org/property/>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

dbpedia_base = "http://dbpedia.org/resource/"
predicate_base = "http://dbpedia.org/ontology/"


class DBpedia(object):

    def __init__(self):
        pass

    def load_graph(self, id, redirect=None):
        if redirect is None:
            redirect = False
        else:
            redirect = True
        g = self.__graph_loader(id)
        if redirect:
            redirect_uri = self.redirect(g)
            if redirect_uri is not None:
                g = self.__graph_loader(redirect_uri)
        return g

    def __graph_loader(self, id):
        g = Graph()
        if dbpedia_base in id:
            uri = id
        else:
            uri = dbpedia_base + id
        try:
            dbp_graph = g.parse(uri)
        except:
            # Wait in case dbpedia has returned a 500 etc.
            time.sleep(2)
            try:
                dbp_graph = g.parse(uri)
            except:
                dbp_graph = None
        if dbp_graph is not None:
            dbp_graph.uri = uri
            dbp_graph.resource_name = uri.replace("http://dbpedia.org/resource/", "")
            dbp_graph.label = self.label(dbp_graph)
        return dbp_graph

    def property_list(self, **kwargs):
        if "graph" in kwargs:
            graph = kwargs["graph"]
        else:
            graph = None
        if "predicate" in kwargs:
            predicate = kwargs["predicate"]
        else:
            predicate = None
        if "position" in kwargs:
            position = kwargs["position"]
            if position is not None:
                position = position.lower()
        else:
            position = None
        if "lang" in kwargs:
            language = kwargs["lang"]
        else:
            language = None

        if graph is not None and predicate is not None:
            if predicate == "type":
                predicate_uri = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
            elif predicate == "label":
                predicate_uri = "http://www.w3.org/2000/01/rdf-schema#label"
            elif not re.search(r"^http:", predicate):
                predicate_uri = predicate_base + predicate
            else:
                predicate_uri = predicate

            raw_pairs = graph.subject_objects(URIRef(predicate_uri))

            if language is not None:
                raw_pairs = [p for p in raw_pairs if
                             self.test_language(p, language)]

            pairs = []
            for p in raw_pairs:
                row = []
                for item in p:
                    if item.__class__.__name__ == "URIRef":
                        j = str(item)
                    elif item.__class__.__name__ == "Literal":
                        j = item.n3()
                    row.append(j)
                pairs.append(row)

            if pairs:
                if position == "subject":
                    return [p[0] for p in pairs if p[0] != graph.uri]
                elif position == "object":
                    return [p[1] for p in pairs if p[1] != graph.uri]
                else:
                    if p[1] == graph.uri:
                        return [p[0] for p in pairs]
                    else:
                        return [p[1] for p in pairs]
        return []

    def first_property(self, **kwargs):
        lst = self.property_list(**kwargs)
        if lst:
            return lst[0]
        return None

    def test_language(self, pair, language):
        match = True
        for item in pair:
            if item.__class__.__name__ == "Literal":
                try:
                    if item.language != language:
                        match = False
                except AttributeError:
                    pass
        return match

    def raw_triples(self, graph):
        if graph is not None:
            return graph.triples((None, None, None))
        else:
            return []

    def abstract(self, graph):
        string = self.first_property(graph=graph,
                                     predicate="abstract",
                                     position="object",
                                     lang="en")
        if string is not None:
            string = string.replace("@en", "")
            string = string.replace("\"", "")
        return string

    def label(self, graph):
        string = self.first_property(graph=graph,
                                     predicate="label",
                                     position="object",
                                     lang="en")
        if string is not None:
            string = string.replace("@en", "")
            string = string.replace("\"", "")
        return string

    def wikipedia(self, graph):
        return self.first_property(graph=graph,
                                  predicate="http://xmlns.com/foaf/0.1/primaryTopic",
                                  position="subject")

    def redirect(self, graph):
        return self.first_property(graph=graph,
                                   predicate="wikiPageRedirects",
                                   position="object")

    def types(self, graph, ontology=None):
        type_list = self.property_list(graph=graph,
                                       predicate="type",
                                       position="object")
        if ontology is not None and ontology:
            type_list = [t for t in type_list if\
                         "http://dbpedia.org/ontology/" in t]
        return type_list

    def disambiguations(self, graph):
        return self.property_list(graph=graph,
                                  predicate="wikiPageDisambiguates",
                                  position="object")

    def sparql_query(self, **kwargs):
        if "query" in kwargs:
            query = kwargs["query"]
        else:
            return []
        if "format" in kwargs:
            format = [j.strip() for j in kwargs["format"].split(",")]
        else:
            format = None

        sparql.setQuery(sparql_prefixes + "\n" + query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        if format is None:
            return results["results"]["bindings"]
        else:
            output = []
            seen = {}
            for res in results["results"]["bindings"]:
                row = []
                for f in format:
                    if f in res:
                        row.append(res[f]["value"])
                    else:
                        row.append(None)
                sig = result_signature(row)
                if not sig in seen:
                    output.append(row)
                    seen[sig] = 1
            return output



def result_signature(row):
    sig = ""
    for r in row:
        if r is None:
            sig = sig + "-NONE"
        else:
            sig = sig + "-" + r
    return sig



if __name__ == "__main__":
    id = "What_Is_Man%3F"
    dbp = DBpedia()
    g = dbp.load_graph(id)
    if g is not None:
        for triple in g:
            print repr(triple)

