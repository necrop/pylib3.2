
import os
from lxml import etree

from .oxmorphentry import OxmorphEntry
from .oxfordformsmanager import OxfordFormsManager


class MissingForms(object):

    def __init__(self, in_dir, out_dir, oxford_forms_dir):
        self.in_dir = in_dir
        self.out_dir = out_dir
        self.oxford_forms_dir = oxford_forms_dir

    def process(self):
        self.log = []
        ofs = OxfordFormsManager(self.oxford_forms_dir)

        files = [f for f in os.listdir(self.in_dir) if f.endswith('.xml')]
        for f in files:
            print "Doing %s..." % f
            out_file = os.path.join(self.out_dir, f)
            tree = etree.parse(os.path.join(self.in_dir, f))

            # load all the entries
            entries = [OxmorphEntry(n) for n in tree.findall('morphEntry')]
            for e in entries:
                oxform = ofs.retrieve(e.lemma(), e.wordclass())
                if oxform is not None:
                    self.compare(e, oxform)

            outf = open(out_file, "w")
            outf.write(etree.tostring(tree,
                                xml_declaration=True,
                                pretty_print=True,
                                encoding="UTF-8"))
            outf.close()
        self.write_log()

    def compare(self, e, oxform):
        # filter out multi-word forms from the Oxford inflections
        oxinflections = [i for i in oxform.inflections if i.is_viable()]

        # Build a set of signatures for all the existing inflections
        existing = set()
        for i in e.inflections():
            existing.add(i.signature())

        # Check for any signatures among the Oxford forms that aren't
        #  already covered
        additions = []
        for i in oxinflections:
            if not i.signature() in existing:
                additions.append(i)

        if additions:
            # Remove existing inflection, if it's just a single dummy
            # inflection unit, as in e.g. Ahnin
            if len(e.inflections()) < 2:
                for f in e.inflections():
                    f.node.getparent().remove(f.node)
            # Append XMl nodes for each new form
            for i in additions:
                e.forms_wrapper().append(i.xml())
            # sort
            e.sort_forms()

            # Track the fact that this entry has been changed
            self.log.append((e.lemma(), e.wordclass(), e.id()))

            #print "\n====================================================="
            #print repr(e.lemma()), e.wordclass(), repr(oxform.filepath)
            #for i in e.inflections():
            #    print "\t" + repr(i.signature())
            #for i in additions:
            #    print "\t\t" + repr(i.signature())

    def write_log(self):
        with open(os.path.join(self.out_dir, "forms-added.txt"), 'w') as fh:
            fh.write('# Entries to which forms have been added from the OxfordForms data.\n')
            for l in self.log:
                line = "%s\t%s\t%s\n" % (l[0], l[1], l[2])
                fh.write(line.encode('utf8'))
