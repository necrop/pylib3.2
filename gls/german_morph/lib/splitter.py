
import os

class Splitter(object):

    def __init__(self, in_file, out_dir, **kwargs):
        self.in_file = in_file
        self.out_dir = out_dir
        self.buffer = []
        self.buffer_size = kwargs.get('size', 1000)
        self.counter = 0
        self.line_num = 0
        self.header_text = 0
        self.tail_text = None

    def set_header(self, h):
        self.header_text = h

    def set_tail(self, t):
        self.tail_text = t

    def purge_buffer(self):
        self.buffer.append(self.tail_text)
        self.counter += 1
        print 'Writing file #%d... (line #%d)' % (self.counter, self.line_num)
        out_file = os.path.join(self.out_dir, '%0.4d.xml' % self.counter)
        with open(out_file, 'w') as fh:
            for l in self.buffer:
                if l:
                    fh.write(l.encode('utf8') + '\n')
        self.buffer = []
        self.buffer.append(self.header_text)

    def clear_output(self):
        files = os.listdir(self.out_dir)
        for f in files:
            os.unlink(os.path.join(self.out_dir, f))


class SourceSplitter(Splitter):
    """Splits the source file
    Oxford_GLS_GEDC_DUDE_DDDSI_Inflected-Forms-Full_1.1.xml
    into a series of smaller files, for convenience during the conversion
    process
    """

    header = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE morphEntries SYSTEM "OxMorphML-full.dtd">
<morphEntries language="ger" morphTextId="Oxford_GLS_GEDC_DUDE_DDDSI_Inflected-Forms" version="1.1.1" date="29-05-2013" sourceTextId="Xelda German morphology v3 2012-09-03 + Oxford_GLS_GEDC_DUDE_DDDSI_C001_EXB_full">"""

    def split(self):
        self.set_header(SourceSplitter.header)
        self.set_tail('</morphEntries>')
        self.buffer = [SourceSplitter.header,]
        with open(self.in_file, 'r') as fh:
            for line in fh:
                line = line.decode('utf8')
                self.line_num += 1
                line = line.strip()
                if line.startswith('<morphEntry'):
                    line = line.replace(' genSource="xelda"', '')
                    self.buffer.append(line)
                    if len(self.buffer) >= self.buffer_size:
                        self.purge_buffer()
        self.purge_buffer()


class XeldaSplitter(Splitter):
    header = '<?xml version="1.0" encoding="UTF-8"?>\n<entries>'

    def split(self):
        self.set_header(XeldaSplitter.header)
        self.set_tail('</entries>')
        self.buffer = [XeldaSplitter.header,]
        with open(self.in_file, 'r') as fh:
            for line in fh:
                line = line.decode('utf8')
                self.line_num += 1
                line = line.strip('\n')
                if (not line.strip() or
                    line.strip().startswith('<?xml') or
                    line.strip().startswith('<entries') or
                    line.strip().startswith('</entries')):
                    pass
                else:
                    self.buffer.append(line)
                    if (line.strip() == '</e>' and
                        len(self.buffer) >= self.buffer_size):
                        self.purge_buffer()
        self.purge_buffer()


def xelda_indexer(dir):
    from lxml import etree
    files = [f for f in os.listdir(dir) if f.endswith('.xml')]
    ids = {}
    for f in files:
        filenum = int(f.replace('.xml', ''))
        tree = etree.parse(os.path.join(dir, f))
        for entry in tree.findall('e'):
            if entry.findall('declensions/d'):
                id = entry.get('refid')
                ids[id] = filenum
    outfile = os.path.join(dir, 'index.txt')
    with open(outfile, 'w') as fh:
        for id in sorted(ids.keys()):
            fh.write('%s\t%d\n' % (id, ids[id],))
