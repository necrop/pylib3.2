import re
from collections import defaultdict
from lxml import etree

import stringtools
from regexcompiler import ReplacementListCompiler


# Used to modernize quotation text prior to tokenizing/stemming
MODERNIZER = ReplacementListCompiler((
    (r'^vn', r'un'),
    (r'([aeiou])u([aeiou])', r'\1v\2'),
))
COMMENT_STRIPPER = ReplacementListCompiler((
    (r'<cm(>| [^<>]*>)([^<>]{1,2})</cm>', r'\2'),
    (r'<cm[ >].*?</cm>', ''),
    (r' ([,.;:])', r'\1'),
    (' (\u2025|\u2026)', r'\1'),  # 2-dot and 3-dot ellipsis
    (r'  +', ' '),
))
BINOMIAL_PATTERN = re.compile(
    r'^([A-Z]([a-z]{3,}[saxonm]|\.) [a-z]{4,}[saxonmie])$')


class QuotationText(object):

    def __init__(self, node, year):
        if node is None:
            self.node = etree.Element('qt')
        else:
            self.node = node
        self.year = year
        self._plaintext = None
        self._tokens = None
        self._keyword = None

    @property
    def plaintext(self):
        if self._plaintext is None:
            self._plaintext = etree.tounicode(self.node, method='text') or ''
        return self._plaintext

    def is_empty(self):
        if not self.plaintext:
            return True
        else:
            return False

    @property
    def keyword(self):
        """
        Retrieve the keyword (if the quotation has been <kw>-tagged)
        """
        if self._keyword is None:
            kwnode = self.node.find('.//kw')
            if kwnode is not None:
                serialized = etree.tounicode(kwnode)
                if '<cm' in serialized:
                    serialized = COMMENT_STRIPPER.edit(serialized)
                serialized = re.sub(r'<[^<>]+>', '', serialized)
                self._keyword = serialized.strip()
        return self._keyword

    @property
    def tokens(self):
        """
        Return a list of tokens from the text (including punctuation).

        Note that square=bracketed comments have been removed first.
        """
        if self._tokens is None:
            text = self.comment_stripped_text().replace('*', '')
            if not text:
                self._tokens = []
            else:
                text = re.sub(r'(\.\.|\u2014|\u2018|\u2019)', r' \1 ', text)
                self._tokens = stringtools.tokens(text)
        return self._tokens

    def comments(self):
        return self.node.findall('.//cm')

    def comment_stripped_text(self):
        """
        Return a version of the plain text with any square-bracketed
        comments removed.
        """
        serialized = etree.tounicode(self.node)
        if '<cm' in serialized:
            stripped = COMMENT_STRIPPER.edit(serialized)
            try:
                new_node = etree.XML(stripped)
            except etree.XMLSyntaxError:
                new_node = self.node
        else:
            new_node = self.node
        return etree.tounicode(new_node, method='text') or ''

    def keyword_index(self, lemma=None):
        """
        Return the position of the keyword in the sequence of tokens
        making up the quotation text.

        Keyword arguments:
        -- lemma: used as a fallback in case the quotation is not
           <kw>-tagged, or the keyword position can't be found

        Returns an int indicating the token index (zero-indexed), or None
        if the keyword position was not found.
        """
        return keyword_index_position(self.tokens, self.keyword, lemma)

    def ranked_collocates(self, lemma):
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
        kw_index = self.keyword_index(lemma=lemma)
        if kw_index:
            keyword_start, keyword_end = kw_index
        else:
            keyword_start, keyword_end = (None, None)

        collocates = defaultdict(list)
        for i, token in enumerate(self.tokens):
            # How far is this token from the keyword (assuming we've
            #  located the keyword)?
            if keyword_start is None:
                distance = 10
            elif i < keyword_start:
                distance = keyword_start - i
            elif i > keyword_end:
                distance = i - keyword_end
            else:
                distance = 10

            if re.search(r'^([a-zA-Z]+|[a-zA-Z]+-[a-zA-Z]+)$', token):
                token = token.lower()
                if self.year < 1800:
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
        if self.year < 1750:
            return []

        italic_text = []
        for italic_node in self.node.findall('./i'):
            if italic_node.text is not None and italic_node.text:
                text = italic_node.text.strip(':,(); ')
                italic_text.append(text)

        _binomials = []
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
                _binomials.append(text)
            elif re.search(r'^[A-Z][a-z]+[saxomn]$', text):
                # Any one-word <i>-tagged text gets stored as a genus term
                genus_terms.append(text)
        return _binomials


def keyword_index_position(tokens, keyword, lemma):
    """
    Find the position of the keyword (entry headword, etc.) in
    the sequence of tokens making up the quotation text.

    Returns a tuple of two integers indicating the index position
    (zero-based) of the start and end of the keyword. (These will be the
    same if the keyword is a single word, but will be different
    if it's a 2- or 3-word phrase.)

    Returns None if the keyword was not found.
    """
    def _normalize(word):
        """
        Return a stemmed/modernized version of the token
        """
        word = stringtools.porter_stem(word.lower().strip())
        word = word.replace(' ', '').replace('-', '').replace('.', '')
        return MODERNIZER.edit(word)

    for target in (keyword, lemma):
        if not target:
            continue
        keyword_stem = _normalize(target)
        for ngram_length in (1, 2, 3):
            for i in range(len(tokens()) - ngram_length + 1):
                ngram = ''.join(tokens()[i:i + ngram_length])
                if _normalize(ngram) == keyword_stem:
                    return (i, i + ngram_length - 1,)
    return None




