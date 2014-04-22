

import string
import re

from lxml import etree  # @UnresolvedImport

from lex.entryiterator import EntryIterator

LETTERS = string.ascii_lowercase
PARSER = etree.XMLParser(remove_blank_text=True)


def test_oed_parser():
    names = []
    for letter in LETTERS:
        print('Collecting names in %s...' % letter)
        filter_pattern = 'oed_%s.xml' % letter.upper()
        iterator = EntryIterator(dictType='oed',
                                 fixLigatures=True,
                                 fileFilter=filter_pattern,
                                 verbosity=None)
        for entry in iterator.iterate():
            if (('personal name' in entry.characteristic_nodes('etymonLanguage') or
                    'place name' in entry.characteristic_nodes('etymonLanguage')) and
                    re.search(r'^([A-Z]|[A-Z]\'[A-Z])[a-z]+$', entry.headword) and
                    not entry.headword.endswith('ism') and
                    not entry.headword.endswith('ist') and
                    not entry.headword.endswith('ian') and
                    not entry.headword.endswith('ite') and
                    entry.primary_wordclass().penn == 'NN'):
                print(entry.headword)
                names.append(entry.headword)
                #for et in entry.etymology().etyma():
                #    print(et)
            #for s1 in entry.s1blocks():
            #    s1.share_quotations()
            #    for i, s in enumerate(s1.senses()):
            #        _process_sense(s, i, len(s1.senses()))

    with open('somenames.txt', 'w') as filehandle:
        for name in names:
            filehandle.write(name + '\n')


def _process_sense(sense, position, num_senses):
    if sense.definition_manager().cross_references():
        print(sense.lemma)
        print(etree.tounicode(sense.definition_manager().node_stripped()))
        for x in sense.definition_manager().cross_references():
            print('\t%s' % x.type)


if __name__ == '__main__':
    test_oed_parser()
