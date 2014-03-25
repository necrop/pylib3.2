#-------------------------------------------------------------------------------
# Name: SmartTokenizer
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import re
import os
import codecs

import nltk

from regexcompiler import ReplacementListCompiler

cleaner = ReplacementListCompiler((
    (r"_", r" "),
    (r"<[a-z]>", r" "),
    (r"<\/[a-z]>", r" "),
    (r"(--+)", r" \1 "),
    (r"  +", r" "),))

upcased = {}
force_downcase = {}

upcased_rx = re.compile(r"^[A-Z][a-z]+(|-[a-z]+)$")
downcased_rx = re.compile(r"^[a-z]+(|-[a-z]+)$")
upcase_finder = re.compile(r"( [a-z]+|[,;]) ([A-Z][a-z]+)([,;:]? |\.$)")


class SmartTokenizer(object):
    upcase_cache = nltk.FreqDist()

    def __init__(self):
        if not upcased:
            load_upcase_words()

    def tokenize(self, sentence):
        self.current_sentence = sentence
        tokens = nltk.word_tokenize(cleaner.edit(sentence))
        tokens = [clean_token(t) for t in tokens]
        if len(tokens) > 2:
            if (is_upcased_word(tokens[0]) and
                (is_downcased_word(tokens[1]) or tokens[0] in force_downcase)):
                tokens[0] = self.revaluate_case(tokens[0])
            elif (is_opening_punctuation(tokens[0]) and
                  is_upcased_word(tokens[1]) and
                  (is_downcased_word(tokens[2]) or tokens[1] in force_downcase)):
                tokens[1] = self.revaluate_case(tokens[1])
        return tokens

    def revaluate_case(self, token):
        if token in force_downcase:
            return token[0].lower() + token[1:]
        elif (token in upcased or
            (token in SmartTokenizer.upcase_cache and
             SmartTokenizer.upcase_cache[token] > 2)):
            return token
        else:
            return token[0].lower() + token[1:]

    def clear_cache(self):
        SmartTokenizer.upcase_cache.clear()

    def update_cache(self, sentence):
        matches = upcase_finder.findall(sentence)
        for m in matches:
            SmartTokenizer.upcase_cache.inc(m[1])




def is_upcased_word(w):
    if upcased_rx.search(w):
        return True
    elif downcased_rx.search(w):
        return False
    else:
        return False

def is_downcased_word(w):
    if downcased_rx.search(w):
        return True
    elif upcased_rx.search(w):
        return False
    elif w == "," or w == "I":
        return True
    else:
        return False

def is_opening_punctuation(w):
    for c in ("-", "--", "\"", "\'", "\`", "(", u"\x60", u"\u2018", u"\u201c"):
        if w == c:
            return True
    return False

def clean_token(t):
    if len(t) > 2 and t[-1] == ",":
        t = t.rstrip(",")
    if len(t) > 2 and t[0] == "\'":
        t = t[1:]
    return t

def load_upcase_words():
    global upcased
    global force_downcase
    data_dir = os.path.join(os.path.dirname(__file__), "data/tokenization/")

    for n in ("titles", "names", "places", "adjectives", "plurals"):
        fh = codecs.open(os.path.join(data_dir, n + ".txt"), "r",
                         encoding="ascii")
        for l in fh.readlines():
            upcased[l.strip()] = 1
        fh.close

    fh = codecs.open(os.path.join(data_dir, "downcase.txt"), "r",
                     encoding="ascii")
    for l in fh.readlines():
        force_downcase[l.strip()] = 1
    fh.close
