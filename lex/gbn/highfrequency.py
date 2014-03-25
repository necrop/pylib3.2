#-------------------------------------------------------------------------------
# Name: HighFrequency
# Purpose:
#
# Author: James McCracken
#
# Created: 12/01/2012
#-------------------------------------------------------------------------------

import re
import string
import os

from .ngram import Ngram

alphabet = list(string.ascii_lowercase)
cutoff = 1

class HighFrequency(object):
    """
    """

    def __init__(self,
                 dir=None,
                 out_file=None,
                 list_length=None,
                 range=None,
                 cutoff=None):
        if list_length is None:
            list_length = 10000
        if cutoff is None:
            cutoff = 1
        if range is None:
            range = "1970-2008"
        self.dir = dir
        self.out_file = out_file
        self.list_length = list_length
        self.range = range
        self.cutoff = cutoff

    def process(self):
        self.hilist = []
        for gram_num in (1, 2, 3):
            for letter in alphabet:
                print "Doing %d/%s (%d)" % (gram_num, letter, len(self.hilist))
                in_dir = os.path.join(self.dir, str(gram_num), letter)
                files = os.listdir(in_dir)
                for fname in files:
                    with open(os.path.join(in_dir, fname), "r") as f:
                        for line in f:
                            n = Ngram(line, gramCount=gram_num)
                            if (n.wordclass == "ALL" and
                                n.frequency(self.range) > self.cutoff):
                                self.hilist.append((n.lemma, n.frequency(self.range)))
        self.write()

    def write(self):
        self.hilist.sort(key=lambda n: n[1], reverse=True)
        f = open(self.out_file, "w")
        f.write("# " + self.range + "\n")
        f.write("# cutoff = " + str(self.cutoff) + " per million\n")
        for i, n in enumerate(self.hilist):
            f.write(n[0] + "\t" + str(n[1]) + "\n")
            if i == self.list_length:
                break
        f.close()


class Delta(object):

    def __init__(self, f1, f2, out_dir):
        self.files = {"f1": f1, "f2": f2}
        self.out_dir = out_dir

    def load_files(self):
        self.data = {}
        self.min = {}
        for fname in self.files:
            self.data[fname] = {}
            with open(self.files[fname], "r") as f:
                for line in f:
                    parts = line.split("\t")
                    if len(parts) == 2:
                        self.data[fname][parts[0]] = float(parts[1])
                        self.min[fname] = float(parts[1])

    def compare(self):
        try:
            self.data
        except AttributeError:
            self.load_files()
        up = []
        down = []
        for lemma in self.data["f2"]:
            new_freq = self.data["f2"][lemma]
            if lemma in self.data["f1"]:
                old_freq = self.data["f1"][lemma]
            else:
                old_freq = self.min["f1"]
            if new_freq > old_freq:
                up.append((lemma, old_freq, new_freq, new_freq/old_freq))
            else:
                down.append((lemma, old_freq, new_freq, old_freq/new_freq))

        up.sort(key=lambda n: n[3], reverse=True)
        down.sort(key=lambda n: n[3], reverse=True)

        out_file1 = os.path.join(self.out_dir, "delta_increase.txt")
        with open(out_file1, "w") as j:
            for n in up:
                j.write("%s\t%f\t%f\t%f\n" % n)

        out_file2 = os.path.join(self.out_dir, "delta_decrease.txt")
        with open(out_file2, "w") as j:
            for n in down:
                j.write("%s\t%f\t%f\t%f\n" % n)
