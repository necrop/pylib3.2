import re

from wikipedia import wikipediaconfig
from lex.inflections.inflection import Inflection

NAMESPACES = wikipediaconfig.NAMESPACES
BRACKET_PATTERN = re.compile(r'^(.*) \(([^()]+)\)$')
SUPERORDINATE_PATTERNS = (
    [re.compile(r'^([a-z -]+)$'), 1],
    [re.compile(r'^([a-z-]+)(,| (of|in|by|from|for|on|born)) '), 1],
    [re.compile(r' ([a-z -]+)$'), 1],
)
SUPERORDINATE_TRIMMER = re.compile(r' (and|or|of) .*$')

LISTS = ('list', 'lists', 'index', 'comparison', 'glossary',
         'complete list', 'outline', 'records')
LISTLIKE = ('discography', 'bibliography', 'filmography', 'timeline',
            'chronology')

COMPETITION_PATTERN = re.compile(r'^(19[0-9][0-9]|20[01][0-9])((-|\u2013)[0-9][0-9]?|) ([A-Z]|in )')
YEAR_IN = re.compile(r'^(1[0-9][0-9]|20[01])([0-9]|0s) in ')
YEARS = re.compile(r'^([1-9][0-9]?[0-9]? BC|[1-9][0-9]?[0-9]?|\d+(th|nd|st) (century|millennium) BC)$')

YEAR_PATTERN = re.compile('[ (](1[0-9][0-9][0-9]|20[01][0-9])([ ),-]|\u2013)')


class ArticleTitle(object):

    """
    The title of a Wikipedia article

    Usage:
    >>> article_title = ArticleTitle('Paradise Lost (band)')
    """

    def __init__(self, title, **kwargs):
        self.full = str(title or '').strip()
        if not kwargs.get('retain_underscores'):
            self.full = self.full.replace('_', '')
        self._namespace = None
        self._main = None
        self._plural = None
        self._qualifier = None
        self._namespacestripped = None
        self._title_parsed = False

        self._qualifier_superordinate = None
        self._qualifier_parsed = False

    def __unicode__(self):
        return self.full

    def __repr__(self):
        return self.full

    def __len__(self):
        return len(self.full)

    @property
    def namespace(self):
        """
        Return the namespace prefix ('Wikipedia', 'Category', etc.)

        Returns a string, or None if the title is not namespaced.
        """
        self._parse_title()
        return self._namespace

    @property
    def namespacestripped(self):
        """
        Return the title without any preceding namespace prefix
        ('Wikipedia', 'Category', etc.)

        Returns a string.
        """
        self._parse_title()
        return self._namespacestripped

    @property
    def main(self):
        """
        Return the base title (without any namespace prefix, and without any
        bracketed qualification).

        Returns a string.

        Usage:
        >>> ArticleTitle('Paradise Lost (band)').main
        Paradise Lost
        >>> ArticleTitle('Category:C++ Standard Library').main
        C++ Standard Library
        """
        self._parse_title()
        return self._main

    @property
    def plural(self):
        if self._plural is None:
            self._plural = Inflection().pluralize(self.main)
        return self._plural

    def may_be_pluralized(self):
        if re.search(r'[a-z]{3}[^siauy]s$', self.main):
            return True
        else:
            return False

    @property
    def main_wordcount(self):
        """
        Return the number of words in the main part of the title.

        Returns int
        """
        return self.main.count(' ') + 1

    @property
    def qualifier(self):
        """
        Return any bracketed qualifier on the end of the title (without
        the brackets).

        Returns a string, or None of there's no qualifier.

        Usage:
        >>> ArticleTitle('Paradise Lost (band)').qualifier
        band
        >>> ArticleTitle('Category:C++ Standard Library').qualifier
        None
        """
        self._parse_title()
        return self._qualifier

    @property
    def qualifier_superordinate(self):
        self._parse_qualifier()
        return self._qualifier_superordinate

    def is_listlike(self):
        """
        Return True if the title indicates that this article
        is list-like.
        """
        lc_title = self.full.lower()
        if any(lc_title.startswith(listword + ' of ') for listword in LISTS):
            return True
        elif any(listname in lc_title for listname in LISTLIKE):
            return True
        elif self.full.endswith(' records'):
            # We have to avoid checking for 'records' in the lower-cased
            #  version of the title, since then we'd also match things like
            #  'Blue Note Records'
            return True
        elif YEAR_IN.search(self.full) or YEARS.search(self.full):
            return True
        return False

    def is_competition(self):
        """
        Return True if the title indicates that this article
        is a sports event or competition - based on the
        fact that it begins with a year.
        """
        if COMPETITION_PATTERN.search(self.full):
            return True
        else:
            return False

    def is_language(self):
        for ending in ('language', 'dialect'):
            if (self.main.endswith(' ' + ending) or
                    self.main.endswith(' ' + ending + 's')):
                return True
        return False

    def is_disambiguation_page(self):
        """
        Return True if the title indicates that this article
        is a disambiguation page.
        """
        if self.qualifier in ('disambiguation', 'surname', 'given name'):
            return True
        else:
            return False

    def contains_date(self):
        text = ' ' + self.full + ' '
        if YEAR_PATTERN.search(text):
            return True
        else:
            return False

    def _parse_title(self):
        if self._title_parsed:
            return

        if ':' in self.full:
            nmsp = self.full.split(':')[0]
            if nmsp.strip().lower() in NAMESPACES:
                self._namespace = nmsp.strip()

        namespacestripped = self.full
        if self._namespace:
            namespacestripped = namespacestripped\
                .replace(self._namespace + ':', '').strip()

        main = namespacestripped
        qualifier = None
        match = BRACKET_PATTERN.search(main)
        if match:
            main = match.group(1).strip()
            qualifier = match.group(2).strip()

        self._namespacestripped = namespacestripped
        self._main = main
        self._qualifier = qualifier
        self._title_parsed = True

    def _parse_qualifier(self):
        # Find the superordinate from within the bracketed qualifier
        if self._qualifier_parsed:
            return

        superordinate = None
        if self.qualifier:
            for pattern, match_index in SUPERORDINATE_PATTERNS:
                match = pattern.search(self.qualifier)
                if match:
                    superordinate = match.group(match_index)
                    break

        # Tidy up - just take the last word of the phrase
        if superordinate:
            superordinate = SUPERORDINATE_TRIMMER.sub('', superordinate)
            superordinate = superordinate.split()[-1]

        self._qualifier_superordinate = superordinate
        self._qualifier_parsed = True
