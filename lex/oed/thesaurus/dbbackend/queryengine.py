"""
queryengine

@author: James McCracken
"""

import re
import itertools
from collections import OrderedDict

from sqlalchemy import or_
import sqlalchemy.orm.exc

from lex.oed.thesaurus.dbbackend import thesaurusdbconfig
from lex.oed.thesaurus.dbbackend.models import (ThesClass,
                                                ThesInstance,
                                                Superordinate)
from lex.oed.thesaurus.dbbackend.subjectmapper import SubjectMapper

SESSION = thesaurusdbconfig.SESSION
WORDCLASS_TRANSLATIONS = thesaurusdbconfig.WORDCLASS_TRANSLATIONS
SUBJECT_MAPPER = SubjectMapper()
CLASS_CACHE = OrderedDict()


def taxonomy(**kwargs):
    """
    Return every node in the thesaurus taxonomy
    """
    level = kwargs.get('level')
    if level is None:
        return SESSION.query(ThesClass)
    else:
        return SESSION.query(ThesClass).filter(ThesClass.level <= level)


def get_thesclass(class_id):
    try:
        class_id = int(class_id)
    except (ValueError, TypeError):
        return None
    try:
        return CLASS_CACHE[class_id]
    except KeyError:
        try:
            thesclass = SESSION.query(ThesClass).filter_by(id=class_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            thesclass = None
        CLASS_CACHE[class_id] = thesclass
        if len(CLASS_CACHE) > 100:
            CLASS_CACHE.popitem(last=False)
        return thesclass


def get_superordinate_record(superordinate):
    try:
        record = SESSION.query(Superordinate).filter_by(
                 superordinate=superordinate).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return None
    else:
        return record


def search(**kwargs):
    lemma = kwargs.get('lemma')
    wordclass = kwargs.get('wordclass')
    refentry = kwargs.get('refentry')
    entrynode = kwargs.get('entrynode')
    refid = kwargs.get('refid')
    thes_linked = kwargs.get('thes_linked', False)
    subjects = kwargs.get('subjects', [])

    # 'branches' can be either a list of ThesaurusClass objects,
    #  or a list of thesaurus class IDs
    branches = kwargs.get('branches', [])

    if lemma is not None:
        lemma = re.sub(r'(.)[ -](.)', r'\1\2', lemma)

    if refentry is not None:
        refentry = int(refentry)
    if refid is not None:
        refid = int(refid)
    if entrynode is not None:
        entrynode = int(entrynode)
    if wordclass is not None and wordclass in WORDCLASS_TRANSLATIONS:
        wordclass = WORDCLASS_TRANSLATIONS[wordclass]

    if lemma is not None:
        candidates = SESSION.query(ThesInstance).filter_by(lemma=lemma)
    elif refentry is not None:
        candidates = SESSION.query(ThesInstance).filter_by(refentry=refentry)

    if wordclass is not None:
        candidates2 = candidates.filter_by(wordclass=wordclass)
        if candidates2.count() == 0:
            candidates2 = candidates.filter_by(wordclass='PHR')
        candidates = candidates2

    if refentry is not None:
        candidates = candidates.filter_by(refentry=refentry)

    if refid is not None:
        if kwargs.get('exact_sense') or kwargs.get('exactSense'):
            candidates = candidates.filter_by(refid=refid)
        else:
            # When filtering by refid, allow for the fact that the refid might
            #  point to the *lemma* node, or to a parent sense node, rather
            #  than to sense node itself; hence we also need to check the
            #  refid_alt string
            refid_string = '%,' + str(refid) + ',%'
            candidates = candidates.filter(or_(ThesInstance.refid == refid,
                ThesInstance.refid_alt.like(refid_string)))

    if entrynode is not None:
        candidates = candidates.filter_by(entry_node=entrynode)

    if thes_linked or subjects or branches:
        candidates = candidates.filter(ThesInstance.class_id != None)
    if subjects:
        candidates = [c for c in candidates if SUBJECT_MAPPER.matches(
            c.thesclass, subjects)]
    if branches:
        candidates = [c for c in candidates if
            any([c.thesclass.is_descendant_of(b) for b in branches])]

    # Return query set as list
    if wordclass is not None:
        # Drop instances where the thesaurus class is in the wrong
        #  wordclass
        candidates = [c for c in candidates if c.thesclass is None or
            c.thesclass.wordclass is None or
            c.thesclass.penn_wordclass() == wordclass]
    else:
        candidates = [c for c in candidates]

    return candidates


def search_current(**kwargs):
    """
    Like search, but filters out obsolete results
    """
    instances = search(**kwargs)
    return [i for i in instances if i.size > 0]


def ranked_search(**kwargs):
    """
    Return results of search_current() ordered by rating

    Keyword arguments:

        'include_homographs' True/False (defaults to True): If True, senses
            from all homographs are returned; if False, only senses from
            the largest homograph are returned.

        'current_only' True/False (defaults to False): If True, only
            instances for non-obsolete senses are returned.

        'promote': A sense ID (refid). Instances from the sense with this
            ID will be promoted to the top of the list. (Generally only
            used if the main sense is known in advance.)
    """
    include_homographs = kwargs.get('include_homographs', False)
    promoted_refid = kwargs.get('promote', None)

    if kwargs.get('current_only', False) or kwargs.get('currentOnly', False):
        candidates = search_current(**kwargs)
    else:
        candidates = search(**kwargs)
    if not candidates:
        return []
    else:
        if not include_homographs:
            # Filter to senses from the largest entry only
            candidates.sort(key=lambda i: i.entry_size, reverse=True)
            candidates = [instance for instance in candidates
                          if instance.refentry == candidates[0].refentry]

        # Sort so that the highest-rated is top
        candidates.sort(key=lambda i: i.branch_size(), reverse=True)
        candidates.sort(key=lambda i: i.rating(), reverse=True)

        if candidates and promoted_refid:
            # Move any instances matching the promoted refid
            #  to the top of the list
            promotion = [instance for instance in candidates
                         if instance.refid == promoted_refid]
            candidates = [instance for instance in candidates
                          if instance.refid != promoted_refid]
            # Make sure that promoted instances have a higher rating
            #  than the instance that was previously top
            if candidates:
                for instance in promotion:
                    if instance.rating() <= candidates[0].rating():
                        instance.set_rating(candidates[0].rating() * 1.1)
            # Square the deck
            candidates = promotion + candidates
        return candidates


def highest_ranked(**kwargs):
    """
    Return the highest-ranked result from ranked_search()
    (or None if no results were found).
    """
    try:
        return ranked_search(**kwargs)[0]
    except IndexError:
        return None


def common_ancestor(lemmas, **kwargs):
    candidates_set = []
    for lemma in lemmas:
        local_args = {k: v for k, v in kwargs.items()}
        local_args['lemma'] = lemma
        local_args['current_only'] = True
        candidates = ranked_search(**local_args)
        candidates = [c for c in candidates if c.thesclass is not None]
        # Omit deprecated senses if possible
        candidates = ([c for c in candidates if not c.is_deprecated]
                      or candidates)
        # Restrict to just the best 5 senses
        candidates = candidates[0:5]
        candidates_set.append(candidates)
    return best_fit(candidates_set)


def best_fit(candidates_set):
    possibles = []
    for perm in itertools.product(*candidates_set):
        ancestor_sets = [p.thesclass.ancestors() for p in perm]
        shared_ancestor = None
        for ancestor in ancestor_sets[0]:
            shared_ancestor = True
            for ancestor_set in ancestor_sets[1:]:
                if not ancestor in ancestor_set:
                    shared_ancestor = False
            if shared_ancestor:
                shared_ancestor = ancestor
                break
        if shared_ancestor:
            possibles.append((shared_ancestor, perm))
    possibles.sort(key=lambda ancestor: ancestor[0].branch_size)
    try:
        return possibles[0]
    except IndexError:
        return (None, None)


def cross_reference_target(**kwargs):
    """
    Find the instance or instances corresponding to the sense
    targeted by a cross-reference.

    Returns a 2-ple consisting of:
     -- the list of target instances (ranked by importance);
     -- an int indicating the number of different senses.
    """
    # Try first assuming that the refid value points to a specific sense
    args1 = {k: kwargs.get(k) for k in ('lemma', 'refentry', 'refid')}
    target_senses = ranked_search(**args1)

    # ... or fallback to assuming that the refid is actually pointing to
    #  the entry rather than to a specific sense
    if not target_senses:
        args2 = {k: kwargs.get(k) for k in ('lemma', 'refentry', 'wordclass')}
        args2['entrynode'] = kwargs.get('refid')
        target_senses = ranked_search(**args2)

    return (target_senses, len(set([t.refid for t in target_senses])))
