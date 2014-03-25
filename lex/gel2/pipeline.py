#-------------------------------------------------------------------------------
# Name: Pipeline
# Purpose: GEL2 process dispatcher
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import shutil
import os

from lex.gel2.gel2config import GEL2config

config = GEL2config()


def dispatch():
    for function_name in config.pipeline:
        if config.get("processes", function_name):
            print "=" * 30
            print "Running '%s'..." % (function_name,)
            print "=" * 30
            fn = globals()[function_name]
            fn()


def compileTopicData():
    from lex.gel2.processors.topics import OdoTopicLister, OedTopicLister
    t = OdoTopicLister(inFile=config.get("paths", "ode_full_text"),
        outFile=os.path.join(config.get("paths", "topics_dir"), "ode_topics.csv"))
    t.extract_topics()

    t = OdoTopicLister(inFile=config.get("paths", "noad_full_text"),
        outFile=os.path.join(config.get("paths", "topics_dir"), "noad_topics.csv"))
    t.extract_topics()

    t = OedTopicLister(inDir=config.get("paths", "oed_full_text"),
        outFile=os.path.join(config.get("paths", "topics_dir"), "oed_topics.csv"))
    t.extract_topics()


def compileSoundfiles():
    from lex.gel2.processors.soundfiles import SoundfileLister
    t = SoundfileLister(
        name="ode",
        inFile=config.get("paths", "ode_full_text"),
        outFile=os.path.join(config.get("paths", "soundfiles_dir"), "ode.csv"),
    )
    t.extract_soundfiles()

    t = SoundfileLister(
        name="noad",
        inFile=config.get("paths", "noad_full_text"),
        outFile=os.path.join(config.get("paths", "soundfiles_dir"), "noad.csv"),
    )
    t.extract_soundfiles()



def buildFixtures():
    from lex.gel2.processors.fixturebuilder import FixtureBuilder
    fb = FixtureBuilder(gel1Dir=config.get("paths", "gel1_data_dir"),
                        outDir=config.get("paths", "fixtures_dir"),
                        topics=config.get("paths", "topics_dir"),
                        soundfiles=config.get("paths", "soundfiles_dir"),)
    fb.make_fixtures()
    #fb.load_topics()



if __name__ == "__main__":
    dispatch()
