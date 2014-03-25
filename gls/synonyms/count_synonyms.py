#-------------------------------------------------------------------------------
# Name: count_synonyms
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import os
import csv

from lxml import etree

dir = "C:/j/work/gls/synonyms/dicts/"
outfile = "C:/j/work/gls/synonyms/synonym_counts.csv"
parser = etree.XMLParser(remove_blank_text=True)

languages = ("Chinese_Simplified", "Chinese_Traditional", "Dutch",
             "French", "German", "Italian", "Japanese", "Korean",
             "Norwegian", "Spanish")


def count_synonyms():
    results = {l: {"complete": {}, "c001": {}} for l in languages}

    for l in languages:
        subdir = os.path.join(dir, l)

        for type in ("complete", "c001"):
            if type == "complete":
                files = [os.path.join(subdir, f) for f in os.listdir(subdir)
                         if f.endswith(".xml") and not "_C001" in f]
            else:
                files = [os.path.join(subdir, f) for f in os.listdir(subdir)
                         if f.endswith(".xml") and "_C001" in f]

            entries = entries_with_synonyms = synonyms = 0
            for f in files:
                tree = etree.parse(f, parser)
                for e in tree.findall(".//e"):
                    entries += 1
                    syns = e.findall(".//syn")
                    if syns:
                        entries_with_synonyms += 1
                        synonyms += len(syns)

            results[l][type] = {
                "entries": entries,
                "entries_with_synonyms": entries_with_synonyms,
                "synonyms": synonyms
            }

    with (open(outfile, "wb")) as fh:
        csvw = csv.writer(fh)
        for type in ("complete", "c001"):
            for l in languages:
                row = [l]
                for r in ("entries", "entries_with_synonyms", "synonyms"):
                    row.append(results[l][type][r])
                csvw.writerow(row)



if __name__ == "__main__":
    count_synonyms()
