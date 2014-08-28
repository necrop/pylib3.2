import os
from collections import defaultdict

from .. import wikipediaconfig
from .topicset import TopicSet

DEFAULT_RAWFILE = os.path.join(wikipediaconfig.TAXONOMY_DIR, 'categories_filtered.txt')
DEFAULT_MAPPEDFILE = os.path.join(wikipediaconfig.TAXONOMY_DIR, 'categories_mapped.txt')
DEFAULT_FAILEDFILE = os.path.join(wikipediaconfig.TAXONOMY_DIR, 'categories_unmapped.txt')
DEFAULT_STOPWORDS = wikipediaconfig.COUNTRIES_FILE
RUNNER_UP_FACTOR = 0.7


class TopicPicker(object):

    stopwords = set()
    map = {}

    def __init__(self, **kwargs):
        self.raw_file = kwargs.get('in_file') or DEFAULT_RAWFILE
        self.mapping_file = kwargs.get('out_file') or DEFAULT_MAPPEDFILE
        self.failed_file = kwargs.get('failed_file') or DEFAULT_FAILEDFILE
        self.stopwords_file = kwargs.get('stopwords') or DEFAULT_STOPWORDS
        self.runner_up_factor = kwargs.get('runner_up_factor') or RUNNER_UP_FACTOR

    def convert_category_to_topic(self, category):
        if not TopicPicker.map:
            self._load_map()
        category = category.lower().replace('category:', '').strip()
        try:
            return TopicPicker.map[category]
        except KeyError:
            return []

    def is_classified(self, category):
        """
        Check that a given category has a classification in the topic taxonomy
        """
        if not TopicPicker.map:
            self._load_map()
        category = category.lower().replace('category:', '').strip()
        if category in TopicPicker.map:
            return True
        else:
            return False

    def build_topic_map(self):
        if not TopicPicker.stopwords:
            self._load_stopwords()

        categories = {}
        with open(self.raw_file, 'r') as filehandle:
            for line in filehandle:
                parts = line.strip().lower().split('\t')
                category = parts[0]
                if len(parts) > 1:
                    parents = parts[1:]
                else:
                    parents = []
                categories[category] = {'parents': {p: set() for p in parents},
                                        'topics': defaultdict(int)}

        # Seed by scoring categories which equal (or include) terms in the
        #  topic set
        topic_set = TopicSet()
        catlist = list(categories.keys())
        for category in catlist:
            topix = topic_set.classify(category)
            for topic_tuple in topix:
                topic = topic_tuple[0]
                if topic_tuple[1]:
                    categories[category]['topics'][topic] += 100
                else:
                    categories[category]['topics'][topic] += 20

        for iteration in (1, 2, 3, 4, 5, 6,):
            print('Building topic map: iteration %d...' % iteration)
            for category in catlist:
                # If this category is one of our base topics, don't
                #  attempt to re-score it!
                topic_tuple = topic_set.classify(category)
                if topic_tuple and topic_tuple[0]:
                    continue
                # ... And don't score categories in the stop list
                if category in TopicPicker.stopwords:
                    continue

                category_stem = category[0:5]
                for p, seen in categories[category]['parents'].items():
                    if p.startswith(category_stem) and len(p) < len(category):
                        factor = 0.5
                    elif p.startswith(category_stem):
                        factor = 0.3
                    elif len(p) < len(category):
                        factor = 0.2
                    else:
                        factor = 0.1
                    try:
                        scores = categories[p]['topics']
                    except KeyError:
                        pass
                    else:
                        for topic, v in scores.items():
                            if topic in seen:
                                continue
                            categories[category]['topics'][topic] += (v * factor)
                            seen.add(topic)

        with open(self.mapping_file, 'w') as filehandle:
            for category in catlist:
                if categories[category]['topics']:
                    scores = [(k, v) for k, v in categories[category]['topics'].items()]
                    scores.sort(key=lambda t: t[1], reverse=True)
                    scores = scores[0:3]
                    line = (category + '\t' +
                            '\t'.join(['%s=%0.3g' % s for s in scores]))
                    filehandle.write(line + '\n')

        with open(self.failed_file, 'w') as filehandle:
            for category in catlist:
                if not categories[category]['topics']:
                    line = category + '\t' + repr(categories[category]['parents'])
                    filehandle.write(line + '\n')

    def _load_map(self):
        TopicPicker.map = {}
        with open(self.mapping_file) as filehandle:
            for line in filehandle:
                parts = line.strip().split('\t')
                category = parts[0]

                ranking = []
                for t in parts[1:]:
                    topic, score = t.split('=')
                    ranking.append((topic, float(score)))
                top_score = ranking[0][1]
                ranking = [r[0] for r in ranking
                           if r[1] > top_score * self.runner_up_factor]

                TopicPicker.map[category] = ranking

    def _load_stopwords(self):
        with open(self.stopwords_file) as filehandle:
            for line in filehandle:
                TopicPicker.stopwords.add(line.strip().lower())
