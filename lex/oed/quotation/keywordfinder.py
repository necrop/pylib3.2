
import re
from lxml import etree
import stringtools
from lex.inflections.inflection import Inflection

INFLECTOR = Inflection()
SPACER = re.compile('(\u2025|\u2026|\u2014|\u2018|\u2019)')  # ellipses + dashes
PUNCTUATION = {':', ';', '!', '?', '(', ')', }
POSS_PRONOUNS = {'my', 'your', 'thy' 'our', 'his', 'her', 'its', 'their'}
REFL_PRONOUNS = {'myself', 'yourself', 'thyself' 'ourselves', 'himself',
                 'herself', 'itself' 'yourselves', 'themselves'}
PHRASE_ADJUSTMENTS = {
    'in': ['into', 'inside', 'within', 'on', ],
    'to': ['into', ],
    'into': ['in', 'onto', ],
    'on': ['onto', 'in', 'upon', ],
    'the': ['a', 'an', 'his', 'her', 'its', 'my', ],
    'a': ['the', 'his', 'her', 'its', 'my', ],
    'an': ['the', 'his', 'her', 'its', 'my', ],
    'to': ['into', ],
    'with': ['without', ],
    'without': ['with', ],
}


class KeywordFinder(object):

    def __init__(self):
        # Entry-level attributes
        self.entry_lemma = None
        self.formslist = None

        # Sense-level attributes
        self.lemma = None
        self.lemma_flat = None
        self.secondary_lemmas = None
        self.fallback_lemma = None
        self.wordclass = None
        self.local_variants = None
        self.local_variants_inflected = None
        self.inflections = None

    def null_entry_level_attributes(self):
        """
        Null any entry-level attributes
        """
        self.entry_lemma = None
        self.formslist = None

    def null_sense_level_attributes(self):
        """
        Null any sense-level attributes
        """
        self.lemma = None
        self.lemma_flat = None
        self.secondary_lemmas = None
        self.fallback_lemma = None
        self.wordclass = None
        self.local_variants = None
        self.local_variants_inflected = None
        self.inflections = None

    def ingest_entry(self, entry):
        # Clear the decks
        self.null_entry_level_attributes()
        self.null_sense_level_attributes()

        self.entry_lemma = entry.lemma
        self.formslist = _flatten_variants(entry.variants().formslist('uniqued'))

    def ingest_sense(self, sense):
        # Clear the decks
        self.null_sense_level_attributes()

        # If the sense is a main sense defining a compound or similar,
        #   we adopt the entry headword as a fallback in case the
        #   full compound can't be found (useful for absol. uses, etc.).
        if sense.is_subentry() or sense.is_subentry_like():
            fallback = None
        elif sense.lemma.lower() == self.entry_lemma.lower():
            fallback = None
        elif len(sense.lemma.split()) <= 2:
            fallback = stringtools.lexical_sort(self.entry_lemma)
        else:
            fallback = None

        self.lemma = sense.lemma
        self.lemma_flat = stringtools.lexical_sort(sense.lemma)
        self.secondary_lemmas = _find_secondary_lemmas(sense)
        self.fallback_lemma = fallback
        self.wordclass = sense.primary_wordclass().penn
        self.inflections = _inflection_set(sense.lemma, self.wordclass)

        if sense.is_subentry() or sense.is_subentry_like():
            variants = {}
        elif sense.lemma.lower() == self.entry_lemma.lower():
            variants = {f: d for f, d in self.formslist.items()}
        else:
            variants = {}
        lemma_flat = stringtools.lexical_sort(sense.lemma)
        variants[lemma_flat] = 2050
        # Allow "whippin'" for "whipping"
        if lemma_flat.endswith('ing'):
            variants[lemma_flat.rstrip('g')] = 2050

        self.local_variants = variants
        self.local_variants_inflected = _inflect_variants(variants, self.wordclass)

    def find_keyword(self, quotation):
        text = quotation.text.comment_stripped_text()
        text = SPACER.sub(' ', text)
        tokens, ngrams = _tokenize_text(text)
        year = quotation.year

        lemma = self.lemma
        lemma_flat = self.lemma_flat
        variants = self.local_variants_inflected

        # Simple matching
        match = _literal_match(lemma, text, tokens)
        if not match:
            match = _fuzzy_match(lemma_flat, tokens)
        if not match:
            match = _affix_match(lemma, lemma_flat, tokens)
        if not match:
            match = _inflected_match(self.inflections, tokens)
        if not match:
            match = _secondary_lemma_match(self.secondary_lemmas, tokens, ngrams)
        if not match:
            match = _hyphen_match(self.inflections, tokens)
        if not match:
            match = _open_compound_match(lemma_flat, ngrams)
        if not match:
            match = _variants_match(variants, tokens, year)
        if not match:
            match = _variants_flattened_match(variants, tokens, ngrams)
        if not match:
            match = _phrase_match(lemma, tokens, ngrams)
        if not match:
            match = _loose_phrase_match(lemma, text)
        if not match:
            match = _adjusted_phrase_match(lemma, text)
        if not match:
            match = _metaphone_match(variants, tokens, ngrams)
        if not match:
            match = _prefix_match(lemma, lemma_flat, tokens, year)
        if not match:
            match = _compound_prefix_match(lemma, text)
        if not match:
            match = _compound_reverse_match(lemma, tokens, ngrams)
        if not match:
            match = _fuzzy_match(self.fallback_lemma, tokens)
            #if match:
            #    print('-' * 30)
            #    print(lemma)
            #    print(text)
            #    print(match)

        return _keyword_cleanup(match, lemma)


#===========================================================
# Various different matching heuristics used by KeywordFinder.find_keyword()
#===========================================================

def _literal_match(lemma, text, tokens):
    match = None
    for token_full, token_flat in tokens:
        if (lemma == token_full or
                lemma + 's' == token_full or
                lemma + 'es' == token_full):
            match = token_full
            break
    if not match:
        lemma2 = _clean_brackets(lemma)
        regex = '[ ,;:!?(-](' + lemma2 + ')[ ,:;!?).-]'
        regmatch = re.search(regex, text, re.I)
        if regmatch:
            match = regmatch.group(1)
    return match


def _fuzzy_match(lemma_flat, tokens):
    if not lemma_flat:
        return None

    match = None
    for token_full, token_flat in tokens:
        if (lemma_flat == token_flat or
                lemma_flat + 's' == token_flat or
                lemma_flat + 'es' == token_flat):
            match = token_full
            break
    return match


def _affix_match(lemma, lemma_flat, tokens):
    match = None
    if lemma.startswith('-') and len(lemma_flat) >= 3:
        for token_full, token_flat in tokens:
            if token_flat.endswith(lemma_flat):
                match = token_full
                break
    elif lemma.endswith('-') and len(lemma_flat) >= 3:
        for token_full, token_flat in tokens:
            if token_flat.startswith(lemma_flat):
                match = token_full
                break
        if not match and len(lemma_flat) > 4:
            lemma_flat = lemma_flat[:4]
            for token_full, token_flat in tokens:
                if token_flat.startswith(lemma_flat):
                    match = token_full
                    break
    return match


def _inflected_match(inflections, tokens):
    match = None
    for token_full, token_flat in tokens:
        if token_flat in inflections:
            match = token_full
            break
    return match


def _hyphen_match(inflections, tokens):
    match = None
    for token_full, token_flat in tokens:
        parts = token_full.split('-')
        if len(parts) == 1:
            continue
        parts = [(p, stringtools.lexical_sort(p)) for p in parts]
        for p_full, p_flat in parts:
            if p_flat in inflections:
                match = p_full
        if match:
            break
    return match


def _open_compound_match(lemma_flat, bigrams):
    match = None
    for bigram_full, bigram_flat in bigrams:
        if (lemma_flat == bigram_flat or
                lemma_flat + 's' == bigram_flat or
                lemma_flat + 'es' == bigram_flat):
            match = bigram_full
            break
    return match


def _variants_match(variants, tokens, year):
    match = None
    for token_full, token_flat in tokens:
        if token_flat in variants and variants[token_flat] + 50 > year:
            match = token_full
            break
    return match


def _variants_flattened_match(variants, tokens, bigrams):
    flat_variants = set([_vowel_flattener(v) for v in variants])
    flat_variants = set([v for v in flat_variants if v])
    match = None
    for token_full, token_flat in tokens + bigrams:
        if _vowel_flattener(token_flat) in flat_variants:
            match = token_full
            break
    return match


def _phrase_match(lemma, tokens, bigrams):
    words = lemma.split()
    if len(words) < 3:
        return None

    match = None
    if words[0] == 'to':
        phrase_words = words[1:]
    else:
        phrase_words = words[:]

    phrase_words = [[w, stringtools.lexical_sort(w),] for w in phrase_words]
    for w in phrase_words:
        w_flat = w[1]
        if len(w_flat) > 3:
            w.append(w_flat[0:3])
        else:
            w.append(w_flat)

    phrase_flat = ''.join([w[1] for w in phrase_words])
    for token_full, token_flat in bigrams:
        if token_flat == phrase_flat:
            match = token_full
            break

    if not match:
        phrase_length = len(phrase_words)
        for i in range(0, len(tokens)-1):
            try:
                ngram = tokens[i:i+phrase_length]
            except IndexError:
                pass
            else:
                match_failed = False
                for p_token, q_token in zip(phrase_words, ngram):
                    if q_token[1].startswith(p_token[2]):
                        pass
                    elif p_token[0] in "one's" and q_token[0] in POSS_PRONOUNS:
                        pass
                    elif p_token[0] in "oneself" and q_token[0] in REFL_PRONOUNS:
                        pass
                    else:
                        match_failed = True
                        break
                if not match_failed:
                    match = ' '.join([t[0] for t in ngram])
                    break
    return match


def _loose_phrase_match(lemma, text):
    """
    Match a 3+ word phrase loosely by matching any window starting with
    the first and ending with the last word (thus allowing variation
    in the interior).
    """
    words = lemma.split()
    if len(words) < 2:
        return None

    if len(words) == 2:
        short_phrase = True
    else:
        short_phrase = False

    match = None
    if words[0] == 'to':
        phrase_words = words[1:]
    else:
        phrase_words = words[:]
    if len(phrase_words) < 2:
        return None
    if phrase_words[0] == 'be':
        return None

    # Pad the text to make matching on word-breaks easier
    text = ' ' + text + ' '
    word1 = _clean_brackets(phrase_words[0])
    word2 = _clean_brackets(phrase_words[-1])
    first_words = [word1, ]
    if len(word1) > 4:
        first_words.append(word1[0:4])

    # We have two shots at this; first using the first word in full,
    #  then just using the first four letters
    for first_word in first_words:
        if short_phrase:
            regex = '[ ,;:!?(-](' + first_word + ' [a-z-]+ ' + word2 + ')[ ,:;!?).-]'
        else:
            regex = '[ ,;:!?(-](' + first_word + '.*? ' + word2 + ')[ ,:;!?).-]'
        regmatch = re.search(regex, text, re.I)
        if regmatch:
            match = regmatch.group(1)
            break

    # Check that the span matched looks reasonable (not too many words,
    #   no medial punctuation)
    if match and len(match.split()) > len(phrase_words) + 2:
        match = None
    if (match and
            any([punc in match for punc in (',', ';', ':', '?', '!', '.')])):
        match = None
    return match


def _adjusted_phrase_match(lemma, text):
    """
    Try matching a phrase by adjusting prepositions and other function words.
    """
    words = lemma.split()
    if len(words) < 2:
        return None

    match = None
    alternatives = []
    for i, word in enumerate(words):
        if word in PHRASE_ADJUSTMENTS:
            for replacement in PHRASE_ADJUSTMENTS[word]:
                alternatives.append(_adjust_phrase(words, i, replacement))
    for phrase in alternatives:
        regex = '[ ,;:!?(-](' + phrase + ')[ ,:;!?).-]'
        regmatch = re.search(regex, text, re.I)
        if regmatch:
            match = regmatch.group(1)
            break
    return match


def _adjust_phrase(words, index, replacement):
    words2 = []
    for i, word in enumerate(words):
        if i == index:
            words2.append(replacement)
        else:
            words2.append(word)
    return ' '.join(words2)


def _secondary_lemma_match(secondary_lemmas, tokens, bigrams):
    match = None
    for lemma_full, lemma_flat in secondary_lemmas:
        for token_full, token_flat in tokens + bigrams:
            if (lemma_flat == token_flat or
                    lemma_flat + 's' == token_flat or
                    lemma_flat + 'es' == token_flat):
                match = token_full
                break
    return match


def _metaphone_match(variants, tokens, bigrams):
    flat_variants = set([stringtools.metaphone(v) for v in variants])
    flat_variants = set([v for v in flat_variants if len(v) > 1])
    match = None
    for token_full, token_flat in tokens + bigrams:
        if stringtools.metaphone(token_flat) in flat_variants:
            match = token_full
            break
    return match


def _prefix_match(lemma, lemma_flat, tokens, year):
    if ' ' in lemma or '-' in lemma or len(lemma_flat) < 6:
        return None
    match = None
    if year < 1800:
        for prefix_size in (4, 3):
            prefix = lemma_flat[0:prefix_size]
            for token_full, token_flat in tokens:
                if ' ' in token_full or '-' in token_full:
                    continue
                if len(token_flat) < 6:
                    continue
                if token_flat.startswith(prefix):
                    match = token_full
                    break
            if match:
                break
    if not match:
        # Look for match at the beginning *and* end of the word
        prefix = lemma_flat[0:2]
        suffix = lemma_flat[-2] + lemma_flat[-1]
        for token_full, token_flat in tokens:
            if ' ' in token_full or '-' in token_full:
                continue
            if len(token_flat) < 6:
                continue
            if token_flat.startswith(prefix) and token_flat.endswith(suffix):
                match = token_full
                break
    return match


def _compound_prefix_match(lemma, text):
    if lemma.startswith('-') or lemma.endswith('-'):
        return None
    if not ' ' in lemma and not '-' in lemma:
        return None
    lemma = lemma.replace('-', ' ')
    words = lemma.split()
    if len(words) != 2 or len(words[0]) < 4 or len(words[1]) < 4:
        return None

    match = None
    text = ' ' + text + ' '
    prefix1 = _clean_brackets(words[0])[0:3]
    prefix2 = _clean_brackets(words[1])[0:3]
    regex = '[ ,;:!?(-](' + prefix1 + '[a-z]+[ -]' + prefix2 + '[a-z]+)[ ,:;!?).-]'
    regmatch = re.search(regex, text, re.I)
    if regmatch:
        match = regmatch.group(1)
    return match


def _compound_reverse_match(lemma, tokens, ngrams):
    match = None
    words = lemma.split()
    if len(words) == 2:
        reverse1 = words[1] + ' ' + words[0]
        reverse2 = words[1] + 's ' + words[0]
        reverse1 = stringtools.lexical_sort(reverse1)
        reverse2 = stringtools.lexical_sort(reverse2)
        for token_full, token_flat in tokens + ngrams:
            if token_flat == reverse1 or token_flat == reverse2:
                match = token_full
                break
    return match


def _vowel_flattener(word):
    for before, after in (('ickal', 'ical'), ('ick', 'ic'), ('icke', 'ic'),
                          ('ique', 'ic'), ):
        word = word.replace(before, after)
    word = word.rstrip('e')
    for before, after in (('y', 'i'), ('v', 'u'), ('a', 'V'),
                          ('e', 'V'), ('o', 'V'), ):
        word = word.replace(before, after)
    word = word.replace('VV', 'V')
    return word


#==============================================================
# Convert text to tokens and ngrams
#==============================================================

def _tokenize_text(text):
    naive_tokens = text.split()
    tokens = [t.strip(',:;()[]."?! ') for t in naive_tokens]
    tokens = [re.sub(r"'s$", '', t) for t in tokens]
    tokens = [(t, stringtools.lexical_sort(t)) for t in tokens]
    ngrams = (_compile_ngrams(naive_tokens, 2) +
              _compile_ngrams(naive_tokens, 3) +
              _compile_ngrams(naive_tokens, 4))
    return tokens, ngrams


def _compile_ngrams(tokens, length):
    ngrams = []
    for i in range(0, len(tokens)):
        try:
            window = tokens[i:i+length]
        except IndexError:
            pass
        else:
            ngram = ' '.join(window)
            ngram = ngram.strip(',:;().!?- ')
            ngram = re.sub(r"'s$", '', ngram)
            # check for internal punctuation
            if any([p in ngram for p in PUNCTUATION]):
                pass
            else:
                ngrams.append((ngram, stringtools.lexical_sort(ngram)))
    return ngrams


#==============================================================
# Inflections
#==============================================================

def _inflection_set(lemma, wordclass):
    lemma_flat = stringtools.lexical_sort(lemma)
    if wordclass == 'NN':
        infs = {INFLECTOR.compute_inflection(lemma_flat, 'NNS'),
                lemma_flat + 's',
                re.sub(r'(...)um$', r'\1a', lemma_flat),
                re.sub(r'(...)us$', r'\1i', lemma_flat),
                re.sub(r'(...)sis$', r'\1ses', lemma_flat), }
    elif wordclass == 'VB':
        infs = {INFLECTOR.compute_inflection(lemma_flat, 'VBZ'),
                INFLECTOR.compute_inflection(lemma_flat, 'VBD'),
                INFLECTOR.compute_inflection(lemma_flat, 'VBG'),
                INFLECTOR.compute_inflection(lemma_flat, 'VBD', region='us'),
                INFLECTOR.compute_inflection(lemma_flat, 'VBG', region='us'),
                lemma_flat + 'in',
                lemma_flat + 'eth',
                lemma_flat + 'ethe',
                lemma_flat + 'est',
                lemma_flat + 'd',
                lemma_flat + 'id',
                lemma_flat + 'it',
                lemma_flat + 'de',
                lemma_flat + 'yng',
                lemma_flat + 'ynge', }
    elif wordclass in ('JJ', 'RB'):
        infs = {INFLECTOR.compute_inflection(lemma_flat, 'JJR'),
                INFLECTOR.compute_inflection(lemma_flat, 'JJS'),
                INFLECTOR.compute_inflection(lemma_flat, 'JJR', region='us'),
                INFLECTOR.compute_inflection(lemma_flat, 'JJS', region='us'),
                # We may as well throw in plural, since adj. and n. quotes
                #  are often mixed together ('Zyrian', etc.)
                INFLECTOR.compute_inflection(lemma_flat, 'NNS'), }
    else:
        infs = set()
    infs.add(lemma_flat)
    return infs


#==============================================================
# Variants
#==============================================================

def _inflect_variants(variants, wordclass):
    inflections = {}
    for variant, end_date in variants.items():
        inflections[variant] = end_date
        local_inflections = _inflection_set(variant, wordclass)
        for inf in local_inflections:
            if not inf in inflections or end_date > inflections[inf]:
                inflections[inf] = end_date
    return inflections


def _flatten_variants(variants):
    flat = {}
    for v in variants:
        if v.is_truncated() or not v.sort:
            continue
        if not v.sort in flat or v.date.end > flat[v.sort]:
            flat[v.sort] = v.date.end
    return flat


#==============================================================
# Secondary lemmas (lm, vl, vf)
#==============================================================

def _find_secondary_lemmas(sense):
    # Any other lemmas (<lm> or <vl> elements) in the sense
    secondary_lemmas = set()
    for tag in ('lm', 'vl', 'vf'):
        for node in sense.node.findall('.//' + tag):
            text = etree.tounicode(node,
                                   method='text',
                                   with_tail=False)
            # Skip truncated stuff
            if text.startswith('-') or text.endswith('-'):
                pass
            else:
                secondary_lemmas.add(text)
    secondary_lemmas.discard(sense.lemma)
    return [(l, stringtools.lexical_sort(l)) for l in secondary_lemmas]


def _clean_brackets(text):
    for punc in ('(', ')', '[', ']'):
        text = text.replace(punc, '')
    return text


def _keyword_cleanup(keyword, lemma):
    if keyword:
        keyword = keyword.strip()
        if keyword.endswith(' is') and not lemma.endswith(' is'):
            keyword = re.sub(r' is$', '', keyword)
            keyword = keyword.strip()
    return keyword
