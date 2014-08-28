import re
from .. import wikipediaconfig

COUNTRIES_FILE = wikipediaconfig.COUNTRIES_FILE
IA_FOLLOWING_WORDS = 'is|was|has|may|can|will|in|with|by|for|at|of|to'
PL_FOLLOWING_WORDS = 'are|were|have'
NONLEXICAL_ENDINGS = {'family', 'history', }


class LexicalityTester(object):

    countries = set()

    def __init__(self, article):
        self.article = article
        self._searchable_lines = None
        if not LexicalityTester.countries:
            _load_countries()

    def is_lexical(self):
        if not self.title_may_be_lexical():
            return False
        if self.title_is_lexical():
            return True
        if self.prepluralized() and self.article.title.main_wordcount == 1:
            return True

        plurals = self.num_plurals()
        lowers = self.num_lowercase_forms()
        capitalized = self.num_capitalized_forms()
        indefs = self.num_indefinite_articles()
        if (plurals + lowers + indefs > capitalized and
                plurals + lowers + indefs > 4):
            return True
        if plurals + indefs > 6:
            return True
        return False

    def title_may_be_lexical(self):
        """
        Return True if this title *could* represent a lexical item,
        as opposed to an encyclopedic/proper-name entity, essay, etc.

        Note that this should be used as a preliminary filter only: it will
        return False for titles that are obviously not lexical; but
        returning True does not guarantee that the article really is lexical.

        Returns:
            bool
        """
        title = self.article.title
        tokens = title.main.split()
        tokens_lower = [w.lower() for w in tokens]
        if not tokens or len(tokens) > 3:
            return False
        if tokens[-1] in LexicalityTester.countries:
            return False
        for invalid in ('in', 'the', 'by', '&'):
            if invalid in tokens_lower:
                return False
        for invalid in ',.;:/0123456789':
            if invalid in title.main:
                return False
        if '\u2013' in title.main:
            return False
        for word in ('History', 'Economy', 'Demographics', 'Geography',
                     'Politics'):
            if title.main.startswith(word + ' of '):
                return False
        for word in ('languages', 'history'):
            if title.main.lower().endswith(' ' + word):
                return False
        return True

    def title_is_lexical(self):
        """
        Return True if this title's capitalization indicates that this
        definitely *is* lexical (though this will not be sufficient
        to catch *all* lexical articles).

        Returns:
            bool
        """
        title = self.article.title
        tokens = title.main.split()
        if (len(tokens) > 1 and
                re.search(r'^[a-z]{4,}$', tokens[-1]) and
                tokens[-1] not in NONLEXICAL_ENDINGS):
            return True
        else:
            return False

    @property
    def searchable_lines(self):
        if self._searchable_lines is None:
            fulltext = self.article.plaintext_main
            lines = [l.strip().replace('-', '') for l in
                     fulltext.split('\n') if l.strip()]
            # We add a sentence-end and sentence-start on the end of each
            #  line, so that we can keep the regexes simpler
            lines = ['. ' + line + ' An ' for line in lines]
            self._searchable_lines = lines
        return self._searchable_lines

    def num_plurals(self):
        """
        Return the number of plural forms of the article title found
        in the full text.

        Returns:
            int
        """
        if self.article.title.plural == self.article.title.main:
            return 0
        pluralform = self.article.title.plural.replace('-', '')
        plural_search = re.compile('[ (]' + pluralform + '[ .,;:)]', re.I)
        num_plurals = 0
        for line in self.searchable_lines:
            num_plurals += len(plural_search.findall(line))
        return num_plurals

    def prepluralized(self):
        """
        Return > 0 if the title appears to already be in the plural
        (in which case we assume that it must be lexical).

        This requires the following conditions:
        - the title ends in 's'
        - the title appears in the full text followed by 'are', 'were', etc.

        Returns:
            int (number of such occurrences found)
        """
        if not self.article.title.may_be_pluralized():
            return 0
        pluralform = self.article.title.main.replace('-', '')
        plural_search = re.compile('[ (]' + pluralform +
                                   ' (' + PL_FOLLOWING_WORDS + ') ', re.I)
        num_plurals = 0
        for line in self.searchable_lines:
            num_plurals += len(plural_search.findall(line))
        return num_plurals

    def num_lowercase_forms(self):
        """
        Return the number of lower-case forms of the article title found
        in the full text.

        Returns:
            int
        """
        lc_form = self.article.title.main.lower().replace('-', '')
        lc_search = re.compile('[ (]' + lc_form + '[ .,;:)]')
        num_lc = 0
        for line in self.searchable_lines:
            matches = lc_search.findall(line)
            num_lc += len(matches)
        return num_lc

    def num_capitalized_forms(self):
        """
        Return the number of capitalized forms of the article title (i.e.
        forms capitalized the same way as the article title) found in
        the full text.

        We skip those at the start of sentences, since we'd expect these
        to be capitalized anyway, so are not indicative.

        Returns:
            int
        """
        uc_form = self.article.title.main.replace('-', '')
        uc_search = re.compile('[^.] ' + uc_form + '[ .,;:)]')
        num_uc = 0
        for line in self.searchable_lines:
            matches = uc_search.findall(line)
            num_uc += len(matches)
        return num_uc

    def num_indefinite_articles(self):
        """
        Return the number of times the article title appears in the full
        text preceded by indefinite article ('a', 'an') and followed
        by 'is', 'was', 'has',  etc. - indicating that it's a lexical
        term rather than a proper name.

        Returns:
            int
        """
        # Note that we have to be careful about the following word, in
        #  case the article title is being used attributively - e.g.
        #  'a London street' would not be evidence that 'London' is lexical.
        ia_form = self.article.title.main.replace('-', '')
        ia_pattern = (' an? ' + ia_form +
                      '([.;:,)]| (' + IA_FOLLOWING_WORDS + ')) ')
        ia_search = re.compile(ia_pattern, re.I)
        num_ia = 0
        for line in self.searchable_lines:
            matches = ia_search.findall(line)
            num_ia += len(matches)
        return num_ia


def _load_countries():
    with open(COUNTRIES_FILE, 'r') as filehandle:
        for line in filehandle:
            LexicalityTester.countries.add(line.strip())
