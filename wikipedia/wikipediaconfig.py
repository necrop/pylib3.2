"""
wikipediaconfig -- Configuration for Wikipedia dumps and related data
"""

import os

#======================================================
# Base directories
#======================================================

BASE_DIR = '/home/james/j/projects/wikipedia'
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESOURCES_DIR = os.path.join(BASE_DIR, 'resources')

#======================================================
# Dumps
#======================================================

DUMP_DIR = os.path.join(DATA_DIR, 'dumps')
CURRENT_DUMP = os.path.join(DUMP_DIR, 'enwiki-20140614-pages-articles.xml')
DUMP_SEGMENTED_DIR = os.path.join(DATA_DIR, 'segmented')
TRIAGE_DIR = os.path.join(DATA_DIR, 'triaged')

UNCLASSIFIED_TARGET = 'zzother'
FILTERED_DIR = os.path.join(TRIAGE_DIR, UNCLASSIFIED_TARGET)
LEXICAL_DIR = os.path.join(DATA_DIR, 'lexical')
TAXONOMY_DIR = os.path.join(RESOURCES_DIR, 'topictaxonomy')

FILESIZE_LINES = 100000  # Num. lines per output file (approx)
FILESIZE_CHARS = 7000000  # Num. wikicode characters per output file (approx)

COUNTRIES_FILE = os.path.join(RESOURCES_DIR, 'countries_and_states.txt')

# Wikimedia namespaces (prefix + colon in Wikipedia page titles)
NAMESPACES = {'user', 'wikipedia', 'file', 'mediawiki', 'template',
              'help', 'category', 'portal', 'book', 'draft',
              'education program', 'timedtext', 'module',
              'special', 'media'}

# Disambiguation articles
DISAMBIGUATION_TEMPLATES = (
    '[a-z-]+ disambiguation', 'disambiguation', 'disambiguation cleanup',
    'disambig', 'dab', 'disamb', 'hndis', 'geodis', 'numberdis',
    'letter-numbercombdisambig', 'hndis-cleanup', 'geodis-cleanup',
    'schooldis', 'roaddis', 'callsigndis', 'mathdab')

# Set index articles
SIA_TEMPLATES = ('sia', 'set index article', 'mountainindex',
                 'shipindex', 'sportindex', 'surname', 'given name',
                 '[a-z]+ index', '[a-z]+index', 'molformdisambig',
                 'molecular formula disambiguation')


INFOBOXES = {'infobox', 'geobox', 'starbox', 'galaxybox', 'planetbox',
             'chembox', 'taxobox', 'speciesbox', 'subspeciesbox', 'drugbox',
             'sccinfobox', 'superherobox', 'warbox'}


MAIN_ARTICLE_END = {'references', 'footnotes', 'see also', 'external links',
                    'further reading'}