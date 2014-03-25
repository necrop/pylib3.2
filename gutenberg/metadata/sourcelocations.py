#-------------------------------------------------------------------------------
# Name: SoureLocations
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import csv


class SourceLocations(object):

    def __init__(self, path):
        self.path = path
        self.parse()

    def parse(self):
        self.texts = {}
        reader = csv.reader(open(self.path, "rb"))
        for row in reader:
            id = int(row[0])
            loc = row[1]
            self.texts.setdefault(id, []).append(loc)

    def locations(self, id):
        id = int(id)
        if id in self.texts:
            return self.texts[id]
        else:
            return []

    def exists(self, id):
        if self.locations(id):
            return True
        else:
            return False
