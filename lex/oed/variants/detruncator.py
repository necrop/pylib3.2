"""
Detruncator -- detruncate truncated variants.
TruncationChecker --

@author: James McCracken
"""

import re

from lex.lemma import Lemma


class Detruncator(object):

    """
    Detruncate truncated variants by comparing with a full lemma
    """

    def __init__(self):
        self.comparator = None
        self.truncation = None
        self._truncation_features = {}

    def set_comparator(self, arg):
        self.comparator = _create_lemma_object(arg)

    def set_truncation(self, arg):
        self.truncation = _create_lemma_object(arg)
        self._truncation_features = {}

    def set_feature(self, name, value):
        self._truncation_features[name] = bool(value)

    def has_feature(self, name):
        try:
            return self._truncation_features[name]
        except KeyError:
            return False

    def detruncate(self):
        full_form = None  # default
        try:
            self.comparator
        except AttributeError:
            raise AttributeError('Comparator must be set before detruncating.')
        try:
            self.truncation
        except AttributeError:
            raise AttributeError('Truncation must be set before detruncating.')

        if (self.comparator.is_affix() or
                not self.truncation.is_affix() or
            self.has_feature('compound')):
            return None

        # Handle infixes
        if full_form is None and self.truncation.is_infix():
            full_form = _infix_handler(self.comparator, self.truncation)
            return full_form  # Don't attempt anything further for infixes

        # Easy matches in the case of hyphenated or space compounds - just
        #  check if the truncated form is similar to the first or last word
        #  in the compound
        if self.comparator.is_compound():
            full_form = _compound_handler(self.comparator, self.truncation)

        # Handle cases where the truncated form matches the start or end of the
        #  comparator form (i.e. no change)
        if full_form is None and len(self.truncation.lexical_sort()) >= 3:
            full_form = _unchanged_handler(self.comparator, self.truncation)

        # Handle cases where the first (or last) 3 letters of the truncated\
        #  form matches the first (or last) 3 letters of a text of the
        #  comparator.
        if full_form is None and len(self.truncation.lexical_sort()) >= 5:
            full_form = _substring_handler(self.comparator, self.truncation)

        # Handle plurals
        if (full_form is None and
                self.has_feature('plural') and
            self.truncation.is_suffix()):
            full_form = _plural_handler(self.comparator, self.truncation)

        # Handle more awkward cases requiring fuzzy matching
        if full_form is None:
            full_form = _fuzzy_matcher(self.comparator, self.truncation)

        if full_form is not None:
            # sanitize
            for before, after in (('--', '-'), ('  ', ' '),
                                  ('- ', ' '), (' -', ' ')):
                full_form = full_form.replace(before, after)
        return full_form


def _create_lemma_object(arg):
    if isinstance(arg, Lemma):
        return arg
    else:
        try:
            arg.lower()
        except AttributeError:
            raise TypeError('Argument must be a string or a Lemma object.')
        else:
            return Lemma(arg)


def _infix_handler(comparator, truncation):
    full_form = None
    ends = re.search(r'^(.)..?(.)$', truncation.lexical_sort())
    if ends is not None:
        pattern = re.compile(r'^(.*)' + ends.group(1) + '.?.?' +
                             ends.group(2) + '(.*)$')
        match = pattern.search(comparator.parenstripped())
        if match is not None:
            full_form = '%s%s%s' % (match.group(1),
                                    truncation.hyphenstripped(),
                                    match.group(2))
    else:
        ends = re.search(r'^(.)(.)$', truncation.lexical_sort())
        if ends is not None:
            pattern = re.compile(r'^(.*)' + ends.group(1) + '.' +
                                 ends.group(2) + '(.*)$')
            match = pattern.search(comparator.parenstripped())
            if match is not None:
                full_form = '%s%s%s' % (match.group(1),
                                        truncation.hyphenstripped(),
                                        match.group(2))
    return full_form


def _compound_handler(comparator, truncation):
    full_form = None
    if truncation.is_suffix():
        hyph_match = re.search('^(.*[ -])(' + truncation.initial() + '.*)$',
                               comparator.parenstripped())
        if hyph_match is not None:
            word1, word2 = hyph_match.groups()
            if abs(len(word2) - len(truncation.hyphenstripped())) < 4:
                full_form = word1 + truncation.hyphenstripped()
    elif truncation.is_prefix():
        pattern = '^(.*' + truncation.terminator() + 'e?)([ -].*)$'
        hyph_match = re.search(pattern, comparator.parenstripped())
        if hyph_match is None and truncation.terminator() == 'e':
            before_final_e = re.search(r'([a-z])e-$', truncation.lemma)
            if before_final_e is not None:
                pattern = '^(.*' + before_final_e.group(1) + ')([ -].*)$'
                hyph_match = re.search(pattern, comparator.parenstripped())
        if hyph_match is not None:
            word1, word2 = hyph_match.groups()
            if abs(len(word1) - len(truncation.hyphenstripped())) < 4:
                full_form = truncation.hyphenstripped() + word2
    return full_form


def _unchanged_handler(comparator, truncation):
    full_form = None
    for left_slice, right_slice in comparator.slices():
        if (truncation.is_prefix() and
            left_slice.lexical_sort() == truncation.lexical_sort()):
            full_form = truncation.hyphenstripped() + right_slice.text
            continue
        elif (truncation.is_suffix() and
              right_slice.lexical_sort() == truncation.lexical_sort()):
            full_form = left_slice.text + truncation.hyphenstripped()
            continue
    return full_form


def _substring_handler(comparator, truncation):
    full_form = None
    if truncation.is_prefix():
        substring_rx = re.compile(truncation.lexical_sort()[-3:] + '$')
        for left_slice, right_slice in comparator.slices():
            if substring_rx.search(left_slice.lexical_sort()):
                full_form = truncation.hyphenstripped() + right_slice.text
                continue
    elif truncation.is_suffix():
        substring_rx = re.compile('^' + truncation.lexical_sort()[:3])
        for left_slice, right_slice in comparator.slices():
            if substring_rx.search(right_slice.lexical_sort()):
                full_form = left_slice.text + truncation.hyphenstripped()
                continue
    return full_form


def _plural_handler(comparator, truncation):
    terminator = comparator.terminator()
    full_form = None
    if ((truncation.lemma == '-s' and terminator != 's') or
            (truncation.lemma == '-os' and terminator == 'o') or
            (truncation.lemma == '-as' and terminator == 'a') or
            (truncation.lemma == '-is' and terminator == 'i') or
            (truncation.lemma == '-oes' and terminator == 'e')):
        full_form = comparator.lemma + 's'
    elif truncation.lemma == '-oes' and terminator == 'o':
        full_form = comparator.lemma + 'es'
    elif truncation.lemma == '-i' and terminator == 'o':
        full_form = re.sub(r'o$', 'i', comparator.lemma)
    elif truncation.lemma == '-ies' and terminator == 'y':
        full_form = re.sub(r'y$', 'ies', comparator.lemma)
    elif truncation.lemma == '-a' and re.search(r'um$', comparator.lemma):
        full_form = re.sub(r'um$', 'a', comparator.lemma)
    elif (truncation.lemma == '-man' and
            re.search(r'man$', comparator.lemma)):
        full_form = re.sub(r'man$', 'men', comparator.lemma)
    elif (re.search(r'^-[iyea][sz]$', truncation.lemma) and
            re.search(r'[bdfgklmnptw]', terminator)):
        full_form = comparator.lemma + truncation.hyphenstripped()
    return full_form


def _fuzzy_matcher(comparator, truncation):
    full_form = None

    # iterate through abstract levels 0-7 (different kinds of normalization)
    matches = []
    for i in range(8):
        for slicetuple in comparator.slices():
            left_slice, right_slice = slicetuple
            # Skip slices that split two vowels (e.g. 'appe|ar')
            if (left_slice.ends_with_vowel() and
                right_slice.starts_with_vowel()):
                pass
            elif (truncation.is_prefix() and
                    left_slice.text != truncation.hyphenstripped() and
                    left_slice.abstract(i) == truncation.abstract(i)):
                matches.append(slicetuple)
            elif (truncation.is_suffix() and
                    right_slice.text != truncation.hyphenstripped() and
                    right_slice.abstract(i) == truncation.abstract(i)):
                matches.append(slicetuple)
        if matches:
            break

    if matches:
        if truncation.is_prefix():
            matches.sort(key=lambda x: len(x.right.text), reverse=True)
            matches.sort(key=lambda x: len(x.left.text), reverse=True)
            full_form = truncation.hyphenstripped() + matches[0].right.text
        else:
            matches.sort(key=lambda x: len(x.left.text), reverse=True)
            matches.sort(key=lambda x: len(x.right.text), reverse=True)
            full_form = matches[0].left.text + truncation.hyphenstripped()
    return full_form


class TruncationChecker(object):

    def __init__(self, headword_manager, vf_list):
        self.vf_list = vf_list
        self.headword_manager = headword_manager

    def components(self):
        try:
            return self.__components
        except AttributeError:
            j = self.headword_manager.lemma.replace('-', ' ')
            self.__components = [Lemma(j.split(' ')[0]), Lemma(j.split(' ')[-1])]
            return self.__components

    def check_truncation(self):
        if (not self.headword_manager.is_compound() or
                self.headword_manager.is_affix()):
            return self.vf_list

        for variant_form in self.vf_list:
            if (not variant_form.lemma_manager().is_compound() and
                    not variant_form.is_truncated() and
                    variant_form.lemma_manager().length() <= self.headword_manager.length() - 3):
                match_index = self._match_component(variant_form.lemma_manager())
                if match_index == 0:
                    variant_form.reset_form(variant_form.form + '-')
                elif match_index == 1:
                    variant_form.reset_form('-' + variant_form.form)
        return self.vf_list

    def _match_component(self, truncation):
        match = None
        for word in self.components():
            if (word.prefix() == truncation.prefix() and
                    word.suffix() == truncation.suffix()):
                match = self.components().index(word)
        for word in self.components():
            if (word.initial() == truncation.initial() and
                    word.terminator() == truncation.terminator() and
                    abs(word.length() - truncation.length()) < 3):
                match = self.components().index(word)
        if match is None:
            for word in self.components():
                if ((word.prefix() == truncation.prefix() or
                        word.suffix() == truncation.suffix()) and
                        abs(word.length() - truncation.length()) < 3):
                    match = self.components().index(word)
        return match

