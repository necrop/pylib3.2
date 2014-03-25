
import os
from lxml import etree

from .oxmorphentry import OxmorphEntry

def reducer(in_dir, out_dir):

    files = [f for f in os.listdir(in_dir) if f.endswith('.xml')]
    for f in files:
        print "Doing %s..." % f
        out_file = os.path.join(out_dir, f)
        tree = etree.parse(os.path.join(in_dir, f))

        root  = tree.getroot()
        if root.get('sourceTextId'):
            del(root.attrib['sourceTextId'])

        entries = [OxmorphEntry(n) for n in tree.findall('morphEntry')]
        for e in entries:
            e.reduce_to_basic()

        outf = open(out_file, "w")
        outf.write(etree.tostring(tree,
                            xml_declaration=True,
                            pretty_print=True,
                            encoding="UTF-8"))
        outf.close()
