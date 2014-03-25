

import string

from lxml import etree  # @UnresolvedImport

from lex.entryiterator import EntryIterator
from lex import lexconfig

DEFAULT_INPUT = lexconfig.OEDLATEST_TEXT_DIR
LETTERS = string.ascii_lowercase
PARSER = etree.XMLParser(remove_blank_text=True)


def test_oed_parser():
    for letter in LETTERS:
        print('Collecting vital statistics in %s...' % letter)
        filter_pattern = 'oed_%s.xml' % letter.upper()
        iterator = EntryIterator(dictType='oed',
                                 fixLigatures=True,
                                 fileFilter=filter_pattern,
                                 verbosity=None)
        for entry in iterator.iterate():
            if entry.etymology().etyma():
                print(entry.headword)
                for et in entry.etymology().etyma():
                    print(et)
            #for s1 in entry.s1blocks():
            #    s1.share_quotations()
            #    for i, s in enumerate(s1.senses()):
            #        _process_sense(s, i, len(s1.senses()))


def _process_sense(sense, position, num_senses):
    if sense.definition_manager().cross_references():
        print(sense.lemma)
        print(etree.tostring(sense.definition_manager().node_stripped(), encoding='unicode'))
        for x in sense.definition_manager().cross_references():
            print('\t%s' % x.type)


if __name__ == '__main__':
    test_oed_parser()
