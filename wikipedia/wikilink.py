
from .articletitle import ArticleTitle


class Wikilink(object):

    def __init__(self, title, surface):
        self.title = ArticleTitle(title.strip())
        self.surface = (surface or title).strip()

    @property
    def namespace(self):
        return self.title.namespace
