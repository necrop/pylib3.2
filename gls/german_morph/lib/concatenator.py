
import os
import re

class Concatenator(object):

    def __init__(self, **kwargs):
        self.in_dir = kwargs.get('inDir')
        self.out_file = kwargs.get('outFile')
        self.mode = kwargs.get('mode', 'full')

    def concatenate(self):
        files = [f for f in os.listdir(self.in_dir) if f.endswith('.xml')]
        #files = [f for f in files if re.search(r'000[1-5]', f)]

        if self.mode == 'full':
            source_text = ' sourceTextId="Xelda German morphology v3 2012-09-03 + Oxford_GLS_GEDC_DUDE_DDDSI_C001_EXB_full"'
        else:
            source_text = ''
        header = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE morphEntries SYSTEM "OxMorphML-%s.dtd">
<morphEntries language="ger" morphTextId="Oxford_GLS_GEDC_DUDE_DDDSI_Inflected-Forms" version="1.1.1" date="29-05-2013"%s>"""
        header = header % (self.mode, source_text)

        with open(self.out_file, 'w') as outf:
            outf.write(header + '\n')
            for f in files:
                with open(os.path.join(self.in_dir, f), 'r') as fh:
                    for line in fh:
                        line = line.decode('utf8')
                        line = line.strip() + '\n'
                        if line.startswith('<morphEntry'):
                            outf.write(line.encode('utf8'))
            outf.write('</morphEntries>\n')
