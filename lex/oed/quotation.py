"""
Quotation -- OED quotation class.

@author: James McCracken
"""

import re
from collections import defaultdict

from lxml import etree  # @UnresolvedImport

import stringtools
from regexcompiler import ReplacementListCompiler
from lex.oed.oedcomponent import OedComponent

# Used to help spot dictionary quotations
GLOSSLIKE = ('Dict.', 'Gloss.', 'Lexicon', 'Word-bk.',
             'World of Words', 'N.E.D.')
# Used to help spot newspaper quotations
NEWSPAPER_NAMES = set(('Herald', 'Times', 'Star', 'Daily', 'Morning',
                       'Evening', 'Echo', 'Post', 'Telegraph',
                       'Recorder', 'Sentinel', 'Guardian', 'Mail',
                       'Gaz.', 'Saturday', 'Sunday', 'Tel.', 'Inquirer',
                       'Sun', 'Mercury', 'Advertiser', 'Gazette',))

# Used to modernize quotation text prior to tokenizing/stemming
MODERNIZER = ReplacementListCompiler((
    (r'^vn', r'un'),
    (r'([aeiou])u([aeiou])', r'\1v\2'),
))

BINOMIAL_PATTERN = re.compile(
    r'^([A-Z]([a-z]{3,}[saxonm]|\.) [a-z]{4,}[saxonmie])$')


class Quotation(OedComponent):

    """
    OED quotation class.
    """

    def __init__(self, node):
        OedComponent.__init__(self, node)

    def is_suppressed(self):
        """
        Return True if this is a suppressed quotation
        """
        if self.node.get('supp') or self.node.get('suppressed'):
            return True
        else:
            return False

    def is_bracketed(self):
        """
        Return True if this is a square-bracketed quotation
        """
        info_text = self.node.get('info', 'no').lower()
        if info_text in ('yes', 'intro'):
            return True
        else:
            return False

    def year(self):
        """
        Return the quotation date, as an integer.

        By default, this is taken from the value of the dorder attribute,
        not from the text of the <d> element.
        """
        try:
            return self._year
        except AttributeError:
            date_node = self.node.find('./cit/d')
            if date_node is not None:
                year_string = date_node.get('dorder', '')
            else:
                year_string = ''
            match = re.search(r'(\d+)', year_string)
            if match is not None:
                num_string = match.group(1)
                if len(num_string) == 6:
                    year = num_string[:4]
                elif len(num_string) == 4:
                    year = num_string
                else:
                    year = 0
            else:
                year = 0
            self._year = int(year)
            return self._year

    date = year

    #=========================================================
    # Functions relating to the quotation text
    #=========================================================

    def text(self):
        """
        Return the text of the quotation (<qt> element),
        as an untagged string.

        Returns None if the quotation has no <qt> element.
        """
        try:
            return self._text
        except AttributeError:
            if self.node.find('.//qt') is not None:
                self._text = etree.tounicode(self.node.find('.//qt'),
                                             method='text')
            else:
                self._text = None
            return self._text

    def tokens(self):
        """
        Return the text of the quotation as a list of tokens
        (including punctuation).
        """
        try:
            return self._tokens
        except AttributeError:
            if self.text() is None:
                self._tokens = []
            else:
                text = self.text().replace('*', '')
                text = re.sub(r'(\.\.|\u2014|\u2018|\u2019)', r' \1 ', text)
                self._tokens = stringtools.tokens(text)
            return self._tokens

    def keyword_index(self, keyword):
        """
        Find the position of the keyword (entry headword, etc.) in
        the sequence of tokens making up the quotation text.

        Returns a tuple of two integers indicating the index position
        (zero-based) of the start and end of the keyword. These will be the
        same if the keyword is a single-word lemma, but will be different
        if it's a 2- or 3-word lemma.

        Returns None if the keyword was not found.
        """
        def normalize(word):
            """
            Return a stemmed/modernized version of the token
            """
            word = stringtools.porter_stem(word.lower().strip())
            word = word.replace(' ', '').replace('-', '').replace('.', '')
            return MODERNIZER.edit(word)

        keyword_stem = normalize(keyword)
        for ngram_length in (1, 2, 3):
            for i in range(len(self.tokens()) - ngram_length + 1):
                ngram = ''.join(self.tokens()[i:i + ngram_length])
                if normalize(ngram) == keyword_stem:
                    return (i, i + ngram_length - 1,)
        return None

    def ranked_collocates(self, keyword):
        """
        Score each word-like token in the quotation text, apart from
        the keyword(s) itself.

        Score is determined by distance from the keyword
        (minimum distance, if the token occurs more than once),
        up to a maximum of 10

        Returns a list of 2-ples (ranked by score). Each 2-ple consists of
         -- the lemma stem (as returned by Porter stemmer;
         -- the score (1-10)
        """
        kw_position = self.keyword_index(keyword)
        collocates = defaultdict(list)
        for i, token in enumerate(self.tokens()):
            if kw_position is None:
                distance = 10
            elif i < kw_position[0]:
                distance = kw_position[0] - i
            elif i > kw_position[1]:
                distance = i - kw_position[0]
            else:
                distance = 10
            if re.search(r'^([a-zA-Z]+|[a-zA-Z]+-[a-zA-Z]+)$', token):
                token = token.lower()
                if self.year() < 1800:
                    token = MODERNIZER.edit(token)
                stem = stringtools.porter_stem(token)
                collocates[stem].append(distance)

        collrank = [(token, min(distances))
                    for token, distances in collocates.items()]
        collrank.sort(key=lambda token: token[1], reverse=True)
        return collrank

    def binomials(self):
        """
        Return a list of any <i>-tagged genus terms found in
        the quotation text.

        Attempts to expand any abbreviated terms where possible.
        """
        # Bail out if this quotation is from pre-Linnean times
        if self.year() < 1750:
            return []

        italic_text = []
        text_node = self.node.find('.//qt')
        if text_node is not None:
            for italic_node in text_node.findall('./i'):
                if italic_node.text is not None and italic_node.text:
                    text = italic_node.text.strip(':,(); ')
                    italic_text.append(text)

        binoms = []
        genus_terms = []
        for text in italic_text:
            if BINOMIAL_PATTERN.search(text):
                word1, word2 = text.split()
                if re.search(r'^[A-Z]\.$', word1):
                    # Attempt expansion
                    initial = word1[0]
                    for genus in genus_terms:
                        if genus.startswith(initial):
                            text = genus + ' ' + word2
                else:
                    # Store the first term as a genus term
                    genus_terms.append(word1)
                binoms.append(text)
            elif re.search(r'^[A-Z][a-z]+[saxomn]$', text):
                # Any one-word <i>-tagged text gets stored as a genus term
                genus_terms.append(text)
        return binoms



    #=========================================================
    # Functions relating to the citation (author/title)
    #=========================================================

    def _citation(self):
        """
        Return the citation node (<cit>).
        """
        return self.node.find('./cit')

    def _bibsub(self):
        """
        Return the <bibSub> node.
        """
        if self._citation() is not None:
            if self._citation().find('./bibSub') is not None:
                return self._citation().find('./bibSub')
            else:
                return self._citation().find('./bibMain')
        else:
            return None

    def _bibmain(self):
        """
        Return the <bibMain> node.
        """
        if self._citation() is not None:
            return self._citation().find('./bibMain')
        else:
            return None

    def author(self, **kwargs):
        """
        Return the first author name.

        Include the argument 'full=True' to return the full form
        of the author name.
        """
        if not self.author_forms():
            return None
        elif kwargs.get('full') == True and len(self.author_forms()) > 1:
            return self.author_forms()[1]
        else:
            return self.author_forms()[0]

    def title(self, **kwargs):
        """
        Returns the title.

        Include the argument 'full=True' to return the full form of the title
        """
        if not self.title_forms():
            return None
        elif kwargs.get('full') == True and len(self.title_forms()) > 1:
            return self.title_forms()[1]
        else:
            return self.title_forms()[0]

    def citation_signature(self):
        """
        Return a simple author + title text version of the citation.
        """
        sig = ''
        if self.author() is not None:
            sig += self.author() + ' '
        if self.title() is not None:
            sig += '_%s_' % self.title()
        return sig.strip()

    def author_forms(self):
        try:
            self._author_forms
        except AttributeError:
            self._author_forms = []
            if self._bibsub() is not None:
                anode = self._bibsub().find('.//a')
                if anode is not None:
                    self._author_forms.append(anode.text)
                    if anode.get('ch_fullAuthor') is not None:
                        self._author_forms.extend(
                            anode.get('ch_fullAuthor').split('|'))
        return self._author_forms

    def title_forms(self):
        try:
            self._title_forms
        except AttributeError:
            self._title_forms = []
            if self._bibmain() is not None:
                tnode = self._bibmain().find('.//w')
                if tnode is not None:
                    text = etree.tounicode(tnode,
                                           method='text')
                    self._title_forms.append(text)
                    if tnode.get('ch_fullTitle') is not None:
                        self._title_forms.extend(
                            tnode.get('ch_fullTitle').split('|'))
        return self._title_forms

    def citation_matches(self, **kwargs):
        """
        Return True if the citation matches any of the list of authors
        and/or titles passed as keyword arguments.
        """
        authors = kwargs.get('authors', [])
        titles = kwargs.get('titles', [])
        authors_matched = [a for a in authors if a in self.author_forms()]
        titles_matched = [t for t in titles if t in self.title_forms()]
        if ((authors_matched or not authors) and
            (titles_matched or not titles)):
            return True
        else:
            return False

    def is_glossary(self):
        """
        Return True if the quotation appears to be from a
        dictionary or glossary.
        """
        for word in GLOSSLIKE:
            if word in self.title():
                return True
        return False

    def is_newspaper(self):
        """
        Return True if the quotation appears to be from a newspaper.
        """
        if self.author() is not None:
            return False
        if self._citation() is None or self.title() is None:
            return False
        if self._citation().find('.//place') is not None:
            return True
        if self._citation().find('.//di')is not None:
            date = self._citation().find('.//di').text
            if date and re.search(r'^[123]?[0-9] [A-Z]', date):
                tokens = self.title().split()
                if any([token in NEWSPAPER_NAMES for token in tokens]):
                    return True
        return False
