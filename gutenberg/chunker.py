#-------------------------------------------------------------------------------
# Name: chunker
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

from __future__ import division
import re

import nltk

from stringsimplifier import StringSimplifier
from lex.inflections.singularizer import Singularizer

grammar = r"""
  NP: {<NNS?> <IN> <NN>+}
      {<NN>+ <NNS?>}
      {<JJ> <NNS?>}
      {<NNS?>}
  NEP: {<NNPS?> <IN> <NNPS?>+}
       {<NNPS?>+ <NNPS?>}
       {<JJ> <NNPS?>}
       {<NNPS?>}"""


roman_rx = re.compile(r"(^| )(iii?|iv|ix|vi+|xv|x[xivl][xiv]*|l[ivx][xiv]*)($| )")
dull_adjectives = set(["next", "own", "other", "several", "some", "same",
                       "any", "certain", "further", "such", "whole", "all",
                       "many", "few", "new", "good", "nice", "little", "large",
                       "great", "fine", "small", "difficult", "different",
                       "only", "last"])
kind_of = set(["kind", "sort", "type"])

cp = nltk.RegexpParser(grammar)
stemmer = Singularizer()
sentence_spacing_replacements = []


class Chunker(object):

    def __init__(self, tokens):
        self.tokens = tokens

    def chunked(self):
        try:
            return self.chunked_tkns
        except AttributeError:
            self.chunked_tkns = cp.parse(self.tokens)
            for t in self.chunked_tkns:
                if type(t) is not tuple:
                    t.normalized = normalize_chunk(t)
            return self.chunked_tkns

    def chunks(self):
        return [t for t in self.chunked() if type(t) is not tuple]

    def display(self):
        sent_array = []
        for t in self.chunked():
            if type(t) is tuple:
                sent_array.append(xml_safe(t[0]))
            else:
                tag = t.node.lower()
                unit = " ".join([xml_safe(token[0]) for token in t])
                sent_array.append("<%s>%s</%s>" % (tag, unit, tag))
        return "<s>" + join_tokens(sent_array) + "</s>"


class ChunkSet(object):

    def __init__(self):
        self.chunks = []

    def add_chunks(self, arr):
        self.chunks.extend(arr)

    def uniq(self):
        arr = []
        seen = {}
        for c in self.chunks():
            if not c.normalized in seen:
                arr.append(c)
                seen[c.normalized] = 1
        return arr

    def freq_dist(self):
        f = nltk.FreqDist()
        for chunk in self.chunks:
            if is_salient_chunk(chunk):
                f.inc(chunk.normalized)
            if len(chunk) > 1:
                for token in [t for t in chunk if "NN" in t[1] and is_salient_token(t)]:
                    f.inc(normalize(token[0], chunk.node))
        return f


def join_tokens(arr):
    string = " ".join(arr)
    if not sentence_spacing_replacements:
        compile_replacements()
    for k in sentence_spacing_replacements:
        string = string.replace(k[0], k[1])
    return string

def xml_safe(string):
    for tup in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;")):
        string = string.replace(tup[0], tup[1])
    return string

def normalize_chunk(chunk):
    return normalize(" ".join([w[0] for w in chunk]), chunk.node)

def normalize(token, node):
    norm = StringSimplifier(token).asciified
    norm = norm.replace("-", " ").lower()
    norm = norm.replace("  ", " ").lower()
    if norm and norm[0] == "\'":
        norm = norm[1:]
    if len(norm) > 4 and norm[0:4] == "the ":
        norm = norm[4:]
    if node != "NEP":
        norm = stemmer.singularize(norm)
    return norm.strip()

def compile_replacements():
    global sentence_spacing_replacements
    r = []
    for punct in ",:.;)!?":
        r.append((" " + punct, punct))
    for punct in "(":
        r.append((punct + " ", punct))
    for token in ("\'s", "n\'t", "\'d", "\'ve"):
        r.append((" " + token + " ", token + " "))
        r.append((" <vp>" + token, "<vp>" + token))
    for tup in (("<s>\" ", "<s>\""), (" \"</s>", "\"</s>")):
        r.append(tup)
    for word in ("said",
                 "exclaimed",
                 "remarked",
                 "replied",
                 "cried",
                 "repeated",
                 "whispered",
                 "muttered",
                 "murmured",
                 "faltered",
                 "shouted"):
        r.append((", \" <vp>" + word, ",\" <vp>" + word))
        r.append((", \" I <vp>" + word, ",\" I <vp>" + word))
        r.append((", \" he ", ",\" he " + word))
    for word in ("he", "she"):
        r.append((", \" " + word + " ", ",\" " + word + " "))
    sentence_spacing_replacements = r


def is_salient_chunk(chunk):
    first_word = chunk[0][0].lower()
    first_tag = chunk[0][1]
    if roman_rx.search(first_word):
        return False
    if first_tag == "JJ" and first_word in dull_adjectives:
        return False
    if (len(chunk) > 2 and
        chunk[1][0].lower() == "of" and
        first_word in kind_of):
        return False
    return True

def is_salient_token(token):
    word = token[0].lower()
    if roman_rx.search(word):
        return False
    if word in dull_adjectives:
        return False
    if word == "the" or word == "of" or word == "in":
        return False
    return True
