"""
SpellingConverter -- conversion between US and UK spellings.

@author: James McCracken
"""

import os
import re

from lxml import etree  # @UnresolvedImport

from regexcompiler import ReplacementListCompiler
from lex import lexconfig
from lex.inflections.singularizer import Singularizer
from lex.inflections.inflection import Inflection

ODE_DISTILLED = os .path.join(lexconfig.ODO_DIR, 'ode_distilled.xml')
CASECHECK = re.compile(r'^[A-Z][a-z -]+$')
VERB_ENDINGS = re.compile(r'^(.*)(ed|ing)$')
SPLITTER = ReplacementListCompiler((
    (r'(.)(\'s )', r'\1#\2'),
    (r'(.)([ _.;:!?-])(.)', r'\1#\2#\3'),
    ('(.)(\u2013|\u2014)(.)', r'\1#\2#\3'),
    (r'##+', r'#'),))
LOOKUP_FILE = os.path.join(os.path.dirname(__file__), 'data', 'us_mappings.txt')
SINGULARIZER = Singularizer()
INFLECTOR = Inflection()


class SpellingConverter(object):

    """
    Class for converting between US and UK spellings
    """

    mappings = {}

    def __init__(self):
        pass

    def us_spelling(self, text):
        """
        Return the US-spelling equivalent of UK-spelled text.

        This is mainly intended for handling dictionary lemmas
        (single words or phrases). It should also be able to handle
        most inflected words, and to handle longer pieces of
        running text; but this is not guaranteed -- see limitations
        of the _lazy_tokenize() function.
        """
        lemma_us = self._translate(text)
        if lemma_us is not None:
            return lemma_us
        elif re.search(r'^[a-zA-Z]+$', text):
            return text
        else:
            components = _lazy_tokenize(text)
            components_us = []
            for token in components:
                if re.search(r'[a-zA-Z]', token):
                    token_us = self._translate(token) or token
                else:
                    token_us = token
                components_us.append(token_us)
            return _lazy_untokenize(components_us)

    convert = us_spelling

    def _translate(self, token):
        """
        Convert a single UK token to its US equivalent.

        The token may be a base lemma form, or may be a plural or inflection.

        If no conversion is found, the token is returned unchanged.
        """
        token_us = self._lookup_lemma(token)

        # The token may be a plural; so we try reducing it to its
        #  singular form, then we see if there's a US version
        #  of that.
        if (token_us is None and
            token.endswith('s') and
            not token.endswith('ss')):
            lemma = SINGULARIZER.singularize(token)
            if lemma != token:
                lemma_us = self._lookup_lemma(lemma)
                if lemma_us is not None:
                    # Turn it back into a plural
                    if token == lemma + 's':
                        token_us = lemma_us + 's'
                    elif token == lemma + 'es':
                        token_us = lemma_us + 'es'
                    else:
                        token_us = INFLECTOR.pluralize(lemma_us)

        # The token may be a verbal -ed or -ing form; so we remove
        #  the ending, then we see if there's a US version of the base
        if token_us is None and len(token) >= 8 and VERB_ENDINGS.search(token):
            match = VERB_ENDINGS.search(token)
            lemma_us = self._lookup_lemma(match.group(1))
            if lemma_us is not None:
                token_us = lemma_us + match.group(2)

        return token_us

    def _lookup_lemma(self, lemma):
        """
        Convert a single UK lemma to its US equivalent,
        using the mapping table.

        Returns None if no conversion is found in the mapping table.
        """
        if not SpellingConverter.mappings:
            SpellingConverter.mappings = _load_mappings()
        if lemma in SpellingConverter.mappings:
            return SpellingConverter.mappings[lemma]
        elif CASECHECK.search(lemma):
            lemma_lc = lemma.lower()
            if lemma_lc in SpellingConverter.mappings:
                return SpellingConverter.mappings[lemma_lc].capitalize()
        return None


def _load_mappings():
    """
    Load the mappings file into memory, for use in lemma lookups.
    """
    mappings = {}
    with open(LOOKUP_FILE) as filehandle:
        for line in filehandle:
            uk_form, us_form = line.strip().split('\t')
            mappings[uk_form] = us_form
    return mappings

def _lazy_tokenize(text):
    """
    Tokenize the text, so that each token can be converted individually.

    Spaces are retained as individual tokens, so that the text
    can be reconstructed later using _lazy_untokenize().

    Note that this is a quick and crude attempt at tokenization; it's
    sufficient to handle things like space- and hyphen-separated
    compounds, but not really good enough for real-world continuous text. 
    """
    # mask actual octothorpes
    text = text.replace('#', '#ZHASHZ#')
    # Separate tokens with octothorpe characters ('#')
    octothorped = SPLITTER.edit(' ' + text + ' ')
    octothorped = octothorped.strip(' #')
    return octothorped.split('#')

def _lazy_untokenize(components):
    """
    Reverse the tokenization process carried out by _lazy_tokenize().
    This should return the text to its original form.
    """
    return ''.join(components).replace('ZHASHZ', '#').strip()



def generate_list(src):
    conversions = []
    tree = etree.parse(src)
    for entry in tree.findall('.//e'):
        hw_nodes = entry.findall('./hw')
        if (len(hw_nodes) == 2 and
            hw_nodes[0].get('locale') == 'uk' and
            hw_nodes[1].get('locale') == 'us'):
            conversions.append((hw_nodes[0].text, hw_nodes[1].text))

    with open(LOOKUP_FILE, 'w') as filehandle:
        for uk_form, us_form in conversions:
            filehandle.write('%s\t%s\n' % (uk_form, us_form))


if __name__ == '__main__':
    generate_list(ODE_DISTILLED)
