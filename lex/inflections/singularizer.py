#-------------------------------------------------------------------------------
# Name: Singularizer
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import re
import os

from regexcompiler import ReplacementListCompiler

UPCASE_PATTERN = re.compile(r'^[A-Z][a-z -]+$')

IRREGULAR_PATTERN = ReplacementListCompiler((
    (r'theses$', r'thesis'),
    (r'^men$', r'man'),
    (r'([^m])men$', r'\1man'),
    (r'people$', r'person'),
    (r'children$', r'child'),
    (r'teeth$', r'tooth'),
    (r'geese$', r'goose'),
    (r'feet$', r'foot'),
    (r'sheep$', r'sheep'),
    (r'mice$', r'mouse'),
    (r'zoa$', r'zoon'),
    (r'eaux$', r'eau'),))

REGULAR_PATTERN = ReplacementListCompiler((
    (r'(.[bcdfghklmnprtvw]|que|ee|[aeo]y)s$', r'\1'),
    (r'([aeiou][bcdfgklmnprtvwyz]e|ue)s$', r'\1'),
    (r'(ness|glass|kiss|box|sh|tch|dress)es$', r'\1'),
    (r'(house|shoe|.nce)s$', r'\1'),
    (r'(.[bcdfgkpty]le)s$', r'\1'),
    (r'(crac|log|tom|berr|[ai]lit|graph|iet)ies$', r'\1y'),))

UNCHANGED_PATTERN = (
    re.compile(r'ss$'),
    re.compile(r'us$'),
    re.compile(r'series$'),
    re.compile(r'species$'),
    re.compile(r'[ey]sis$'),
    re.compile(r'itis$'),)



class Singularizer(object):

    """
    Engine to manage turning plural nouns into singular.
    """

    singulars = set()
    plural_stems = {}

    def __init__(self):
        pass

    def singularize(self, word):
        if not Singularizer.singulars:
            self._load_lookups()

        if UPCASE_PATTERN.search(word):
            self._token = word[0].lower() + word[1:]
            self._case_changed = True
        else:
            self._token = word
            self._case_changed = False

        singular = self._stem()
        if self._case_changed:
            return singular[0].upper() + singular[1:]
        else:
            return singular

    def _stem(self):
        if self._token in Singularizer.singulars:
            return self._token
        elif self._token in Singularizer.plural_stems:
            return Singularizer.plural_stems[self._token]

        for sep in ('-', ' '):
            parts = list(self._token.split(sep))
            if len(parts) > 1 and parts[-1] in Singularizer.singulars:
                return self._token
            elif len(parts) > 1 and parts[-1] in Singularizer.plural_stems:
                parts[-1] = Singularizer.plural_stems[parts[-1]]
                return sep.join(parts)

        if re.search(r'[^s]s$', self._token):
            for k in UNCHANGED_PATTERN:
                if k.search(self._token):
                    return self._token
            j = IRREGULAR_PATTERN.edit_once(self._token)
            if j != self._token:
                return j
            j = REGULAR_PATTERN.edit_once(self._token)
            if j != self._token:
                return j
            # At this point we've failed to singularize it; maybe it's
            # not a plural at all; so we return it unchanged.
            return self._token

        else:
            return self._token

    def _load_lookups(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data')

        with open(os.path.join(data_dir, 'singulars.txt'),
                  encoding='utf-8') as filehandle:
            for line in filehandle:
                line = line.strip()
                if line and not line.startswith('#'):
                    Singularizer.singulars.add(line)

        with open(os.path.join(data_dir, 'plural_stems.txt'),
                  encoding='utf-8') as filehandle:
            for line in filehandle:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('\t')
                    Singularizer.plural_stems[parts[0]] = parts[1]
