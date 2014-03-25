#-------------------------------------------------------------------------------
# Name: GEL2config
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import re
import ConfigParser

files = (
    "C:/j/work/dictionaries/gel2/config.ini",
    "C:/j/work/dictionaries/gel2/pipeline.ini",
)
true_rx = re.compile(r"^(yes|on|true|1)$", re.I)
false_rx = re.compile(r"^(no|off|false|0)$", re.I)

class GEL2config(object):
    parser = ConfigParser.ConfigParser()
    pipeline = []
    files_read = False

    def __init__(self):
        self.read_file()

    def read_file(self):
        if not GEL2config.files_read:
            GEL2config.parser.read(files)
            fh = open(files[1], "r")
            GEL2config.pipeline = [l.split(":")[0].strip()\
                                  for l in fh.readlines() if ":" in l]
            GEL2config.files_read = True

    def get(self, section, option):
        value = GEL2config.parser.get(section, option)
        if value is None:
            return None
        elif re.search(r"^-?[0-9]+$", value):
            return int(value)
        elif true_rx.search(value):
            return True
        elif false_rx.search(value):
            return False
        else:
            return value

    def items(self, section):
        return GEL2config.parser.items(section)

    def pipeline(self):
        return GEL2config.pipeline
