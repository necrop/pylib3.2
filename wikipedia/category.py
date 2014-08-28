import re

from regexcompiler import ReplacementListCompiler

from .articletitle import ArticleTitle
from .topictaxonomy.topicpicker import TopicPicker

# Regex substitutions to remove extraneous parts of the category -
#  so that we can just get to the superordinate
CATEGORY_STRIPPER = ReplacementListCompiler((
    (r' stubs$', ''),
    (r' \([^()]+\)', ''),
    (r' ([a-z]+(ed|en)|set|made) (by|in|with|for|on|for|to) .*$', ''),
    (r' (in|from|with|without|between|by|at|for|who|on|for|to|that|about) .*$', ''),
    (r'(University) of ', r'\1_of_'),
    (r' of .*$', ''),
    (r' and [a-z].*$', ''),
))
CATEGORY_FINDER = {
    'bio': re.compile(r'^\d{4}s? (births|deaths)$'),
    'superordinate1': re.compile(r' ([a-z-]+[^s]s|[a-z]*(men|people|craft)|alumni)$'),
    'superordinate2': re.compile(r'^([A-Za-z][a-z-]+([^s]s|men|craft)|Women|Men|People|Alumni)$'),
}
topic_picker = TopicPicker()


class Category(ArticleTitle):

    def __init__(self, text):
        ArticleTitle.__init__(self, text)
        self._parsed = False
        self._superordinate = None
        self._superordinate_longer = None

    @property
    def superordinate(self):
        self._parse_superordinate()
        return self._superordinate

    @property
    def superordinate_longer(self):
        self._parse_superordinate()
        return self._superordinate_longer

    @property
    def topics(self):
        return topic_picker.convert_category_to_topic(self.namespacestripped)

    def has_topic_classification(self):
        """
        Check that this category has a classification in the topic taxonomy
        """
        return topic_picker.is_classified(self.namespacestripped)

    def _parse_superordinate(self):
        # Find the superordinate from within the category
        if self._parsed:
            return

        if CATEGORY_FINDER['bio'].search(self.main):
            self._superordinate = 'people'
        else:
            text = CATEGORY_STRIPPER.edit(self.main).strip()
            match = CATEGORY_FINDER['superordinate1'].search(text)
            if match:
                self._superordinate = match.group(1)
            else:
                match = CATEGORY_FINDER['superordinate2'].search(text)
                if match:
                    self._superordinate = match.group(1).lower()

            # Make a longer version of the superordinate, including
            # the preceding word (if any) - so that we capture e.g.
            # 'electoral wards' as well as just 'wards'
            if self._superordinate:
                pattern = r'(^| )([A-Za-z]+) ' + self._superordinate
                match = re.search(pattern, self.main)
                if match:
                    self._superordinate_longer = (match.group(2).lower()
                                                  + ' '
                                                  + self._superordinate)

        self._parsed = True


class CategoryCollection(object):

    """
    The set of categories into which a given article (or another category)
    is classified.

    Used to determine which of the listed categories should be considered
    salient. Generally, we assume that the categories listed first are
    the most salient; so we just take the first x listed (where x is the
    max number required).

    But in cases where the categories are listed
    alphabetically (more or less), we pick the shortest ones, or the
    ones which seem best matched to the current article.

    Arguments to __init__ are:
     - iterable of Category objects
     - ArticleTitle object for the current article
    """

    default_max_num = 4

    def __init__(self, categories, article_title):
        self.category_list = list(categories)
        self.article_title = article_title

    def salient_categories(self, **kwargs):
        """
        Return the subset of x most salient categories
        """
        max_num = kwargs.get('max') or self.default_max_num

        if len(self.category_list) <= max_num:
            return self.category_list
        elif self._list_is_alphabetical():
            reordered = _order_by_salience(self.category_list,
                                           self.article_title)
            return reordered[0:max_num]
        else:
            return self.category_list[0:max_num]

    def display(self):
        display_string = self.article_title.full + '\n'
        display_string += repr(self.category_list)
        display_string += '\nALPHABETICAL? ' + str(self._list_is_alphabetical())
        display_string += '\n' + repr(self.salient_categories()) + '\n'
        return display_string

    def _list_is_alphabetical(self):
        previous = '0'
        alpha_yes, alpha_no = 0, 0
        for c in self.category_list:
            prefix = c.namespacestripped.lower()[0:3]
            if prefix >= previous:
                alpha_yes += 1
            else:
                alpha_no += 1
            previous = prefix
        if alpha_yes > alpha_no * 2:
            return True
        else:
            return False


def _order_by_salience(category_list, title):
    prefix = _title_prefix(title)
    for c in category_list:
        if _title_prefix(c) == prefix:
            c.score = 0
        else:
            c.score = 10
        c.score += len(c.namespacestripped)
    return sorted(category_list,
                  key=lambda c: c.score)


def _title_prefix(title):
    return title.namespacestripped.lower()[0:5]