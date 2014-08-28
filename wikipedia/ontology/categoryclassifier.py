import os
import re
from collections import defaultdict

from .. import wikipediaconfig

NAMES_DIR = os.path.join(wikipediaconfig.RESOURCES_DIR, 'categories')
YEAR_PATTERN = re.compile(r'^(1[0-9]{3}|200[0-9]|1[7-9][0-9]0s) in ')


class CategoryClassifier(object):

    """
    Used to suggest general classification of an article based on its
    categories
    """

    groups = {}

    def __init__(self):
        if not CategoryClassifier.groups:
            load_names()

    def classification_of(self, article):
        poll = defaultdict(int)
        for category in article.categories:
            group = self.category_to_group(category)
            if group:
                poll[group] += 1

        if poll:
            league_table = [(group, value) for group, value in poll.items()]
            league_table.sort(key=lambda r: r[1], reverse=True)
            return league_table
        else:
            return None

    def category_to_group(self, category):
        try:
            return CategoryClassifier.groups[category.superordinate]
        except KeyError:
            try:
                return CategoryClassifier.groups[category.superordinate_longer]
            except KeyError:
                pass

        if YEAR_PATTERN.search(category.main):
            return 'event'
        else:
            return None


def load_names():
    for filename in os.listdir(NAMES_DIR):
        group = os.path.splitext(filename)[0]
        with open(os.path.join(NAMES_DIR, filename)) as filehandle:
            for line in filehandle:
                CategoryClassifier.groups[line.strip()] = group
