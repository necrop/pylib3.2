"""
VitalStatisticsWriter -- store vital stats for OED entries as XML documents
VitalStatisticsCache -- retrieve vital stats from XML store

@author: James McCracken
"""

import os
import string
from collections import namedtuple

from lxml import etree  # @UnresolvedImport

from lex.entryiterator import EntryIterator
from lex import lexconfig

DEFAULT_INPUT = lexconfig.OEDLATEST_TEXT_DIR
DEFAULT_OUTPUT = lexconfig.OED_VITALSTATS_DIR
DEFAULT_LINKS = lexconfig.OED_LINKS_DIR

LETTERS = string.ascii_lowercase
PARSER = etree.XMLParser(remove_blank_text=True)


class VitalStatisticsWriter(object):

    """
    Store vital statistics for OED entries as XML documents.
    """

    def __init__(self, **kwargs):
        self.oed_dir = kwargs.get('oedDir') or DEFAULT_INPUT
        self.out_dir = kwargs.get('outDir') or DEFAULT_OUTPUT

    def store_vital_statistics(self):
        for letter in LETTERS:
            print('Collecting vital statistics in %s...' % letter)
            filter_pattern = 'oed_%s.xml' % letter.upper()
            iterator = EntryIterator(path=self.oed_dir,
                                     dictType='oed',
                                     fixLigatures=True,
                                     fileFilter=filter_pattern,
                                     verbosity=None)

            self.doc = etree.Element('entries')
            for entry in iterator.iterate():
                entry_node = etree.SubElement(
                    self.doc,
                    'e',
                    xrid=entry.id,
                    quotations=str(entry.num_quotations(force_recount=True)),
                    weightedSize='%0.2g' % entry.weighted_size(),
                    obsolete=str(entry.is_marked_obsolete()),
                    revised=str(entry.is_revised),
                    firstDate=str(entry.date().start),
                    lastDate=str(entry.date().end)
                )
                label_node = etree.SubElement(entry_node, 'label')
                label_node.text = entry.label()
                hw_node = etree.SubElement(entry_node, 'headword')
                hw_node.text = entry.headword

                if entry.header() is not None:
                    header_node = etree.SubElement(entry_node, 'header')
                    header_node.text = entry.header()

                etym_node = etree.SubElement(entry_node, 'etyma')
                for etymon in entry.etymology().etyma():
                    if etymon.type() == 'cross-reference':
                        etymon_node = etree.SubElement(etym_node, 'etymon')
                        etymon_node.set('xrid', str(etymon.refentry()))
                        etymon_node.text = etymon.lemma

                lang_node = etree.SubElement(entry_node, 'language')
                language = (entry.characteristic_first('etymonLanguage') or
                            entry.characteristic_first('sourceLanguage'))
                if language:
                    lang_node.text = language

                def_node = etree.SubElement(entry_node, 'def')
                definition = entry.definition(length=100, current=True)
                if definition:
                    def_node.text = definition

                if entry.senses():
                    for label_type in ('subject', 'region', 'usage'):
                        label_text = entry.senses()[0].characteristic_first(label_type)
                        label_text = label_text.split('/')[-1]
                        if label_text:
                            label_node = etree.SubElement(entry_node, label_type)
                            label_node.text = label_text

            self._write_output(letter)

    def _write_output(self, letter):
        with open(os.path.join(self.out_dir, letter + '.xml'), 'w') as filehandle:
            filehandle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            filehandle.write(etree.tounicode(self.doc,
                                             pretty_print=True))


class VitalStatisticsCache(object):

    """
    Cache vital statistics for OED entries by reading in
    from XML store.
    """

    entries = []
    lookup = {}
    EntryData = namedtuple('EntryData', ['id', 'label', 'headword', 'header',
                'first_date', 'last_date', 'quotations', 'weighted_size',
                'obsolete', 'revised', 'subject', 'region',
                'usage', 'etyma', 'language', 'indirect_language',
                'definition', 'ode', 'noad', ])

    def __init__(self, **kwargs):
        self.vs_dir = kwargs.get('vitalStatisticsDir') or DEFAULT_OUTPUT
        self.links_dir = kwargs.get('linksDir') or DEFAULT_LINKS
        if not VitalStatisticsCache.entries:
            self.load_cache()

    def find(self, entry_id, field=None):
        entry_id = int(entry_id)
        try:
            entry = VitalStatisticsCache.lookup[entry_id]
        except KeyError:
            return None
        else:
            if field is None:
                return entry
            else:
                dictified = entry._asdict()
                try:
                    return dictified[field]
                except KeyError:
                    return None

    def load_cache(self):
        self._load_language_bases()
        self._load_links()
        for letter in LETTERS:
            fname = os.path.join(self.vs_dir, letter + '.xml')
            tree = etree.parse(fname, PARSER)
            for entry in tree.findall('e'):
                VitalStatisticsCache.entries.append(self._parse_entry(entry))

        for entry in VitalStatisticsCache.entries:
            VitalStatisticsCache.lookup[int(entry[0])] = entry

        del self.language_bases
        del self.redirects
        del self.links

    def _parse_entry(self, entry):
        entry_id = int(entry.get('xrid'))
        if (entry.get('obsolete') is not None and
            entry.get('obsolete').lower() == 'true'):
            obsolete = True
        else:
            obsolete = False

        if (entry.get('revised') is not None and
            entry.get('revised').lower() == 'true'):
            revised = True
        else:
            revised = False

        etyma = [(etnode.text, int(etnode.get('xrid') or 0))
                 for etnode in entry.findall('./etyma/etymon')]

        language = entry.findtext('./language') or ''
        target_id = _first_complete_etymon(entry)
        indirect_language = (self._indirect_language(target_id) or
                             language or None)

        try:
            ode, noad = self.links[entry_id]
        except KeyError:
            ode, noad = (None, None)

        return self.EntryData(
            entry_id,
            entry.findtext('./label') or '',
            entry.findtext('./headword') or '',
            entry.findtext('./header') or '',
            int(entry.get('firstDate') or 0),
            int(entry.get('lastDate') or 0),
            int(entry.get('quotations') or 0),
            float(entry.get('weightedSize') or 0),
            obsolete,
            revised,
            entry.findtext('./subject') or '',
            entry.findtext('./region') or '',
            entry.findtext('./usage') or '',
            etyma,
            language,
            indirect_language,
            entry.findtext('./def') or '',
            ode,
            noad,
        )

    def _indirect_language(self, target_id, strict=True):
        for _ in range(5):
            if target_id in self.language_bases:
                return self.language_bases[target_id]
            elif target_id in self.redirects:
                target_id = self.redirects[target_id]
            else:
                target_id = None
        return None

    def _load_links(self):
        self.links = {}
        if self.links_dir is not None:
            for letter in LETTERS:
                fname = os.path.join(self.links_dir, letter + '.xml')
                tree = etree.parse(fname, PARSER)
                for entry in tree.findall('e'):
                    xrid = int(entry.get('xrid'))
                    ode = entry.find('./links').get('ode')
                    noad = entry.find('./links').get('noad')
                    self.links[xrid] = (ode, noad)

    def _load_language_bases(self):
        languages = {}
        redirects = {}
        for letter in LETTERS:
            fname = os.path.join(self.vs_dir, letter + '.xml')
            tree = etree.parse(fname, PARSER)
            for entry in tree.findall('e'):
                id = int(entry.get('xrid'))
                if not _first_complete_etymon(entry):
                    ltext = entry.findtext('./language')
                    if ltext is not None:
                        languages[id] = ltext
                else:
                    redirects[id] = _first_complete_etymon(entry)
        self.language_bases = languages
        self.redirects = redirects


def _first_complete_etymon(entry_node):
    etyma = [(etymon.text, int(etymon.get('xrid'))) for etymon
              in entry_node.findall('./etyma/etymon')]
    etyma_targets = [etymon[1] for etymon in etyma if not etymon[0] or
                     not(etymon[0].startswith('-') or etymon[0].endswith('-'))]
    if etyma_targets:
        return etyma_targets[0]
    else:
        return None


if __name__ == '__main__':
    VitalStatisticsWriter().store_vital_statistics()
