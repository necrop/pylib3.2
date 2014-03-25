
import os
import copy
from lxml import etree

from .oxmorphentry import OxmorphEntry
from .xeldaentry import XeldaEntry

class PluralFixer(object):

    def __init__(self, in_dir, out_dir, xelda_dir):
        self.in_dir = in_dir
        self.out_dir = out_dir
        self.xelda_dir = xelda_dir

    def process(self):
        self.load_index()
        self.log = []
        self.counts = {'entriesAll': 0, 'entriesWithPlural': 0}

        files = [f for f in os.listdir(self.in_dir) if f.endswith('.xml')]
        for f in files:
            print "Doing %s..." % f
            out_file = os.path.join(self.out_dir, f)

            # Parse the OxMorph XML file
            tree = etree.parse(os.path.join(self.in_dir, f))

            # load all entries that have more than one inflection unit
            entries = [OxmorphEntry(n) for n in tree.findall('morphEntry')]
            entries = [e for e in entries if len(e.forms()) > 1]
            self.counts['entriesAll'] += len(entries)

            # check which already have plurals (and can therefore be ignored)
            j = len(entries)
            entries = [e for e in entries if not e.has_plurals()]
            self.counts['entriesWithPlural'] += j - len(entries)

            # Poll the entries to determine which Xelda files we're going
            # to have to open in order to find corresponding entries
            xelda = {}
            for e in entries:
                xelda[e.source_id()] = None
            xelda_files = set()
            for id in xelda.keys():
                if id in self.xelda_index:
                    xelda_files.add(self.xelda_index[id])

            # Load corresponding Xelda entries
            for xfile_num in xelda_files:
                xfile = os.path.join(self.xelda_dir, '%0.4d.xml'% xfile_num)
                xelda_tree = etree.parse(xfile)
                xelda_entries = [XeldaEntry(n) for n in xelda_tree.findall('e')]
                for e in xelda_entries:
                    if e.id() in xelda:
                        xelda[e.id()] = e

            for e in [e for e in entries if e.wordclass() == 'adjective']:
                if xelda[e.source_id()] is not None:
                    self._compare_entries(e, xelda[e.source_id()])

            outf = open(out_file, "w")
            outf.write(etree.tostring(tree,
                                xml_declaration=True,
                                pretty_print=True,
                                encoding="UTF-8"))
            outf.close()

        # write log file to record the entries that have been changed
        self.write_log()
        print 'Corrected %d / %d entries' % (len(self.log), self.counts['entriesAll'])
        print '%d entries already had plurals.' % self.counts['entriesWithPlural']

    def _compare_entries(self, e, x):
        if [d for d in x.declensions() if d.number == 'plural']:
            #print '==============================================='
            #print repr(e.lemma()), e.id()
            #for f in e.forms():
            #    print '\t', repr(f.signature())

            plurals = [d for d in x.declensions() if d.number == 'plural']
            singulars = [d for d in x.declensions() if d.number == 'singular']
            #for d in plurals:
            #    print "\t\t", repr(d.signature())

            used = set()
            for f in e.forms():
                for i, d in enumerate(plurals):
                    if (not i in used and
                        d.wordform == f.wordform() and
                        f.number == 'singular' and
                        self._is_close_match(f, d, e.wordclass())):

                        # If this form can *only* be plural, just switch the
                        # @number attribute; if it can be *both* singular and
                        # plural, add the plural version as a new node
                        if self._is_also_singular(f, singulars, e.wordclass()):
                            newnode = copy.deepcopy(f.node)
                            newnode.set('number', 'plural')
                            e.forms_wrapper().append(newnode)
                            print "\t\t", repr(f.signature()), repr(d.signature())
                        else:
                            f.node.set('number', 'plural')
                        #print "\t\t", repr(f.signature()), repr(d.signature())
                        used.add(i)
                        break
            e.sort_forms()

            # Track the fact that this entry has been changed
            self.log.append((e.lemma(), e.id()))

    def _is_close_match(self, oxmorph_unit, xelda_declension, wordclass):
        if (wordclass == 'noun' and
            oxmorph_unit.case == xelda_declension.case):
            return True
        if (wordclass == 'adjective' and
            oxmorph_unit.case == xelda_declension.case and
            oxmorph_unit.gender == xelda_declension.gender and
            oxmorph_unit.degree == xelda_declension.degree and
            oxmorph_unit.inflectionType == xelda_declension.inflectionType):
            return True
        if (wordclass == 'verb' and
            oxmorph_unit.mood == xelda_declension.mood and
            oxmorph_unit.tense == xelda_declension.tense and
            oxmorph_unit.person == xelda_declension.person and
            oxmorph_unit.nonFinType == xelda_declension.nonFinType):
            return True
        return False

    def _is_also_singular(self, oxmorph_unit, xelda_singulars, wordclass):
        if [d for d in xelda_singulars if d.wordform == oxmorph_unit.wordform()
            and self._is_close_match(oxmorph_unit, d, wordclass)]:
            return True
        else:
            return False


    def load_index(self):
        self.xelda_index = {}
        index_file = os.path.join(self.xelda_dir, "index.txt")
        with open(index_file, "r") as fh:
            for l in fh:
                id, filenum = l.strip().split("\t")
                self.xelda_index[id] = int(filenum)

    def write_log(self):
        with open(os.path.join(self.out_dir, "corrected-number.txt"), 'w') as fh:
            fh.write('# Entries corrected by changing plural to singular,\n# based on Xelda data.\n')
            fh.write('# %d/%d entries\n' % (len(self.log), self.counts['entriesAll']))
            for l in self.log:
                line = "%s\t%s\n" % (l[0], l[1],)
                fh.write(line.encode('utf8'))
