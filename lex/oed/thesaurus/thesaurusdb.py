"""
ThesaurusDB

Front-end to modules in /dbbackend
"""

from lex import lexconfig
from lex.oed.thesaurus.dbbackend import populator
from lex.oed.thesaurus.dbbackend import queryengine
from lex.oed.thesaurus.dbbackend import equivalentclass

TAXONOMY_DIR = lexconfig.HTOED_TAXONOMY_DIR
CONTENT_DIR = lexconfig.HTOED_CONTENT_DIR


def store_taxonomy():
    populator.store_taxonomy(TAXONOMY_DIR)


def store_content():
    populator.store_content(CONTENT_DIR)


def reset():
    populator.reset()


def add_links(instance_tuples):
    populator.add_links(instance_tuples)


def taxonomy(**kwargs):
    return queryengine.taxonomy(**kwargs)


def highest_ranked(**kwargs):
    return queryengine.highest_ranked(**kwargs)


def search(**kwargs):
    return queryengine.search(**kwargs)


def search_current(**kwargs):
    """
    Like search(), but filters out obsolete results
    """
    return queryengine.search_current(**kwargs)


def ranked_search(**kwargs):
    return queryengine.ranked_search(**kwargs)


def distinct_senses(instances):
    """
    Return the number of distinct senses represented by a set of
    instances.
    """
    return len(set([(c.refentry, c.refid) for c in instances]))


def distinct_current_senses(instances):
    """
    Return the number of distinct *current* senses represented by a
    set of instances (ignoring obsolete senses).
    """
    return len(set([(c.refentry, c.refid) for c in instances if c.size > 0]))


def common_ancestor(lemmas, **kwargs):
    return queryengine.common_ancestor(lemmas, **kwargs)


def equivalent_class(class_id, wordclass):
    return equivalentclass.equivalent_class(class_id, wordclass)


def child_wordclass_branch(class_id, wordclass):
    return equivalentclass.child_wordclass_branch(class_id, wordclass)


def get_thesclass(class_id):
    return queryengine.get_thesclass(class_id)


def get_superordinate_record(superordinate):
    return queryengine.get_superordinate_record(superordinate)


def cross_reference_target(**kwargs):
    return queryengine.cross_reference_target(**kwargs)


def remove_redundant_classes(classes):
    """
    Filter an iterable of thesaurus classes so as to remove any
    class which is a direct descendant of another class in the iterable.

    Returns a list (preserving the order of the original iterable).
    """
    # Remove duplicates
    seen = set()
    interim = []
    for thesaurus_class in classes:
        if thesaurus_class.id not in seen:
            interim.append(thesaurus_class)
            seen.add(thesaurus_class.id)
    # Remove descendants
    output = []
    for thesaurus_class in interim:
        if any([thesaurus_class != c and
                thesaurus_class.is_descendant_of(c) for c in interim]):
            pass
        else:
            output.append(thesaurus_class)
    return output


if __name__ == '__main__':
    store_taxonomy()
    store_content()
