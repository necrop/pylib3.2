import os

from .. import wikipediaconfig

DEFAULT_FILEPATH = os.path.join(wikipediaconfig.TAXONOMY_DIR, 'topics.txt')


class TopicSet(object):

    mapping = {}

    def __init__(self, **kwargs):
        self.filepath = kwargs.get('filepath') or DEFAULT_FILEPATH
        if not TopicSet.mapping:
            self._load_topics()

    def classify(self, category):
        try:
            topic = TopicSet.mapping[category.lower()]
        except KeyError:
            pass
        else:
            return [(topic, True)]

        category = category.lower().replace('(', '').replace('(', '').replace(',', '')
        words = category.split()
        topix = []
        for w in words:
            try:
                topic = TopicSet.mapping[w]
            except KeyError:
                pass
            else:
                topix.append((topic, False))
        return topix

    def _load_topics(self):
        with open(self.filepath) as filehandle:
            for line in filehandle:
                parts = line.strip().split('\t')
                topic = parts[0].strip('~')
                for p in parts:
                    if '~' in p:
                        continue
                    TopicSet.mapping[p] = topic
