"""
populator - set of functions for populating the HTOED database tables:

store_taxonomy()
store_content()
store_superordinates()
reset()
add_links()

@author: James McCracken
"""

import string
import os
import csv

from lex.oed.thesaurus.dbbackend import thesaurusdbconfig
from lex.oed.thesaurus.contentiterator import ContentIterator
from lex.oed.thesaurus.taxonomymanager import TaxonomyManager
from lex.oed.thesaurus.dbbackend.models import (ThesClass,
                                                ThesInstance,
                                                Superordinate,
                                                SuperordinateBranch)

DB_ENGINE = thesaurusdbconfig.ENGINE
DB_SESSION = thesaurusdbconfig.SESSION
WORDCLASS_MAP = thesaurusdbconfig.WORDCLASS_TRANSLATIONS


def store_taxonomy(tax_dir):
    ThesInstance.__table__.drop(DB_ENGINE, checkfirst=True)
    SuperordinateBranch.__table__.drop(DB_ENGINE, checkfirst=True)
    Superordinate.__table__.drop(DB_ENGINE, checkfirst=True)
    ThesClass.__table__.drop(DB_ENGINE, checkfirst=True)
    ThesClass.__table__.create(DB_ENGINE, checkfirst=True)

    tree_manager = TaxonomyManager(dir=tax_dir, lazy=True, verbosity=None)

    # Check that the correct attributes are in place
    for thesclass in tree_manager.classes[0:100]:
        if thesclass.size(branch=True) and thesclass.size(branch=False):
            break
    else:
        print('Thesaurus data has no size attributes; exiting.')
        exit()

    for level in range(1, 20):
        classes = [c for c in tree_manager.classes if c.level() == level]
        print(level, len(classes))
        buffer_size = 0
        for thesaurus_class in classes:
            DB_SESSION.add(ThesClass(thesaurus_class))
            buffer_size += 1
            if buffer_size > 100:
                DB_SESSION.commit()
                buffer_size = 0
        DB_SESSION.commit()


def store_content(content_dir):
    ThesInstance.__table__.drop(DB_ENGINE, checkfirst=True)
    ThesInstance.__table__.create(DB_ENGINE, checkfirst=True)

    # Store the lemmas for each thesaurus instance (using
    #  refentry+refid+classid as the identifier)
    lemmas = _cache_thesaurus_lemmas(content_dir)

    from lex.entryiterator import EntryIterator
    iterator = EntryIterator(dictType='oed',
                             fixLigatures=True,
                             verbosity='low')
    buffer_size = 0
    for entry in iterator.iterate():
        entry.check_revised_status()
        for block in entry.s1blocks():
            block.share_quotations()
            entry_size = block.weighted_size()
            senses = [s for s in block.senses() if not s.is_xref_sense()]
            senses.sort(key=_sortable_date)
            for i, s in enumerate(senses):
                records = _prepare_records(s, entry.id, entry.node_id(),
                                           lemmas, i + 1, entry_size,)
                for r in records:
                    DB_SESSION.add(r)
                    buffer_size += 1
        for s in [s for s in entry.senses() if not s.is_in_sensesect()
                  and not s.is_xref_sense()]:
            records = _prepare_records(s, entry.id, entry.node_id(),
                                       lemmas, 5, 1.0,)
            for r in records:
                DB_SESSION.add(r)
                buffer_size += 1

        if buffer_size > 1000:
            DB_SESSION.commit()
            buffer_size = 0
    DB_SESSION.commit()


def store_superordinates(superordinates_dir):
    SuperordinateBranch.__table__.drop(DB_ENGINE, checkfirst=True)
    Superordinate.__table__.drop(DB_ENGINE, checkfirst=True)
    Superordinate.__table__.create(DB_ENGINE, checkfirst=True)
    SuperordinateBranch.__table__.create(DB_ENGINE, checkfirst=True)
    for letter in string.ascii_lowercase:
        print('\tPopulating superordinate database for %s...' % letter)
        FILEPATH = os.path.join(superordinates_dir, letter + '.csv')
        with open(FILEPATH, 'r') as filehandle:
            csvreader = csv.reader(filehandle)
            for row in csvreader:
                superordinate = row.pop(0)
                total = int(row.pop(0))
                record = Superordinate(superordinate=superordinate,
                                       senses=total)

                branches = []
                while row:
                    class_id = int(row.pop(0))
                    probability = float(row.pop(0))
                    branches.append(SuperordinateBranch(class_id=class_id,
                                                        probability=probability))
                if branches:
                    record.branches = branches

                DB_SESSION.add(record)
        DB_SESSION.commit()


def reset():
    """
    Remove all provisional links, and reset 'provisional' flag to False
    """
    instances = DB_SESSION.query(ThesInstance).filter_by(is_provisional=True)
    buffer_size = 0
    for i in instances:
        i.class_id = None
        i.is_provisional = False
        DB_SESSION.add(i)
        buffer_size += 1

        if buffer_size > 1000:
            DB_SESSION.commit()
            buffer_size = 0
    DB_SESSION.commit()


def add_links(instance_tuples):
    """
    Add provisional thesaurus links to a set of instances
    Argument is a list of 2-ples in the form (instance, class_id)
    """
    for instance, class_id in instance_tuples:
        instance.class_id = class_id
        instance.is_provisional = True
        DB_SESSION.add(instance)
    DB_SESSION.commit()


def _cache_thesaurus_lemmas(content_dir):
    lemmas = {}
    ci = ContentIterator(path=content_dir, fixLigatures=True, verbosity='low')
    for c in ci.iterate():
        if c.instances():
            if c.wordclass() is not None and c.wordclass() in WORDCLASS_MAP:
                wordclass = WORDCLASS_MAP[c.wordclass()]
            else:
                wordclass = None
            for i in c.instances():
                identifier = '%d_%d_%d' % (int(i.refentry()),
                                           int(i.refid()),
                                           int(c.id()))
                if not identifier in lemmas:
                    lemmas[identifier] = (i.lemma(), wordclass)
    return lemmas


def _prepare_records(sense, entry_id, entry_lexid, lemmas, count, entry_size):
    sense_size = sense.weighted_size(revised=sense.is_revised)

    if sense.date().end and sense.date().end < 1750:
        sense_size *= 0.5
    elif sense.date().end and sense.date().end < 1600:
        sense_size = 0
    if sense.date().start and sense.date().start > 1900:
        sense_size *= 0.5
    elif sense.date().start and sense.date().start > 1850:
        sense_size *= 0.7
    elif sense.date().start and sense.date().start > 1800:
        sense_size *= 0.8
    if sense.is_current_sense():
        sense_size += 5
    # Downscore supplement senses in unrevised entries
    if sense.is_supplement_sense():
        sense_size *= 0.5
    if _is_heavily_deprecated(sense):
        sense_size *= 0.5
    if _is_deprecated(sense):
        sense_size *= 0.8

    refid_alt = []
    if ((sense.is_subentry() or sense.is_subentry_like()) and
            sense.lemma_id() is not None):
        refid_alt.append(int(sense.lemma_id()))
    for a in sense.ancestors():
        if a.tag in ('s6', 's4', 's1'):
            refid_alt.append(int(a.lexid))
    for subdef in sense.node.findall('.//subDef'):
        if subdef.get('eid'):
            refid_alt.append(int(subdef.get('eid')))
    refid_alt = ''.join([',%d,' % id for id in refid_alt]) or None
    if refid_alt is not None:
        refid_alt = refid_alt.replace(',,', ',')[0:80]

    sense_data = {
        'lemma': sense.lemma,
        'wordclass': sense.primary_wordclass().penn,
        'refentry': int(entry_id),
        'refid': int(sense.node_id()),
        'refid_alt': refid_alt,
        'entry_node': int(entry_lexid),
        'size': sense_size,
        'is_deprecated': _is_deprecated(sense),
        'chronorder': count,
        'entry_size': entry_size,
        'start_year': sense.date().start or None,
        'end_year': sense.date().end or None,
        'subentry_type': sense.subentry_type()
    }

    records = []
    if sense.thesaurus_nodes():
        for n in [int(n) for n in sense.thesaurus_nodes()]:
            record_data = {k: v for k, v in sense_data.items()}
            record_data['class_id'] = n
            # Adjust the lemma to match the form given in the
            #  thesaurus class
            identifier = '%d_%d_%d' % (record_data['refentry'],
                                       record_data['refid'],
                                       record_data['class_id'])
            if identifier in lemmas:
                record_data['lemma'] = lemmas[identifier][0]
                if lemmas[identifier][1] is not None:
                    record_data['wordclass'] = lemmas[identifier][1]
                del(lemmas[identifier])
            records.append(ThesInstance(record_data))
    else:
        record_data = {k: v for k, v in sense_data.items()}
        record_data['class_id'] = None
        records.append(ThesInstance(record_data))
    return records


def _is_heavily_deprecated(sense):
    if (sense.has_rare_indicator() or
            sense.is_grammatically_atypical() or
            sense.has_phrasal_indicator()):
        return True
    else:
        return False


def _is_deprecated(sense):
    if (sense.characteristic_list('usage') or
            sense.is_regional() or
            sense.is_figurative()):
        return True
    else:
        return False


def _sortable_date(sense):
    year = None
    try:
        sense.shared
    except AttributeError:
        pass
    else:
        if sense.shared and sense.quotations():
            for q in sense.quotations():
                if not q.is_bracketed():
                    year = q.year()
                    break
    if year is None:
        year = sense.date().start
    if year is None or year < 500:
        return 2000
    elif year < 1100:
        return 1100
    else:
        return year
