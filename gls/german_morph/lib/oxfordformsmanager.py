
import os

from .oxfordformset import OxfordFormSet

subdirs = (
    '04_allVerbs.models-applied',
    '05_allVerbs.regular',
    'x3_adj_nouns.infl',
    'x3_adj_nouns_with_lexBase.infl',
    'x3_nouns.infl',
    'x3_nouns_with_lexBase.infl',
    'x4_adjectives.infl',
)



class OxfordFormsManager(object):

    def __init__(self, dir):
        self.parent_dir = dir
        self.index_file = os.path.join(self.parent_dir, 'index.txt')
        self.index = {}

    def index_files(self):
        idx = []
        for subdir in subdirs:
            print "\tIndexing %s..." % subdir
            dir = os.path.join(self.parent_dir, subdir)
            for f in os.listdir(dir):
                ofs = OxfordFormSet(os.path.join(dir, f))
                if len(ofs.lemmas) == 2:
                    vartypes = ('max', 'min',)
                else:
                    vartypes = ('null',)
                for l, v in zip(ofs.lemmas, vartypes):
                    idx.append((l, ofs.wordclass, v, subdir, f.decode('cp1250')))

        with open(self.index_file, "w") as fh:
            for i in idx:
                s = '%s\t%s\t%s\t%s\t%s\n' % i
                fh.write(s.encode('utf8'))

    def load_index(self):
        self.index = {}
        with open(self.index_file, "r") as fh:
            for l in fh:
                l = l.decode('utf8').strip()
                cols = l.split('\t')
                self.index[(cols[0], cols[1])] = (cols[2], cols[3], cols[4])

    def retrieve(self, lemma, wordclass):
        if not self.index:
            self.load_index()
        try:
            vartype, subdir, filename = self.index[(lemma, wordclass)]
        except KeyError:
            return None
        else:
            filepath = os.path.join(self.parent_dir, subdir, filename)
            if os.path.isfile(filepath):
                return OxfordFormSet(filepath, vartype=vartype)
            else:
                return None
