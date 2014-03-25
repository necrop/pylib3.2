"""
Db models used for HTOED database:

ThesClass
ThesInstance
Superordinate
SuperordinateBranch

@author: James McCracken
"""

import re

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import NoResultFound

import stringtools
from lex.oed.thesaurus.dbbackend import thesaurusdbconfig

Base = declarative_base()
WORDCLASS_TRANSLATIONS = thesaurusdbconfig.WORDCLASS_TRANSLATIONS


class ThesClass(Base):
    __tablename__ = 'class'

    id = Column(Integer, primary_key=True)
    label = Column(String(200))
    level = Column(Integer)
    wordclass = Column(String(20))
    node_size = Column(Integer, nullable=False)
    branch_size = Column(Integer, nullable=False)
    sortcode = Column(Integer)

    parent_id = Column(Integer, ForeignKey('class.id'))
    children = relationship('ThesClass',
                            backref=backref('parent', remote_side=[id]))

    def __init__(self, thesaurus_class):
        self.id = thesaurus_class.id()
        self.label = thesaurus_class.label() or None
        self.level = thesaurus_class.level()
        self.wordclass = thesaurus_class.wordclass()
        self.node_size = thesaurus_class.size(branch=False)
        self.branch_size = thesaurus_class.size(branch=True)
        self.parent_id = thesaurus_class.parent()
        self.sortcode = thesaurus_class.sortcode()
        if self.label is not None:
            self.label = self.label[0:200]

    def __repr__(self):
        return '<ThesClass %d (%s)>' % (self.id, self.signature())

    def __eq__(self, other):
        return int(self.id) == int(other.id)

    def __hash__(self):
        return int(self.id)

    def signature(self):
        sig = ''
        if self.wordclass is not None:
            sig += '[' + self.wordclass + '] '
        if self.label is not None and self.label:
            sig += self.label
        return sig.strip()

    def penn_wordclass(self):
        try:
            return WORDCLASS_TRANSLATIONS[self.wordclass]
        except KeyError:
            return None

    #========================================================
    # Functions for displaying the class breadcrumb as a string
    #========================================================

    def breadcrumb_components(self):
        try:
            return self._breadcrumb_components
        except AttributeError:
            self._breadcrumb_components = []
            for ancestor in reversed(self.ancestors()):
                self._breadcrumb_components.append(ancestor.signature())
            return self._breadcrumb_components

    def breadcrumb(self):
        return ' > '.join(self.breadcrumb_components()[1:])

    def breadcrumb_tail(self):
        return ' > '.join(self.breadcrumb_components()[-3:])

    def breadcrumb_short(self):
        return ' > '.join(self.breadcrumb_components()[1:3]) + ' ... ' + \
            ' > '.join(self.breadcrumb_components()[-3:])

    #========================================================
    # Functions for finding descendants and ancestors
    #========================================================

    def ancestors(self):
        """
        Return a list of ancestor classes in ascending order,
        beginning with self.

        Note that that the present class is included as the first element
        of the list
        """
        try:
            return self._ancestors
        except AttributeError:
            self._ancestors = [self, ]
            if self.parent is not None:
                parent = self.parent
                while parent is not None:
                    self._ancestors.append(parent)
                    try:
                        parent = parent.parent
                    except NoResultFound:
                        parent = None
            return self._ancestors

    def ancestors_ascending(self):
        return self.ancestors()

    def ancestors_descending(self):
        try:
            return self._ancestors_descending
        except AttributeError:
            self._ancestors_descending = list(reversed(self.ancestors()))
            return self._ancestors_descending

    def ancestor_ids(self):
        return set([a.id for a in self.ancestors()])

    def ancestor(self, level=1):
        """
        Return the ancestor class at ancestor specified level (defaults to 1)
        """
        if self.level == level:
            return self
        for ancestor in self.ancestors():
            if ancestor.level == level:
                return ancestor
        return None

    def is_descendant_of(self, class_id):
        """
        Return True is the present class is a descendant of the argument.

        Argument can be either another ThesaurusClass object, or a
        thesaurus class ID
        """
        if class_id is None or not class_id:
            return False
        if isinstance(class_id, ThesClass):
            class_id = class_id.id
        class_id = int(class_id)
        if class_id in [a.id for a in self.ancestors()]:
            return True
        else:
            return False

    def is_same_branch(self, other):
        """
        Return True if the present class is the same as the argument
        class, is a descendant of the argument class, or is a direct
        ancestor of the argument.
        """
        if self.id == other.id:
            return True
        elif self.is_descendant_of(other) or other.is_descendant_of(self):
            return True
        else:
            return False

    def common_ancestor(self, other):
        other_ids = set([a.id for a in other.ancestors()])
        for ancestor in self.ancestors():
            if ancestor.id in other_ids:
                return ancestor
        return None

    def descendants(self):
        """
        Recursively list all descendant classes
        """
        def recurse(node, stack):
            stack.append(node)
            for child in node.children:
                stack = recurse(child, stack)
            return stack

        descendants = []
        for child in self.children:
            descendants = recurse(child, descendants)
        return descendants

    def wordclass_parent(self):
        """
        Return the wordclass-level parent of the current class
        (or None if the current class is already above parent level)
        """
        if self.wordclass is None:
            return None
        for ancestor in self.ancestors_descending():
            if ancestor.wordclass is not None:
                return ancestor

    def wordclass_parent_plus_one(self):
        """
        Return the class immediately below the wordclass-level parent
        (or None if the current class is already above this level)
        """
        if self.wordclass is None:
            return None
        for i, ancestor in enumerate(self.ancestors_descending()):
            if ancestor.wordclass is not None:
                try:
                    return self.ancestors_descending()[i + 1]
                except IndexError:
                    return None

    def wordclass_parent_minus_one(self):
        """
        Return the parent class immediately above wordclass level
        (or None if the current class is already above parent level)
        """
        if self.wordclass is None:
            return None
        for i, ancestor in enumerate(self.ancestors_descending()):
            if self.ancestors_descending()[i + 1].wordclass is not None:
                return ancestor

    def superclass(self):
        return self.wordclass_parent_minus_one()

    #========================================================
    # Other miscellaneous functions
    #========================================================

    def tokens(self):
        if self.label is None:
            return []
        else:
            label = self.label.lower()
            for replacement in '(),;.-':
                label = label.replace(replacement, ' ')
            for replacement in ('by way of', 'by means of', 'as regards'):
                label = label.replace(replacement, ' ')
            label = re.sub(r'  +', ' ', label)
            tokens = [stringtools.porter_stem(t)
                      for t in label.strip().split(' ')
                      if t not in thesaurusdbconfig.STOPWORDS]
            tokens.sort(key=len, reverse=True)
            return tokens

    def oed_url(self):
        """
        Return the URL to this class in OED Online
        """
        return 'http://www.oed.com/view/th/class/%d' % self.id

    def is_specific_enough(self, **kwargs):
        level = kwargs.get('level', 3)
        size = kwargs.get('size') or kwargs.get('branch_size', 10000)
        if self.level >= level or self.branch_size < size:
            return True
        else:
            return False


class ThesInstance(Base):
    __tablename__ = 'instance'

    id = Column(Integer, primary_key=True)
    lemma = Column(String(100), index=True)
    wordclass = Column(String(20))
    refentry = Column(Integer, nullable=False, index=True)
    refid = Column(Integer, nullable=False)
    refid_alt = Column(String(80))
    entry_node = Column(Integer, nullable=False)  # refid of the <Entry> element
    size = Column(Float, nullable=False)
    entry_size = Column(Float, nullable=False)
    is_deprecated = Column(Boolean)
    is_provisional = Column(Boolean)
    subentry_type = Column(String(20))
    chronorder = Column(Integer, nullable=False)
    start_year = Column(Integer)
    end_year = Column(Integer)

    class_id = Column(Integer, ForeignKey('class.id'))
    thesclass = relationship('ThesClass', backref=backref('instances'))

    def __init__(self, data):
        for key, value in data.items():
            self.__dict__[key] = value
        if self.lemma is not None:
            self.lemma = re.sub(r'(.)[ -](.)', r'\1\2', self.lemma)
            self.lemma = self.lemma[0:100]
        self.is_provisional = False

    def __repr__(self):
        if self.thesclass is not None:
            return '<ThesInstance (%s, %d#eid%d, HTclass=%d)>' % (self.lemma,
                self.refentry, self.refid, self.thesclass.id)
        else:
            return '<ThesInstance (%s, %d#eid%d, HTclass=null)>' % (self.lemma,
                self.refentry, self.refid)

    def rating(self):
        """
        Return the rating computed for this instance (higher for
        more significant senses, lower for minor senses; zero for
        obsolete senses.

        Returns a float.
        """
        try:
            return self._rating
        except AttributeError:
            if self.is_deprecated:
                rating = self.size
            else:
                rating = self.size * 2
            chron_supplement = max([0, 10 - self.chronorder])
            rating += (chron_supplement * 0.5)
            rating += self.archetype()
            self._rating = rating
            return self._rating

    def set_rating(self, value):
        """
        Force the rating to be a particular value
        """
        try:
            self._rating = float(value)
        except ValueError:
            pass

    def probability(self, total):
        return self.rating() / total

    def archetype(self):
        """
        Test if this instance is an archetypal example of its class.

        Considered true if the lemma appears in the class label
        (or parent class label, if the immediate class is unlabelled).

        Returns 2 if the lemma matches the class label, or 1 if the lemma
        is contained in the class label. Otherwise, returns 0.
        """
        return_value = 0
        if self.thesclass is not None:
            try:
                parent = [a for a in self.thesclass.ancestors() if
                          a.label is not None and a.label][0]
            except IndexError:
                pass
            else:
                label = parent.label
                if label in (self.lemma, 'a ' + self.lemma, 'an ' + self.lemma):
                    return_value = 2
                else:
                    target = ' ' + self.lemma + ' '
                    label = label.replace(',', ' ').replace(';', ' ')
                    label = ' ' + label + ' '
                    if target in label:
                        return_value = 1
        return return_value

    def branch_size(self):
        if self.thesclass is not None:
            return self.thesclass.branch_size
        else:
            return 0

    def node_size(self):
        if self.thesclass is not None:
            return self.thesclass.node_size
        else:
            return 0

    def is_derivative(self):
        if self.subentry_type == 'derivative':
            return True
        else:
            return False

    def superclass(self):
        """
        Return the parent class immediately above wordclass level
        (or None if the instance has no thesaurus class)
        """
        if self.thesclass is not None:
            return self.thesclass.superclass()
        else:
            return None

    def is_affix(self):
        if self.lemma.startswith('-') or self.lemma.endswith('-'):
            return True
        else:
            return False

    def wordclass_parent(self):
        if self.thesclass is not None:
            return self.thesclass.wordclass_parent()
        else:
            return None

    def is_descendant_of(self, class_id):
        if self.thesclass is None:
            return False
        else:
            return self.thesclass.is_descendant_of(class_id)

    def breadcrumb(self):
        if self.thesclass is None:
            return ''
        else:
            return self.thesclass.breadcrumb()

    def common_ancestor(self, other_thesclass):
        if self.thesclass is None:
            return None
        else:
            return self.thesclass.common_ancestor(other_thesclass)

    def oed_url(self):
        return 'http://www.oed.com/view/Entry/%d#eid%d' % (self.refentry,
            self.refid)


class Superordinate(Base):
    __tablename__ = 'superordinate'

    id = Column(Integer, primary_key=True)
    superordinate = Column(String(200), index=True)
    senses = Column(Integer)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value
        self.superordinate = self.superordinate[0:200]


class SuperordinateBranch(Base):
    __tablename__ = 'superordinatebranch'

    id = Column(Integer, primary_key=True)
    probability = Column(Float)
    superordinate_id = Column(Integer, ForeignKey('superordinate.id'))
    class_id = Column(Integer, ForeignKey('class.id'))
    thesclass = relationship('ThesClass')
    superordinate = relationship('Superordinate', backref=backref('branches'))

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value
