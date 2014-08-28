"""
lexconfig -- Configuration for lexical functions

@author: James McCracken
"""

import os

#======================================================
# Base directories
#======================================================

LEX_DIR = '/home/james/j/work/lex'
OED_DIR = os.path.join(LEX_DIR, 'oed')
ODO_DIR = os.path.join(LEX_DIR, 'odo')
GEL_DIR = os.path.join(LEX_DIR, 'gel')
GEL2_DIR = os.path.join(LEX_DIR, 'gel2')
NGRAMS_DIR = os.path.join(LEX_DIR, 'googleNgrams')
HTOED_DIR = os.path.join(LEX_DIR, 'oed/oedlatest/oedlatest_thesaurus')


#======================================================
# OED-related stuff
#======================================================

OEDLATEST_TEXT_DIR = os.path.join(OED_DIR, 'oedlatest/text20140228')
OEDPUB_TEXT_DIR = os.path.join(OED_DIR, 'oedpub/oed_publication_text')

OED_RESOURCES_DIR = os.path.join(OED_DIR, 'resources')
OED_VITALSTATS_DIR = os.path.join(OED_RESOURCES_DIR, 'vital_statistics')
OED_MAIN_SENSES_DIR = os.path.join(OED_RESOURCES_DIR, 'main_senses')
OED_LINKS_DIR = os.path.join(OED_RESOURCES_DIR, 'link_tables')
OED_VARIANTS_DIR = os.path.join(OED_RESOURCES_DIR, 'variants')
OED_FREQUENCY_DIR = os.path.join(OED_RESOURCES_DIR, 'frequency_tables')
OED_LANGUAGE_TAXONOMY = os.path.join(OED_RESOURCES_DIR, 'etymology', 'languages.xml')
OED_PROJECTS_DIR = os.path.join(OED_DIR, 'projects')


#======================================================
# ODO-related stuff
#======================================================

ODE_TEXT_DIR = os.path.join(ODO_DIR, 'text/ode')
NOAD_TEXT_DIR = os.path.join(ODO_DIR, 'text/noad')
ODE_DISTILLED = os.path.join(ODO_DIR, 'distilled/ode_distilled')
NOAD_DISTILLED = os.path.join(ODO_DIR, 'distilled/noad_distilled')
ODO_LINKS_DIR = os.path.join(ODO_DIR, 'links')
MORPHOLOGY_DIR = os.path.join(ODO_DIR, 'morphology')


#======================================================
# HTOED-related stuff
#======================================================

HTOED_CONTENT_DIR = os.path.join(HTOED_DIR, 'content')
HTOED_TAXONOMY_DIR = os.path.join(HTOED_DIR, 'taxonomies')


#======================================================
# GEL-related stuff
#======================================================

GEL_DATA_DIR = os.path.join(GEL_DIR, 'globalEnglishLexicon/data')


#======================================================
# Google Ngrams-related stuff
#======================================================

NGRAMS_TABLES_DIR = os.path.join(NGRAMS_DIR, 'tables', 'sorted')
