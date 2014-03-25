"""
thesaurusdbconfig -- settings for functions relating to the
    thesaurus database

@author: James McCracken
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_URL = 'postgresql://james:shapo1PSQL@localhost/htoed'  #?charset=utf8'
ENGINE = create_engine(DB_URL, client_encoding='utf8')
SESSION = sessionmaker(bind=ENGINE)()

WORDCLASS_TRANSLATIONS = {'noun': 'NN', 'adjective': 'JJ', 'adverb': 'RB',
                          'verb': 'VB', 'verb (transitive)': 'VB',
                          'verb (intransitive)': 'VB', 'verb (reflexive)': 'VB',
                          'phrase': 'PHRASE', 'preposition': 'IN',
                          'conjunction': 'CC', 'interjection': 'UH'}

# Stopwords used when tokenizing thesaurus labels
STOPWORDS = set(('a', 'an', 'the', 'of', 'for', 'to', 'and', 'or', 'in',
                 'of', 'relating', 'pertaining', 'characteristic', 'with',
                 'this', 'that', 'by', 'from', 'at', 'one', 'who', 'as',
                 'regards', 'regarding', 'belonging'))
