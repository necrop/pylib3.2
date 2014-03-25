#-------------------------------------------------------------------------------
# Name: gutenbergText
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

from __future__ import division
import os
import re
import datetime
import codecs

import nltk

from .decrufter import Decrufter
from .genredetector import GenreDetector
from .chunker import Chunker, ChunkSet
from nlp.smarttokenizer import SmartTokenizer

default_tagger = nltk.data.load(nltk.tag._POS_TAGGER)
model = {"(": ":", ")": ":", "yet": "RB", "\"": ":"}
tagger = nltk.tag.UnigramTagger(model=model, backoff=default_tagger)
tokenizer = SmartTokenizer()

class GutenbergText(object):

    def __init__(self, path):
        self.path = path
        self.tokenizer_primed = False

    def lines(self):
        try:
            return self.all_lines
        except AttributeError:
            f = open(self.path, "r")
            self.all_lines = [line_decoder(l) for l in f.readlines()]
            f.close()
            return self.all_lines

    def set_lines(self, lst):
        self.all_lines = lst

    def set_catalog_entry(self, c):
        self.cat = c

    @property
    def catalog(self):
        try:
            return self.cat
        except AttributeError:
            return None

    def decruft_lines(self):
        dc = Decrufter()
        dc.load_lines(self.lines())
        return dc.decruft()

    def genre(self):
        gd = GenreDetector(self.lines())
        return gd.detect_genre()

    def paragraphs(self):
        try:
            return self.paras
        except AttributeError:
            paras = []
            buffer = []
            for l in self.lines():
                if not l:
                    para = " ".join(buffer).strip()
                    if para:
                        paras.append(para)
                    buffer = []
                elif l.strip(" -*~"):
                    buffer.append(l)
            self.paras = [Paragraph(text=p, id=i) for i, p in\
                          enumerate(paras)]
            return self.paras

    def num_characters(self):
        try:
            return self.numchars
        except AttributeError:
            self.numchars = sum([len(p.text) for p in self.paragraphs()])
            return self.numchars

    def num_tokens(self):
        try:
            return self.numtokens
        except AttributeError:
            self.numtokens = sum([len(p.tokens()) for p in self.paragraphs()])
            return self.numtokens

    def chunk_freq_dist(self):
        cs = ChunkSet()
        self.prime_tokenizer()
        for p in self.paragraphs():
            cs.add_chunks(p.chunks())
        return cs.freq_dist()

    def prime_tokenizer(self):
        if not self.tokenizer_primed:
            tokenizer.clear_cache()
            for p in self.paragraphs():
                for s in p.sentences():
                    tokenizer.update_cache(s.text)
            self.tokenizer_primed = True


class Paragraph(object):

    def __init__(self, text=None, id=None, parentData=None):
        self.text = text
        self.id = id
        self.parent_data = parentData

    def length(self):
        return len(self.text)

    def sentences(self):
        try:
            return self.sents
        except AttributeError:
            self.sents = [Sentence(s) for s in nltk.sent_tokenize(self.text)]
            return self.sents

    def tokens(self):
        arr = []
        for s in self.sentences():
            arr.extend(s.tokens())
        return arr

    def tagged_display(self):
        return "<p>" + "".join([s.tagged_display() for s in\
                                self.sentences()]) + "</p>"

    def chunked_display(self):
        return "<p>" + "".join([s.chunker().display() for s in\
                                self.sentences()]) + "</p>"

    def chunks(self):
        cs = ChunkSet()
        for s in self.sentences():
            cs.add_chunks(s.chunks())
        return cs.chunks


class Sentence(object):

    def __init__(self, text):
        self.text = text

    def tokens(self):
        try:
            return self.tkns
        except AttributeError:
            self.tkns = tokenizer.tokenize(self.text)
            return self.tkns

    def tagged_tokens(self):
        try:
            return self.tagged_tkns
        except AttributeError:
            self.tagged_tkns = tagger.tag(self.tokens())
            return self.tagged_tkns

    def tagged_display(self):
        return "<s>" + " ".join(["%s/%s" % (xml_safe(t[0]), t[1]) for t in\
               self.tagged_tokens()]) + "</s>"

    def chunker(self):
        try:
            return self.chunk_obj
        except AttributeError:
            self.chunk_obj = Chunker(self.tagged_tokens())
            return self.chunk_obj

    def chunks(self):
        return self.chunker().chunks()


def line_decoder(l):
    l = l.strip()
    if type(l) is str:
        try:
            l = l.decode("ascii")
        except UnicodeDecodeError:
            try:
                l = l.decode("iso-8859-1")
            except UnicodeDecodeError:
                try:
                    l = l.decode("utf-8")
                except UnicodeDecodeError:
                    l = l.decode("ascii", "replace")
    return l

def xml_safe(string):
    for tup in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;")):
        string = string.replace(tup[0], tup[1])
    return string
