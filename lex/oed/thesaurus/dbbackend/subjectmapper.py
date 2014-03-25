"""
SubjectMapper

@author: James McCracken
"""

import os
from collections import defaultdict
import sqlalchemy.orm.exc

from lxml import etree  # @UnresolvedImport

from lex.oed.thesaurus.dbbackend import thesaurusdbconfig
from lex.oed.thesaurus.dbbackend.models import ThesClass

SESSION = thesaurusdbconfig.SESSION
PARSER = etree.XMLParser(remove_blank_text=True)
FILEPATH = os.path.join(os.path.dirname(__file__),
                        'subject_to_thesaurus_mapping.xml')


class SubjectMapper(object):

    subjectmap = defaultdict(set)
    subjectneg = defaultdict(set)
    class_cache = {}

    def __init__(self):
        if not SubjectMapper.subjectmap:
            self.load_map()

    def load_map(self):
        redirects = {}
        tree = etree.parse(FILEPATH, PARSER)
        for node in tree.findall('./class'):
            topic = node.get('name').lower()
            if node.get('redirect'):
                redirects[topic] = node.get('redirect').lower()
            else:
                for branch in node.findall('branch'):
                    classid = int(branch.get('id'))
                    if branch.get('negated'):
                        SubjectMapper.subjectneg[topic].add(classid)
                    else:
                        SubjectMapper.subjectmap[topic].add(classid)

        for topic, target in redirects.items():
            try:
                SubjectMapper.subjectmap[topic] = SubjectMapper.subjectmap[target]
            except KeyError:
                pass
            try:
                SubjectMapper.subjectneg[topic] = SubjectMapper.subjectneg[target]
            except KeyError:
                pass

    def is_thesaurus_mapped(self, topic):
        if topic.lower() in SubjectMapper.subjectmap:
            return True
        else:
            return False

    def equivalent_ids(self, topic):
        try:
            return SubjectMapper.subjectmap[topic.lower()]
        except KeyError:
            return []

    def equivalent_classes(self, topic):
        thesclasses = [self._retrieve_class(id) for id in
                       self.equivalent_ids(topic)]
        thesclasses = [t for t in thesclasses if t is not None and
                       t.wordclass is None]
        return thesclasses

    def equivalent_class(self, topic):
        """
        Return just the first (largest) of the classes returned
        by equivalent_classes()
        """
        thesclasses = self.equivalent_class(topic)
        try:
            return thesclasses[0]
        except IndexError:
            return None


    def _retrieve_class(self, id):
        id = int(id)
        try:
            return SubjectMapper.class_cache[id]
        except KeyError:
            try:
                thesclass = SESSION.query(ThesClass).filter_by(id=id).one()
            except sqlalchemy.orm.exc.NoResultFound:
                thesclass = None
            SubjectMapper.class_cache[id] = thesclass
            return thesclass

    def topics_to_nodes(self, topics):
        """
        Given a list of topics, return the corresponding set of
        thesaurus nodes.
        """
        nodes = set()
        topics = [topic.lower() for topic in topics]
        for topic in topics:
            if topic in SubjectMapper.subjectmap:
                for id in SubjectMapper.subjectmap[topic]:
                    nodes.add(id)
        return nodes

    def class_matches(self, thesclass, topic):
        """
        Return True if the thesclass is on a branch that matches
        the topic; otherwise return False
        """
        if thesclass is None:
            return False
        topic = topic.lower()
        ancestors = thesclass.ancestors()
        if (topic in SubjectMapper.subjectmap and
            any([a.id in SubjectMapper.subjectmap[topic] for a in ancestors]) and
            (topic not in SubjectMapper.subjectneg or not
            any([a.id in SubjectMapper.subjectneg[topic] for a in ancestors]))):
            return True
        else:
            return False

    def matches(self, thesclass, topic_list):
        """
        Return True if the thesclass is on a branch that matches
        any of the topics in the topic list; otherwise return False
        """
        # If topic_list is just a single topic string, turn it into a list
        try:
            topic_list.lower()
        except AttributeError:
            pass
        else:
            topic_list = [topic_list, ]

        # Return true if at least one of the topic matches
        if any([self.class_matches(thesclass, t) for t in topic_list]):
            return True
        else:
            return False
