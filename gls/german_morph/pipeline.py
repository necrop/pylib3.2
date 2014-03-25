#-------------------------------------------------------------------------------
# Name: pipeline
# Purpose: Insert missing Oxford inflections into German OxMorph data
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import os
import re

# 'processes' Controls which functions will be run; comment out
#   any which are not to be run.
# Processes should be run in this order!
processes = (
    #'split_source',
    #'split_xelda',
    #'index_xelda',
    #'index_oxford_forms',
    #'fix_plurals',
    #'insert_oxford_forms',
    #'reduce_to_basic',
    'concatenate',
)


# Filepaths
parent_dir = 'C:/j/work/gls/german_morphology/'
source_file = os.path.join(parent_dir, 'Oxford_GLS_GEDC_DUDE_DDDSI_Inflected-Forms-Full_1.1.xml')
xelda_file = os.path.join(parent_dir, 'German.hw-list-enriched-V4.xml')
oxford_forms_dir = os.path.join(parent_dir, 'OxfordForms')
source_split_dir = os.path.join(parent_dir, 'tmp', 'source')
pluralfixed_dir = os.path.join(parent_dir, 'tmp', 'plural_fixed')
omissionsfixed_dir = os.path.join(parent_dir, 'tmp', 'omissions_fixed')
xelda_split_dir = os.path.join(parent_dir, 'tmp', 'xelda')
basic_dir = os.path.join(parent_dir, 'tmp', 'basic')



def split_source():
    from gls.german_morph.lib.splitter import SourceSplitter
    splitter = SourceSplitter(source_file, source_split_dir, size=1000)
    splitter.clear_output()
    splitter.split()

def split_xelda():
    from gls.german_morph.lib.splitter import XeldaSplitter
    splitter = XeldaSplitter(xelda_file, xelda_split_dir, size=20000)
    splitter.clear_output()
    splitter.split()

def index_xelda():
    from gls.german_morph.lib.splitter import xelda_indexer
    xelda_indexer(xelda_split_dir)

def index_oxford_forms():
    from gls.german_morph.lib.oxfordformsmanager import OxfordFormsManager
    om = OxfordFormsManager(oxford_forms_dir)
    om.index_files()

def fix_plurals():
    from gls.german_morph.lib.pluralfixer import PluralFixer
    pf = PluralFixer(source_split_dir, pluralfixed_dir, xelda_split_dir)
    pf.process()

def insert_oxford_forms():
    from gls.german_morph.lib.missingforms import MissingForms
    mf = MissingForms(pluralfixed_dir, omissionsfixed_dir, oxford_forms_dir)
    mf.process()

def reduce_to_basic():
    from gls.german_morph.lib.reducer import reducer
    reducer(omissionsfixed_dir, basic_dir)

def concatenate():
    from gls.german_morph.lib.concatenator import Concatenator
    out_file1 = os.path.join(parent_dir, 'germanOxmorphCorrected', 'Oxford_GLS_GEDC_DUDE_DDDSI_Inflected-Forms-Full_1.2.xml')
    c1 = Concatenator(inDir=omissionsfixed_dir, outFile=out_file1, mode='full')
    c1.concatenate()

    out_file2 = os.path.join(parent_dir, 'germanOxmorphCorrected', 'Oxford_GLS_GEDC_DUDE_DDDSI_Inflected-Forms-Basic_1.2.xml')
    c2 = Concatenator(inDir=basic_dir, outFile=out_file2, mode='basic')
    c2.concatenate()


if __name__ == '__main__':
    for function_name in processes:
        print '=' * 30
        print 'Running %s...' % (function_name,)
        print '=' * 30
        fn = globals()[function_name]
        fn()
