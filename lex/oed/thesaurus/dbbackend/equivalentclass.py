"""
equivalentclass

equivalent_class()

@author: James McCracken
"""

from sqlalchemy.orm.exc import NoResultFound

from lex.oed.thesaurus.dbbackend import thesaurusdbconfig
from lex.oed.thesaurus.dbbackend.models import ThesClass

SESSION = thesaurusdbconfig.SESSION
WORDCLASS_TRANSLATIONS = thesaurusdbconfig.WORDCLASS_TRANSLATIONS


def equivalent_class(thesclass, target_wordclass):
    """
    For a given thesaurus class under one wordclass, attempt to find
    the nearest equivalent under another wordclass.
    """
    if thesclass is None:
        return None

    if isinstance(thesclass, int):
        try:
            thesclass = SESSION.query(ThesClass).filter_by(id=thesclass).one()
        except NoResultFound:
            return None

    # Find the class immediately above the wordclass parent...
    superclass = thesclass.superclass()
    if superclass is None:
        return None

    # ...then find the child of this that's the right wordclass
    target_branch = child_wordclass_branch(superclass, target_wordclass)


    if target_branch is None:
        # If there is no appropriate wordclass branch, return the branch
        #  immediately *above* wordclass level (as a fallback)
        return superclass

    elif thesclass.level == superclass.level + 1:
        # If thesclass is at wordclass level, then target_branch must
        #   already be at the right level
        return target_branch

    elif thesclass.wordclass == target_branch.wordclass:
        return target_branch

    else:
        # ...otherwise, look for the best match at the next level down
        match = _find_best_match(thesclass, target_branch)
        if match is not None:
            return match
        else:
            return target_branch


def child_wordclass_branch(node, wordclass):
    if wordclass is None:
        return None
    # Find wordclass branches immediately below this parent, where the
    #   wordclass matches the target wordclass. There'll usually only be
    #   one at most, but could be two or more in the case of a verb
    #   (since there are separate branches for trans., intr., and refl.)/
    branches = [c for c in node.children if c.wordclass is not None and
                _wordclass_map(c.wordclass) == _wordclass_map(wordclass)]

    if branches:
        # Sorting is only needed in the case of a verb; this will have
        #   the effect of bringing the trans. branch to the top, which
        #   we're guessing is more likely to be right.
        branches.sort(key=lambda b: b.wordclass, reverse=True)
        return branches[0]
    else:
        return None


def _find_best_match(thesclass, target_branch):
    def trim_tokens(tokens):
        return [t[0:6] for t in tokens]

    match_target = thesclass.ancestor(level=target_branch.level + 1)
    if match_target is not None:
        candidates = []
        match_tokens = set(trim_tokens(match_target.tokens()))
        for c in target_branch.children:
            if set(trim_tokens(c.tokens())) == match_tokens:
                candidates.append(c)
        if len(candidates) == 1:
            return candidates[0]

        candidates = []
        match_tokens_alt = set(trim_tokens(thesclass.tokens()))
        for c in target_branch.children:
            if set(trim_tokens(c.tokens())) == match_tokens_alt:
                candidates.append(c)
        if len(candidates) == 1:
            return candidates[0]

        candidates = []
        for c in target_branch.children:
            # print repr(c.tokens()), repr(match_tokens)
            if match_tokens.intersection(trim_tokens(c.tokens())):
                candidates.append(c)
        if len(candidates) == 1:
            return candidates[0]

    return None


def _wordclass_map(wordclass):
    if wordclass is None or not wordclass:
        return None
    try:
        return WORDCLASS_TRANSLATIONS[wordclass]
    except KeyError:
        try:
            return WORDCLASS_TRANSLATIONS[wordclass.split('(')[0].strip()]
        except KeyError:
            return wordclass
