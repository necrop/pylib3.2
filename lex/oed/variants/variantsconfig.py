"""
config -- configuration for variants-related modules

@author: James McCracken
"""

BASECLASSES = set(('NN', 'VB', 'JJ', 'RB', 'IN', 'CC', 'UH', 'PP',
                   'PDT', 'WDT', 'WP', 'WRB', 'MD'))

 # Approximate number of variant form per file
CACHE_FILE_SIZE = 10000

# Boundary dates to use for an affix (since quotation dates in an
#  affix are not indicative).
AFFIX_DATES = (1200, 2050,)

DERIVATIVE_AFFIXES = set('ability|acean|aire|al|alism|alist|ality|ally|alty|amide|amine|ance|arch|archy|ation|cean|cide|cism|cracy|crat|dness|dom|ectomy|ed|edness|eer|eity|ence|er|ering|ery|ess|et|ette|fulness|genesis|hood|ianism|ic|ical|ication|icide|icism|icity|imide|ineness|iness|ing|ingness|iousness|isation|ish|ishness|ism|ist|itis|itude|ity|ization|ize|ized|izer|izing|lessness|let|liness|ling|lity|ly|ment|ness|nist|ocracy|olatry|ological|ologist|ology|ometry|opathy|ophilia|otomy|phil|phile|philia|phobia|phony|ship|ster|teer|tion|tism|tist'.split('|'))

# Variants will not be generated for the following, where they appear
#  in compounds (case-insensitive).
STOPWORDS_PATTERN = '^(a|an|of|and|the|to|for|by|with|in|on|at|be|as|that|de|du)$'

# Maximum number of variants that will be generated for a compound.
#  If the number of possible compounds is higher than this, the list will
#  be truncated, starting with the oldest (those with the earliest end date).
COMPOUNDS_CAP = 50

DATE_CONVERSIONS = {'OE': (900, 1149),
                    'eOE': (900, 1049),
                    'lOE': (1050, 1149),
                    'ME': (1150, 1499),
                    'eME': (1150, 1399),
                    'lME': (1400, 1499),
                    'pre-17': (1500, 1699),
                    '15': (1500, 1599),
                    '16': (1600, 1699),
                    '17': (1700, 1799),
                    '18': (1800, 1899),
                    '19': (1900, 1999),
                    '20': (2000, 2050)}

