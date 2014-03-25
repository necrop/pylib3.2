"""
stringtools

Functions for simplifying strings, especially used
to return the lexical-sort version of an input string.

Author: James McCracken
"""

from functools import lru_cache
import re
import string

from unidecode import unidecode
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import word_tokenize, sent_tokenize

from regexcompiler import ReplacementListCompiler


AZ_STRING = re.compile(r'^[a-z]+$')

PUNCTUATION_STRIPPER = ReplacementListCompiler((
    (r'&(amp|lt|gt);', ''),
    (r'[^a-zA-Z0-9 -]', ''),))

YOGH_HANDLER = ReplacementListCompiler((
    ('\u021d', 'g'),  # Special handling of yogh
    ('\u021c', 'G'),  # ditto uppercase-yogh
))

DIGIT_TRANSLATOR = ReplacementListCompiler((
    (r'0', r'zero'),
    (r'1', r'one'),
    (r'2', r'two'),
    (r'3', r'three'),
    (r'4', r'four'),
    (r'5', r'five'),
    (r'6', r'six'),
    (r'7', r'seven'),
    (r'8', r'eight'),
    (r'9', r'nine'),
))

# Run this *before* DIGIT_TRANSLATOR in order to turn
# all numbers into strings
NUMBER_TRANSLATOR = ReplacementListCompiler((
    (r'^|$', ' '),  # Add l- and r-padding (temporarily)
    (r'([^1-9])([2-9])000([^0-9])', r'\1\2thousand\3'),
    (r'([^1-9])([2-9])00([^0-9])', r'\1\2hundred\3'),
    (r'([^1-9])360([^0-9])', r'\1three-sixty\2'),
    (r'([^0-9])10([^0-9])', r'\1ten\2'),
    (r'([^0-9])11([^0-9])', r'\1eleven\2'),
    (r'([^0-9])12([^0-9])', r'\1twelve\2'),
    (r'([^0-9])13([^0-9])', r'\1thirteen\2'),
    (r'([^0-9])14([^0-9])', r'\1fourteen\2'),
    (r'([^0-9])15([^0-9])', r'\1fifteen\2'),
    (r'([^0-9])16([^0-9])', r'\1sixteen\2'),
    (r'([^0-9])17([^0-9])', r'\1seventeen\2'),
    (r'([^0-9])18([^0-9])', r'\1eighteen\2'),
    (r'([^0-9])19([^0-9])', r'\1nineteen\2'),
    (r'([^0-9])20([^0-9])', r'\1twenty\2'),
    (r'([^0-9])30([^0-9])', r'\1thirty\2'),
    (r'([^0-9])40([^0-9])', r'\1fourty\2'),
    (r'([^0-9])50([^0-9])', r'\1fifty\2'),
    (r'([^0-9])60([^0-9])', r'\1sixty\2'),
    (r'([^0-9])70([^0-9])', r'\1seventy\2'),
    (r'([^0-9])80([^0-9])', r'\1eighty\2'),
    (r'([^0-9])90([^0-9])', r'\1ninety\2'),
    (r'([^0-9])2(\d)([^0-9])', r'\1twenty-\2\3'),
    (r'([^0-9])3(\d)([^0-9])', r'\1thirty-\2\3'),
    (r'([^0-9])4(\d)([^0-9])', r'\1forty-\2\3'),
    (r'([^0-9])5(\d)([^0-9])', r'\1fifty-\2\3'),
    (r'([^0-9])6(\d)([^0-9])', r'\1sixty-\2\3'),
    (r'([^0-9])7(\d)([^0-9])', r'\1seventy-\2\3'),
    (r'([^0-9])8(\d)([^0-9])', r'\1eighty-\2\3'),
    (r'([^0-9])9(\d)([^0-9])', r'\1ninety-\2\3'),
    (r'^ | $', ''),  # Remove the temporary l- and r-padding
))

MEDIAL_HYPHEN_STRIPPER = ReplacementListCompiler((
    (r'(.)-(.)', r'\1\2'),
))
VOWELS = {'a', 'e', 'i', 'o', 'u'}

PORTER_STEM = PorterStemmer()


def strip_diacritics(text):
    """
    Remove diacritics from a string.

    In fact, transliterates any unicode string into the closest
    possible representation in ascii text.
    """
    return unidecode(text)


strip_accents = strip_diacritics


def asciify(text):
    """
    Extended version of strip_diacritics().

    Includes handling of some more rarefied characters like yogh.
    """
    if AZ_STRING.search(text):
        return text
    else:
        return strip_diacritics(YOGH_HANDLER.edit(text))


@lru_cache(maxsize=256)
def lexical_sort(text):
    """
    Returns the lexical-sort version of the input string.

    I.e. downcased, accent-stripped, hyphen- and punctuation-stripped,
    digits converted to strings.
    """
    if AZ_STRING.search(text):
        return text
    else:
        lex_sorted = asciify(text).lower()
        lex_sorted = convert_numbers_to_strings(lex_sorted)
        lex_sorted = strip_spaces(lex_sorted)
        lex_sorted = strip_all_hyphens(lex_sorted)
        lex_sorted = strip_punctuation(lex_sorted)
        return lex_sorted


dictionary_sort = lexical_sort


def strip_spaces(text):
    """
    Remove all spaces and tabs from the input string.
    """
    return text.strip().replace(' ', '').replace('\t', '')


def strip_punctuation(text):
    """
    Remove all punctuation from the input string.
    """
    return PUNCTUATION_STRIPPER.edit(text)


def strip_all_hyphens(text):
    """
    Remove all hyphens from the input string.
    """
    return text.replace('-', '')


def strip_medial_hyphens(text):
    """
    Remove any medial hyphens from the input string.
    (Preserves hyphens at the start and/or end of the string,
    e.g. for affixes.)
    """
    return MEDIAL_HYPHEN_STRIPPER.edit(text)


def strip_digits(text):
    """
    Remove any digits from the input string.
    """
    return re.sub(r'\d', '', text)


def sortcode(text):
    """
    Return a simple ASCII-sortable version of the input string.

    Similar to lexical_sort(), except that digits are removed
    rather than converted to words.
    """
    text = asciify(text).lower()
    text = strip_digits(text)
    text = strip_spaces(text)
    text = strip_all_hyphens(text)
    text = strip_punctuation(text)
    return text


def convert_numbers_to_strings(text):
    """
    Any digits in the string get converted to words.

    Check NUMBER_TRANSLATOR for exact rules for handling
    multiple digits.
    """
    if re.search(r'\d', text):
        text = NUMBER_TRANSLATOR.edit(text)
        text = DIGIT_TRANSLATOR.edit(text)
    return text


def initial(text):
    """
    Return the first a-z letter of a string (lower-cased).

    If the string'text lexical_sort() evaluates to '', returns 'z'

    Returns a single-letter string in the range a-z.
    """
    i = initial_or_none(text)
    if i is None:
        return 'z'
    else:
        return i


def initial_or_none(text):
    """
    Like initial(), except that it returns None if the string's
    lexical_sort() evaluates to ''.
    """
    text = lexical_sort(text)
    try:
        return text[0]
    except IndexError:
        return None


def terminator(text):
    """
    Return the last letter of a string (lower-cased).

    If the string's lexical_sort() evaluates to '', returns 'z'

    Returns a single-letter string in the range a-z.
    """
    last_letter = terminator_or_none(text)
    if last_letter is None:
        return 'z'
    else:
        return last_letter


def terminator_or_none(text):
    """
    Like terminator(), except that it returns None if the string's
    lexical_sort() evaluates to ''.
    """
    text = lexical_sort(text)
    try:
        return text[-1]
    except IndexError:
        return None


def prefix(text, length):
    """
    Returns the first x letters of the string's lexical_sort().

    The number of characters is supplied as the argument. If the
    lexical_sort has fewer characters than x, the prefix is
    zero-padded to the right.

    Arguments:
    1. string
    2. number of letters (integer)

    Returns: string
    """
    text = lexical_sort(text)
    pref = text[:length]
    while len(pref) < length:
        pref += '0'
    return pref


def suffix(text, length):
    """
    Return the last x letters of the string's lexical_sort().

    The number of characters is supplied as the argument. If
    lexical_sort() return fewer characters than x, the suffix is
    zero-padded to the left.

    Arguments:
    1. string
    2. number of letters (integer)

    Returns: string
    """
    text = lexical_sort(text)
    suff = text[-length:]
    while len(suff) < length:
        suff = '0' + suff
    return suff


def porter_stem(text):
    """
    Return Porter-stemmed version of the string.

    (Wrapper for nltk.PorterStemmer().)
    """
    return PORTER_STEM.stem(text)


def bisect(text):
    """
    Return a list of all the possible ways to slice the text in two.
    Each element in the list is a 2ple consisting of the first and last
    part.

    >>> bisect('fish')
    [('f', 'ish'), ('fi', 'sh'), ('fis', 'h')]
    """
    slices = []
    for i in range(len(text) - 1):
        start = text[:i + 1]
        end = text[i + 1:]
        slices.append((start, end,))
    return slices


def is_vowel(letter):
    """
    Return True if the letter is a vowel (or vowel with diacritics),
    return False otherwise.
    """
    letter = letter[0]  # just take the first letter, if more than one
    if letter.lower() in VOWELS or unidecode(letter.lower()) in VOWELS:
        return True
    else:
        return False


#=====================================================
# Tokenization
#=====================================================

def tokens(text):
    """
    Return a list of tokens from the string.

    (Wrapper for nltk.word_tokenize().)
    """
    return [word for sentence in sent_tokenize(text)
            for word in word_tokenize(sentence)]


def word_tokens(text):
    """
    Return a list of tokenized words only (no punctuation) from the string.
    """
    return [t for t in tokens(text) if not t in string.punctuation]
