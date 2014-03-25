#-------------------------------------------------------------------------------
# Name: named_entities
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import nltk, re, pprint


def chapterize(file):
    f = open(file, "r")
    lines = f.readlines()
    f.close()

    paras = []
    buffer = []
    for l in lines:
        l = l.strip()
        if not l:
            para = " ".join(buffer).strip()
            if para:
                paras.append(para)
            buffer = []
        elif l.strip(" -*~"):
            buffer.append(l)

    paras = decruft(paras)
    return paras

def decruft(paras):
    startparas = []
    endparas = []
    for i, p in enumerate(paras):
        if "project gutenberg" in p.lower():
            if i < 100:
                startparas.append(i)
            elif i > len(paras) - 100:
                endparas.append(i)
    if startparas:
        start_para = max(startparas) + 1
    else:
        start_para = 0
    if endparas:
        end_para = min(endparas)
    else:
        end_para = len(paras) - 1

    return paras[start_para:end_para]



def ie_preprocess(document):
    sentences = nltk.sent_tokenize(document)
    sentences = [nltk.word_tokenize(sent) for sent in sentences]
    sentences = [nltk.pos_tag(sent) for sent in sentences]

    for sent in sentences:
        print nltk.ne_chunk(sent, binary=True)

