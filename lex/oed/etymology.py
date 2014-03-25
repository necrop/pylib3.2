"""
Etymology -- OED etymology class.
Etymon -- Individual etymon (<etymon> element)

@author: James McCracken
"""

from lxml import etree  # @UnresolvedImport

from lex.wordclass.wordclass import Wordclass
from lex.oed.oedcomponent import OedComponent
from lex.lemma import Lemma


class Etymology(OedComponent):

    """
    OED etymology class.
    """

    def __init__(self, node):
        OedComponent.__init__(self, node)

    def etyma_all(self):
        """
        Return a list of all Etymon objects (including models).
        """
        try:
            return self._etyma_all
        except AttributeError:
            self._etyma_all = [Etymon(n) for n in
                               self.node.findall('.//etymon')]
            return self._etyma_all

    def etyma(self):
        """
        Return a list of Etymon objects, omitting models.
        """
        return [et for et in self.etyma_all() if not et.is_model()]

    def etyma_targets(self):
        """
        Return a list of IDs of entries targeted as direct etyma.
        """
        targets = [et.refentry() for et in self.etyma() if
                   et.refentry() is not None and et.refentry()]
        targets_uniq = []
        for target in targets:
            if not target in targets_uniq:
                targets_uniq.append(target)
        return targets_uniq

    def etyma_lemmas(self):
        """
        Return a list of direct etyma (as simple strings, rather than
        as Etymon objects).
        """
        return [et.lemma for et in self.etyma()]

    def is_compound(self, headword=None):
        """
        Return True if the the etyma indicate that this is a compound word
        (i.e. there are two etyma, both of which are English words,
        and neither of which are affixes).

        Return False otherwise.
        """
        if len(self.etyma()) == 2 or len(self.etyma()) == 3:
            if any([et.language() != 'English' or et.lemma_manager().is_affix()
                    for et in self.etyma()]):
                return False
            if headword is None:
                return True
            else:
                headword1 = headword.lower().replace('-', '').replace(' ', '')
                headword2 = ''.join([et.lemma.lower() for et in self.etyma()])
                if headword1 == headword2:
                    return True
                else:
                    return False
        else:
            return False


class Etymon(OedComponent):

    """
    OED etymon class.
    """

    def __init__(self, node):
        OedComponent.__init__(self, node)

    def __repr__(self):
        return '<Etymon: %s (%s)>' % (self.lemma, self.language(),)

    def type(self):
        """
        Return the type of etymon. One of:
         -- 'cross-reference'
         -- 'foreign form'
         -- 'unknown'
        """
        try:
            return self._type
        except AttributeError:
            if self.node.find('xr') is not None:
                self._type = 'cross-reference'
            elif (self.node.find('cf') is not None or
                  self.node.find('ff') is not None):
                self._type = 'foreign form'
            else:
                self._type = 'unknown'
            return self._type

    def language(self):
        """
        Return the source language, as given in the @lang attribute.

        Defaults to 'English' for cross-references, or for etyma
        missing a @lang attribute.
        """
        try:
            return self._language
        except AttributeError:
            if self.type == 'cross-reference':
                self._language = 'English'
            else:
                # Remember that xpath() returns a list, even if
                #  it matches only one element!
                self._language = (self.node.xpath('cf/@lang') or
                                  self.node.xpath('ff/@lang') or
                                  ['English', ])[0]
            return self._language

    def lemma_manager(self):
        """
        Lemma object containing the etymon itself.
        """
        try:
            return self._lemma_object
        except AttributeError:
            etymon_string = ''
            for tag in ('cf', 'ff', 'xlem', 'xhw',):
                node = self.node.find('.//%s' % tag)
                if node is not None:
                    etymon_string = etree.tostring(node,
                                                   method='text',
                                                   encoding='unicode')
                    break
            self._lemma_object = Lemma(etymon_string)
            return self._lemma_object

    @property
    def lemma(self):
        """
        Return the etymon itself (as a string).
        """
        return self.lemma_manager().lemma

    def is_model(self):
        """
        Return True if this is a model rather than a direct etymon.
        """
        if 'model' in self.node.attrib:
            return True
        else:
            return False

    def wordclass(self):
        """
        Return the part of speech of the etymon, if given in the
        cross-reference; return None if not.
        """
        typestrings = self.node.xpath('.//ps/@type')
        if typestrings:
            return Wordclass(typestrings[0]).penn
        else:
            return None

    pos = wordclass

    def refentry(self):
        """
        Return the ID of the target entry (if the etymon is a cross-reference)
        Return None if not.
        """
        if self.type() == 'cross-reference':
            return int(self.node.find('xr').get('refentry', 0))
        else:
            return None

    target_id = refentry

    def refid(self):
        """
        Return the ID of the target node (if the etymon is a cross-reference)
        Return None if not.
        """
        if self.type() == 'cross-reference':
            return int(self.node.find('xr').get('refid', 0))
        else:
            return None
