from lxml import etree


class OxmorphEntry(object):

    def __init__(self, node):
        self.node = node

    def id(self):
        return self.node.get('entryId')

    def source_id(self):
        dnode = self.node.find('dictRef')
        if dnode is not None:
            return dnode.get('entryId')
        else:
            return None

    def lemma(self):
        return self.node.findtext('lemma/hw')

    def headword(self):
        return self.lemma()

    def wordclass(self):
        return self.node.find('lemma').get('pos')

    def gender(self):
        if self.wordclass() == 'noun':
            return self.node.find('lemma').get('gender')
        else:
            return None

    def forms_wrapper(self):
        try:
            return self.wrnode
        except AttributeError:
            if self.wordclass() == 'noun':
                self.wrnode = self.node.find('nounSet')
            elif self.wordclass() == 'verb':
                self.wrnode = self.node.find('verbSet')
            elif self.wordclass() == 'adjective':
                self.wrnode = self.node.find('adjSet')
            else:
                self.wrnode = None
            return self.wrnode

    def forms(self):
        try:
            return self.fset
        except AttributeError:
            nodes = []
            if self.forms_wrapper() is not None:
                for tag in ('nounUnit', 'verbUnit', 'adjUnit',):
                    nodes.extend(self.forms_wrapper().findall(tag))
            self.fset = [Inflection(n, self.wordclass()) for n in nodes]
            return self.fset

    def inflections(self):
        return self.forms()

    def sort_forms(self):
        del(self.fset)
        self.forms().sort(key=lambda i: i.sort_value())
        # Move all the form units to a new wrapper (called 'tmp'),
        #  filtering out any duplicates
        dummy = etree.SubElement(self.node, "tmp")
        signatures = set()
        for f in self.forms():
            if not f.signature() in signatures:
                dummy.append(f.node)
                signatures.add(f.signature())
        tag = self.forms_wrapper().tag
        # delete the original wrapper...
        self.forms_wrapper().getparent().remove(self.forms_wrapper())
        del(self.wrnode)
        # ...and rename 'tmp' as the proper wrapper
        dummy.tag = tag

    def has_plurals(self):
        for form in self.forms():
            if form.number == 'plural':
                return True
        return False

    def reduce_to_basic(self):
        if self.node.get('sourceTextId'):
            del(self.node.attrib['sourceTextId'])
        lemnode = self.node.find('lemma')
        if lemnode.get('restrictions'):
            del(lemnode.attrib['restrictions'])
        for f in self.forms():
            f.reduce_to_basic()
        self.sort_forms()


class Inflection(object):
    ATTRIBUTES = ('gender', 'number', 'case', 'degree', 'inflectionType',
        'mood', 'tense', 'person', 'nonFinType')
    GENDERSORT = {'masculine': 1, 'feminine': 2, 'neuter': 3}
    NUMBERSORT = {'singular': 1, 'plural': 2}
    CASESORT = {'nominative': 1, 'accusative': 2, 'genitive': 3, 'dative': 4}
    DEGREESORT = {'positive': 1, 'comparative': 2, 'superlative': 3}
    INFTYPESORT = {'strong': 1, 'weak': 2}
    MOODSORT = {'indicative': 1, 'subjunctive': 2, 'imperative': 3}
    TENSESORT = {'present': 1, 'past': 2}
    PERSONSORT = {'first': 1, 'second': 2, 'third': 3}

    def __init__(self, node, wordclass):
        self.node = node
        self.wordclass = wordclass
        for name, value in node.items():
            self.__dict__[name] = value
        for name in self.ATTRIBUTES:
            if not name in self.__dict__:
                self.__dict__[name] = None

    def wordform(self):
        return self.node.findtext('wordForm/base')

    def grammar(self):
        vals = {}
        for att in self.ATTRIBUTES:
            if att in self.__dict__ and self.__dict__[att] is not None:
                vals[att] = self.__dict__[att]
        return vals

    def signature(self):
        return self.wordform() + '_' +\
            '_'.join(['%s:%s' % (att, self.grammar()[att])
            for att in sorted(self.grammar().keys())
            if self.grammar()[att] is not None])

    def reduce_to_basic(self):
        for att in ('genType', 'genSource', 'genConfirmed'):
            if self.node.get(att):
                del(self.node.attrib[att])
        for att in ('case', 'degree', 'inflectionType', 'mood', 'tense',
            'nonFinType', 'inflected'):
            if self.node.get(att):
                del(self.node.attrib[att])
        if self.wordclass not in ('noun', 'adjective', 'verb'):
            if self.node.get('number'):
                del(self.node.attrib['number'])
        if self.wordclass not in ('adjective'):
            if self.node.get('gender'):
                del(self.node.attrib['gender'])
        if self.wordclass not in ('verb'):
            if self.node.get('person'):
                del(self.node.attrib['person'])
        particle = self.node.find('wordForm/particle')
        if particle is not None and particle.get('separated'):
            del(particle.attrib['separated'])

    def sort_value(self):
        val = 0
        if self.wordclass == 'noun':
            try:
                val += (100 * self.NUMBERSORT[self.number])
            except KeyError:
                val += (100 * 9)
            try:
                val += (1 * self.CASESORT[self.case])
            except KeyError:
                val += (1 * 9)
        if self.wordclass == 'adjective':
            try:
                val += (10000 * self.DEGREESORT[self.degree])
            except KeyError:
                val += (10000 * 9)
            try:
                val += (1000 * self.INFTYPESORT[self.inflectionType])
            except KeyError:
                val += (1000 * 9)
            try:
                val += (100 * self.NUMBERSORT[self.number])
            except KeyError:
                val += (100 * 9)
            try:
                val += (10 * self.GENDERSORT[self.gender])
            except KeyError:
                val += (10 * 9)
            try:
                val += self.CASESORT[self.case]
            except KeyError:
                val += 9
        elif self.wordclass == 'verb':
            if self.nonFinType == 'infinitive':
                val += 10000
            elif self.nonFinType == 'participle':
                val += 20000
            else:
                val += 30000
            try:
                val += (1000 * self.MOODSORT[self.mood])
            except KeyError:
                val += (1000 * 9)
            try:
                val += (100 * self.TENSESORT[self.tense])
            except KeyError:
                val += (100 * 9)
            try:
                val += (10 * self.NUMBERSORT[self.number])
            except KeyError:
                val += (10 * 9)
            try:
                val += (1 * self.PERSONSORT[self.person])
            except KeyError:
                val += (1 * 9)
        return val


