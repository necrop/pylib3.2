#-------------------------------------------------------------------------------
# Name: FrequencyDistribution
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

from __future__ import division
import os
import datetime
import codecs

import nltk


class FrequencyDistribution(object):

    def __init__(self):
        self.files = []
        self.wordcount = 0
        self.textcount = 0
        self.fd = {"tokens": nltk.FreqDist(),
                   "texts": nltk.FreqDist()}
        self.header_lines = []

    def add_file(self, filepath):
        fdata = FileData(filepath)
        self.add_data(freqDist=fdata.freqdist(type="tokens"),
                      textDist=fdata.freqdist(type="texts"),
                      wordcount=fdata.wordcount,
                      textcount=fdata.textcount)
        self.files.append(filepath)

    def add_data(self, freqDist=None, textDist=None, wordcount=None,
                 textcount=None):
        if wordcount is not None:
            self.wordcount += wordcount
        if textcount is not None:
            self.textcount += textcount
        if freqDist is not None:
            for token, i in freqDist.items():
                self.fd["tokens"].inc(token, count=i)
        if textDist is not None:
            for token, i in textDist.items():
                self.fd["texts"].inc(token, count=i)

    def set_header(self, header_lines):
        self.header_lines = [l.strip() for l in header_lines]

    def header(self):
        head = "###############################\n#\n"
        for l in self.header_lines:
            head += "# " + l + "\n"
        head += "#\n# Compiled %s\n" % (datetime.datetime.now().ctime(),)
        head += "#\n###############################\n"
        return head

    def write(self, file=None, overwrite=None, minFrequency=None,
              minLength=None):
        if minFrequency is None or not minFrequency:
            min_freq = 1
        else:
            min_freq = minFrequency
        if overwrite is None or not overwrite:
            overwrite = False
        else:
            overwrite = True
        if minLength is None or not minLength:
            min_length = 3
        else:
            min_length = int(minLength)
        if not overwrite and os.path.isfile(file):
            return False
        else:
            millions = float(self.wordcount) / 1000000
            fo = codecs.open(file, "w", encoding="utf-8")
            fo.write(self.header())
            fo.write("WORDCOUNT=%d\n" % (self.wordcount,))
            fo.write("TEXTCOUNT=%d\n" % (self.textcount,))
            fo.write("RANK\tTOKEN\tCOUNT\tFPM\tTEXTS\n")
            for i, token in enumerate(self.fd["tokens"].keys()):
                if ((self.fd["tokens"][token] >= min_freq) and
                    len(token) >= min_length):
                    fpm = float(self.fd["tokens"][token])/millions
                    fpm = "%s" % float("%.2g" % fpm)
                    if token in self.fd["texts"]:
                        texts = self.fd["texts"][token]
                    else:
                        texts = 1
                    fo.write("%d\t%s\t%d\t%s\t%d\n" % (i + 1, token,
                             self.fd["tokens"][token], fpm, texts))
            fo.close()
            return True


class FileData(object):

    def __init__(self, filepath):
        self.filepath = filepath
        self.load_file()

    def load_file(self):
        if os.path.isfile(self.filepath):
            f = codecs.open(self.filepath, "r", encoding="utf-8")
            lines = [l.strip() for l in f.readlines()]
            f.close()
        else:
            lines = []

        self.tokens = []
        self.header = []
        self.wordcount = 1
        self.textcount = 1
        for l in lines:
            row = self.parse_line(l)
            if row is not None:
                self.tokens.append(row)
            else:
                if l and l[0] == "#":
                    while l and l[0] == "#":
                        l = l[1:]
                    l = l.strip()
                    if l:
                        self.header.append(l)
                elif "WORDCOUNT=" in l:
                    self.wordcount = int(l.split("=")[1])
                elif "TEXTCOUNT=" in l:
                    self.textcount = int(l.split("=")[1])

    def parse_line(self, l):
        parts = l.split("\t")
        if len(parts) > 3 and parts[0] != "RANK":
            rank, token, count, fpm = parts[0:4]
            if len(parts) > 4:
                texts = parts[4]
            else:
                texts = 1
            return (token, int(count), float(fpm), int(texts), int(rank))
        else:
            return None

    def freqdist(self, type=None):
        if type != "tokens" and type != "texts":
            return nltk.FreqDist()
        else:
            try:
                return self.fd[type]
            except AttributeError:
                self.fd = {"tokens": nltk.FreqDist(),
                           "texts": nltk.FreqDist()}
                for t in self.tokens:
                    self.fd["tokens"].inc(t[0], count=t[1])
                    self.fd["texts"].inc(t[0], count=t[3])
                return self.fd[type]
