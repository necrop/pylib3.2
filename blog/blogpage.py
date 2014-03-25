#-------------------------------------------------------------------------------
# Name: BlogPage
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import os
import re
import time
import urllib2
import datetime
import calendar

from bs4 import BeautifulSoup, Comment
import justext
import dateutil.parser as dateparser

from regexcompiler import ReplacementListCompiler
from .url import Url, HrefLink

user_agent = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:13.0) Gecko/20100101 Firefox/13.0.1"
headers = { "User-Agent" : user_agent }
justext_stoplist = justext.get_stoplist("English")

comments_header = [re.compile(regex, re.I) for regex in (
    r"^((No|\d+) (comments|responses|thoughts on|replies to)|reader[s']* comments)([: ]|$)",
    r"^(1|One) (comment|response|thought on|reply to)([: ]|$)",
    r"^(comments|responses|reader[s']* comments):?$",
)]
text_normalizer = ReplacementListCompiler((
    (u"\u00a0", " "),
    (u"\u2019", "'"),
    (u"\u2018", "'"),
    (r"( |\t)+", " "),
))



class BlogPage(object):

    def __init__(self, url):
        filename = None

        # Test if the URL is actually a file path
        if os.path.isfile(url):
            filename = url

        if filename is not None:
            self.file = filename
            self.url_att = None
        else:
            self.file = None
            self.url_att = Url(url)

    def url(self):
        return self.url_att

    def load_page(self):
        if self.file is not None:
            self.html_att = open(self.file).read()
        else:
            request = urllib2.Request(self.url().defragged(), headers=headers)
            response = None
            for i in (1, 2, 3):
                try:
                    response = urllib2.urlopen(request)
                except urllib2.HTTPError:
                    break
                except urllib2.URLError:
                    time.sleep(2)
                if response is not None:
                    break
            if response:
                self.url_att = Url(response.geturl())
                self.html_att = response.read()
            else:
                self.html_att = None

    def html(self):
        try:
            return self.html_att
        except AttributeError:
            self.load_page()
            return self.html_att

    def justext(self,
                text=None,
                goodOnly=None,
                commentStripped=None,
                boilerplate=None):
        if boilerplate is not None:
            self.inject_boilerplate(boilerplate)
        try:
            self.justext_att
        except AttributeError:
            self.justext_att = justext.justext(self.html(), justext_stoplist)

        customized = [p for p in self.justext_att]
        if commentStripped:
            # Remove all paras from the start of the comments onwards
            comments_start = None
            good_seen = False
            # Find the index of the para containing the comments header (if any)
            for i, p in enumerate(customized):
                if good_seen:
                    for regex in comments_header:
                        if regex.search(p["text"]):
                            comments_start = i
                if p["class"] == "good":
                    good_seen = True
            if comments_start is not None:
                # Slice the customized array to remove comments header and following
                customized = customized[0:comments_start]
        if goodOnly:
            # Remove all boilerplate paras to leave only 'good' ones
            customized = [p for p in customized if not self.is_boilerplate(p)]
        if text:
            # Turn paragraph object into paragraph text string
            customized = [normalize_paragraph(p["text"]) for p in customized]
        return customized

    def is_boilerplate(self, p):
        # Check if the para is marked as 'bad' by justext
        if p["class"] == "bad":
            return True
        # Check if the para is in the site-level boilerplate checklist
        if p["text"] in self.boilerplate_checklist():
            return True
        return False

    def set_boilerplate_checklist(self, boilerplate):
        self.boilerplate_att = boilerplate

    def boilerplate_checklist(self):
        try:
            return self.boilerplate_att
        except AttributeError:
            return {}

    def soup(self):
        try:
            return self.bs_object
        except AttributeError:
            try:
                self.html()
            except AttributeError:
                self.load_page()
            if self.html() is not None:
                self.bs_object = BeautifulSoup(self.html(), "lxml")
            else:
                self.bs_object = None
            return self.bs_object

    def title(self):
        try:
            return self.title_att
        except AttributeError:
            self.title_att = None
            if self.soup() is not None:
                tag = self.soup().title
                if tag is not None:
                    self.title_att = tag.string.strip()
            return self.title_att

    def body(self):
        try:
            return self.body_att
        except AttributeError:
            self.body_att = None
            if self.soup() is not None:
                self.body_att = self.soup().find("body")
                self.body_att = self.soup_cleaner(self.body_att)
            return self.body_att

    def links(self, mode="uniq", type="all"):
        try:
            self.links_all
        except AttributeError:
            if self.body() is not None:
                hrefs = self.body().find_all("a")
            else:
                hrefs = []
            self.links_all = [HrefLink(h) for h in hrefs]
            self.links_all.extend(self.dropdown_links())

        response = []
        if mode == "all":
            response = [l for l in self.links_all]
        elif mode == "uniq":
            seen = {}
            for l in self.links_all:
                if not l.comparable() in seen:
                    response.append(l)
                    seen[l.comparable()] = 1
        if type == "internal":
            response = [l for l in response if not l.is_external(self.url())]
        elif type == "external":
            response = [l for l in response if l.is_external(self.url())]
        return response

    def dropdown_links(self):
        try:
            return self.dropdown_links_att
        except AttributeError:
            if self.body() is not None:
                options = self.body().find_all("option")
            else:
                options = []
            options = [o for o in options if o.get("value") is not None and
                       o.get("value").startswith("http://")]
            self.dropdown_links_att = [HrefLink(o) for o in options]
            return self.dropdown_links_att

    def soup_cleaner(self, c):
        if c is not None:
            # remove comments
            comments = c.find_all(text=lambda text:isinstance(text, Comment))
            [comment.extract() for comment in comments]
        return c

    def blogroll(self):
        try:
            return self.blogroll_att
        except AttributeError:
            # Find all the <ul> lists on the page; prioritize those with
            #   the class 'blogroll' (blogspot blogs tend to use this)
            if self.body() is not None:
                ul_trees = self.body().find_all("ul", "blogroll")\
                           or self.body().find_all("ul")
            else:
                ul_trees = []

            # For each <ul>, create a list of HrefLink objects (one per <li>)
            link_lists = []
            for ul in ul_trees:
                link_list = []
                for r in ul.find_all("li"):
                    a = r.find("a")
                    if a is not None:
                        link_list.append(HrefLink(a))
                link_lists.append(link_list)

            # Discard link lists with fewer than 10 links
            link_lists = [l for l in link_lists if len(l) >= 10]

            # Make a list of candidate blogrolls: link lists where (a) all
            #   links are external and (b) a high proportion (>50%) are to
            #   sites that look like other blogs (i.e. have 'blog','wordpress',
            #   or 'typepad' in the URL).
            candidates = []
            for i, link_list in enumerate(link_lists):
                internal = [a for a in link_list if not a.is_external(self.url())]
                bloglike = [a for a in link_list if a.is_blog()]
                uniq = set([a.netloc_normalized() for a in link_list])
                if (not internal and
                    len(bloglike) > len(link_list) / 2 and
                    len(uniq) > len(link_list) / 2):
                    ratio = float(len(bloglike)) / float(len(link_list))
                    candidates.append({"index": i, "ratio": ratio})

            # Pick the candidate with the highest ratio of blog-like URLs
            candidates.sort(key=lambda a: a["ratio"], reverse=True)
            if candidates:
                self.blogroll_att = link_lists[candidates[0]["index"]]
            else:
                self.blogroll_att = []
            return self.blogroll_att


def normalize_paragraph(para):
    return text_normalizer.edit(para).strip()


class DateHunter(object):

    # Two different dates are used to fill in defaults for any values
    #  missing from the date string found by dateutil.parser. Checking that
    #  the two resulting datetime objects have the same value seems to be
    #  the only way to confirm that dateutil.parser did not have to fill in
    #  any defaults, and therefore that the date string was complete.
    default_fill = (
        datetime.datetime(1990, 1, 1),
        datetime.datetime(1991, 2, 2),
    )
    default_bounds = (
        datetime.datetime(2000, 1, 1),
        datetime.datetime.today()
    )
    urltests = (
        re.compile(r"/(20[01]\d)/(0\d|1[012])/"),
        re.compile(r"[_/](20[01]\d)_(0\d|1[012])[_/]"),
        re.compile(r"/(20[01]\d)(0\d|1[012])/"),
        re.compile(r"=(20[01]\d)(0\d|1[012])l(&|$)"),
    )

    def __init__(self, paragraphs, url):
        self.paragraphs = paragraphs
        self.set_bounds(url)

    def set_bounds(self, url):
        year = None
        month = None
        for t in DateHunter.urltests:
            match = t.search(url)
            if match is not None:
                year = int(match.group(1))
                month = int(match.group(2))
                break
        if month is not None:
            start = datetime.datetime(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end = datetime.datetime(year, month, last_day)
            self.bounds = (start, end)
            self.month_known = True
        else:
            self.bounds = default_bounds
            self.month_known = False

    def find_date(self):
        candidates =[]
        for p in self.paragraphs:
            p_short = p
            if len(p_short) > 100:
                p_short = p_short[0:100]
            for section in p_short.split("|"):
                try:
                    d = dateparser.parse(section,
                        default=DateHunter.default_fill[0], fuzzy=True)
                except ValueError:
                    d = DateHunter.default_fill[0]
                if d >= self.bounds[0] and d <= self.bounds[1]:
                    # Parse out a second date, using alternative defaults,
                    #  then check that the two dates are the same - see comment
                    #  at the definition of default_fill above.
                    d_alt = dateparser.parse(section,
                            default=DateHunter.default_fill[1], fuzzy=True)
                    if d == d_alt:
                        candidates.append(d)
                        break
        if candidates:
            datestamp = self.find_best_candidate(candidates)
            estimate = False
        elif self.month_known:
            datestamp = self.bounds[1]
            estimate = True
        return (datestamp, estimate)

    def find_best_candidate(self, candidates):
        candidates = [[c, i] for i, c in enumerate(candidates)]
        for c in candidates:
            if c[0].month == 1 and c[0].day == 1:
                c[1] += 100
        return candidates[0][0]



if __name__ == "__main__":
    j = BlogPage("http://www.dolcebellezza.net/2010/09/talented-mr-ripley.html")
    print j.title()
    #for z in j.blogroll():
    #    print z.url.cleaned
