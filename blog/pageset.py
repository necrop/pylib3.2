#-------------------------------------------------------------------------------
# Name: PageSet
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import os
import re
import random
from collections import Counter, defaultdict

from .blogpage import BlogPage
from .url import Url

class PageSet(object):
    """Manage a set of blog pages form a give site.

    Essentially, this is to facilitate comparing the pages with each other
    in order to help identify boilerplate; the assumption being that
    boilerplate paragraphs will recur across several pages."""

    def __init__(self):
        self.pages = []
        self.url_tracker = {}

    def add_pages(self, urls):
        for url in urls:
            self.add_page(url)

    def add_page(self, page):
        """Add a page (BlogPage object) to the set"""
        if isinstance(page, str):
            page = BlogPage(page)
        if not isinstance(page, BlogPage):
            raise TypeError("Argument to PageSet.add_page must be a URL or a BlogPage object")
        if not page.url().comparable() in self.url_tracker:
            self.pages.append(page)
            self.url_tracker[page.url().comparable()] = 1

    def boilerplate_checklist(self, **kwargs):
        """Return the boilerplate dictionary"""
        try:
            return self.boilerplate_att
        except AttributeError:
            self.identify_boilerplate(**kwargs)
            return self.boilerplate_att

    def identify_boilerplate(self, **kwargs):
        """Create a dictionary of boilerplate paragraphs.
        Looks for paragraphs which recur across multiple pages (at least
        50% of the sample).

        By default, the sample size is 20 pages selected at random from the
        set. This can be changed by passing a 'sampleSize' keyword argument,
        e.g. 'identify_boilerplate(sampleSize=30)'

        'identify_boilerplate(sampleSize=None)' will cause the whole page
        set to be used as the sample set."""
        sample_size = kwargs.get("sampleSize", 20)
        page_set = [p for p in self.pages]
        if (sample_size is not None and
            isinstance(sample_size, int) and
            sample_size > len(self.pages)):
            page_set = random.sample(page_set, sample_size)
        para_counter = Counter()
        for page in page_set:
            uniq = list(Counter([para for para in page.justext(text=True)]))
            para_counter.update(uniq)
        self.boilerplate_att = {}
        for j in para_counter.most_common():
            print repr(j[0])
            print str(j[1])
            if j[1] >= len(page_set) / 2:
                self.boilerplate_att[j[0]] = j[1]

    def set_boilerplate_checklist(self, **kwargs):
        """Send boilerplate dictionary to each page in the page set"""
        for page in self.pages:
            page.set_boilerplate_checklist(self.boilerplate_checklist(**kwargs))

    def crawler(self):
        try:
            return self.crawl_stack
        except AttributeError:
            self.crawl_stack = CrawlStack()
            return self.crawl_stack


class CrawlStack(object):

    def __init__(self):
        pass

    def navigation(self):
        try:
            return self.nav_att
        except AttributeError:
            self.nav_att = Navigation()
            return self.nav_att

    def set_navigation(self, **kwargs):
        self.navigation().update(**kwargs)

    def crawl(self):
        if self.navigation().start is None:
            raise AttributeError("Navigation must have start URL defined")
        else:
            self.stack = []
            j = StackItem(self.navigation().start)
            j.iterate = True
            self.append_to_stack(j)
            while self.todo():
                for item in self.todo():
                    page = BlogPage(item.url.defragged())
                    if self.navigation().is_linksource(item.url):
                        for l in page.links(mode="uniq", type="internal"):
                            if (self.navigation().is_post(l) or
                                (self.navigation().is_followable(l) and
                                 self.navigation().is_linksource(l))):
                                self.append_to_stack(StackItem(l))
                    item.visited = True
                for s in self.stack:
                    print s.url.defragged(), s.visited
                print str(len(self.stack)), str(len(self.todo()))

    def todo(self):
        return [item for item in self.stack if item.visited == False]

    def append_to_stack(self, item):
        url_dict = {}
        for existing_item in self.stack:
            url_dict[existing_item.url.comparable()] = 1
        if not item.url.comparable() in url_dict:
             self.stack.append(item)
             return True
        else:
            return False


class StackItem(object):

    def __init__(self, url):
        try:
            url.defragged()
        except AttributeError:
            url = Url(url)
        self.url = url
        self.visited = False



class Navigation(object):

    nav_templates = (
        ("year", r"(199[789]|20[01]\d)"),
        ("month", r"(0\d|1[012])"),
        ("day", r"([012]\d|3[01])"),
        ("htmlpost", r"[a-zA-Z0-9%-]+\.p?html?"),
        ("phppost", r"[a-zA-Z0-9%-]+\.php"),
        ("asppost", r"[a-zA-Z0-9%-]+\.aspx?"),
        ("untypedpost", r"[a-zA-Z0-9%-]+/"),
        ("post", r"[a-zA-Z0-9%-]+\.(html?|php|aspx?)"),
    )


    def __init__(self, **kwargs):
        self.start = kwargs.get("start", None)
        self.base_att = kwargs.get("base", None)
        self.recursive = kwargs.get("recursive", True)
        self.rx = {}
        for name in ("follow", "post", "review", "linksource"):
            self.rx[name] = self.compile_regex(kwargs.get(name, "."))
        for name in ("no-follow", "no-post", "no-review", "no-linksource"):
            self.rx[name] = self.compile_regex(kwargs.get(name, "qqxzq"))

    def update(self, **kwargs):
        for name in kwargs.keys():
            if name == "start":
                self.start = kwargs[name]
            elif name == "base":
                self.base_att = kwargs[name]
            else:
                self.rx[name] = self.compile_regex(kwargs[name])

    def start_url(self):
        if self.start is None:
            return None
        try:
            return self.start_url_att
        except AttributeError:
            self.start_url_att = Url(self.start)
            return self.start_url_att

    def base(self):
        if self.base_att is not None:
            return self.base_att
        else:
            return self.start_url().base()

    def matches(self, name, url_string):
        name = name.strip().lower().replace(" ", "-").replace("_", "-")
        if name in self.rx and self.rx[name].search(url_string):
            return True
        else:
            return False

    def is_local(self, url):
        url = self.normalize_urlstring(url)
        if (url.startswith(self.base()) or
            url.replace("http://www.", "http://").startswith(self.base()) or
            url.replace("http://", "http://www.").startswith(self.base())):
            return True
        else:
            return False

    def is_followable(self, url):
        url = self.normalize_urlstring(url)
        if (self.is_local(url) and
            self.matches("follow", url) and
            not self.matches("no-follow", url)):
            return True
        else:
            return False

    def is_post(self, url):
        url = self.normalize_urlstring(url)
        if (self.is_local(url) and
            self.matches("post", url) and
            not self.matches("no-post", url)):
            return True
        else:
            return False

    def is_review(self, url):
        url = self.normalize_urlstring(url)
        if (self.is_post(url) and
            self.matches("review", url) and
            not self.matches("no-review", url)):
            return True
        else:
            return False

    def is_linksource(self, url):
        url = self.normalize_urlstring(url)
        if url == self.normalize_urlstring(self.start_url()):
            return True # Starting URL *must* be treated as a link source
        elif ((self.is_post(url) or self.is_followable(url)) and
            self.matches("linksource", url) and
            not self.matches("no-linksource", url)):
            return True
        else:
            return False

    def normalize_urlstring(self, url):
        try:
            return url.defragged()
        except AttributeError:
            if isinstance(url, str):
                return Url(url).defragged()
            else:
                raise TypeError("Argument must be a URL string or a Url object")

    def compile_regex(self, uncompiled):
        uncompiled = uncompiled.strip()
        for t in Navigation.nav_templates:
            uncompiled = uncompiled.replace("{" + t[0] + "}", t[1])
        return re.compile(uncompiled)

