#-------------------------------------------------------------------------------
# Name: WikiPage
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import os
import re
import time
import urllib2
from collections import Counter

from bs4 import BeautifulSoup, Comment

from regexcompiler import ReplacementListCompiler

url_base = "http://en.wikipedia.org/wiki/"
user_agent = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:13.0) Gecko/20100101 Firefox/13.0.1"
headers = { "User-Agent" : user_agent }

stripped_elements = (
    ("span", {"class": "editsection"}),
    ("span", {"class": "printonly"}),
    ("div", {"class": "printonly"}),
    ("table", {"class": "metadata"}),
    ("table", {"class": "navbox"}),
    ("table", {"class": "vertical-navbox"}),
    ("div", {"class": "thumb"}),
    ("div", {"class": "portal"}),
    ("div", {"id": "mw-hidden-catlinks"}),
    ("a", {"class": "image"}),
    ("sup", {"class": "reference"}),
    ("sup", {"class": "Template-Fact"}),
    ("table", {"class": "persondata"})
)

href_cleaner = ReplacementListCompiler((
    (r"#.*$", ""),
    (r"^/", r"http://en.wikipedia.org/")
))



class WikiPage(object):

    def __init__(self, url):
        filename = None

        # Test if the URL is actually a file path
        if os.path.isfile(url):
            filename = url
        else:
            dir = os.path.dirname(url)
            fname = os.path.basename(url)
            for j in (urllib2.quote(fname), urllib2.unquote(fname)):
                if os.path.isfile(os.path.join(dir, j)):
                    filename = os.path.join(dir, j)

        if filename is not None:
            self.file = filename
            self.url_att = {"source": "", "redirected": ""}
        else:
            self.file = None
            if not url_base in url:
                url = url_base + url.replace(" ", "_")
            self.url_att = {"source": url, "redirected": url}
        self.cleaned = False

    def url(self, type=None):
        if type is None:
            return self.url_att["source"]
        else:
            return self.url_att[type.lower()]

    def id(self):
        if self.file is not None:
            return os.path.basename(self.file).replace(".html", "")
        else:
            return self.url().replace(url_base, "")

    def page_name(self):
        if self.file is not None:
            return os.path.basename(self.file).replace(".html", "")
        else:
            return self.url(type="redirected").replace(url_base, "")

    def load_page(self):
        if self.file is not None:
            self.html_att = open(self.file).read()
        else:
            req = urllib2.Request(self.url(), headers=headers)
            response = None
            for i in (1, 2, 3):
                try:
                    response = urllib2.urlopen(req)
                except urllib2.HTTPError:
                    break
                except urllib2.URLError:
                    time.sleep(2)
                if response is not None:
                    break
            if response:
                self.url_att["redirected"] = response.geturl()
                self.html_att = response.read()
            else:
                self.html_att = None

    def html(self):
        try:
            return self.html_att
        except AttributeError:
            self.load_page()
            return self.html_att

    def soup(self):
        try:
            return self.bs_object
        except AttributeError:
            try:
                self.html
            except AttributeError:
                self.load_page()
            if self.html is not None:
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
                    self.title_att = re.sub(r" - Wikipedia,.*$", "",
                                            tag.string)
            return self.title_att

    def category_box(self):
        try:
            return self.catbox
        except AttributeError:
            self.catbox = None
            if self.soup() is not None:
                c = self.soup().find("div", {"id": "catlinks"})
                c = self.soup_cleaner(c)
                self.catbox = c
            return self.catbox

    def content(self):
        try:
            return self.content_att
        except AttributeError:
            self.content_att = None
            if self.soup() is not None:
                c = self.soup().find("div", {"id": "mw-content-text"})
                c = self.soup_cleaner(c)
                self.content_att = c
            return self.content_att

    def content_clean(self):
        if self.content() is not None and not self.cleaned:
            [element.extract() for element in self.infobox()]
            [element.extract() for element in self.reflist()]
            [element.extract() for element in self.toc()]
            self.cleaned = True
        return self.content()

    def infobox(self):
        try:
            return self.infoboxes
        except AttributeError:
            self.infoboxes = []
            if self.content() is not None:
                self.infoboxes = self.content().find_all("table", {"class": "infobox"})
            return self.infoboxes

    def reflist(self):
        try:
            return self.reflists
        except AttributeError:
            self.reflists = []
            if self.content() is not None:
                self.reflists = self.content().find_all("div", {"class": "reflist"})
                xtra1 = self.content().find_all("div", {"class": "refbegin"})
                xtra2 = self.content().find_all("ol", {"class": "references"})
                self.reflists.extend(xtra1)
                self.reflists.extend(xtra2)
            return self.reflists

    def toc(self):
        try:
            return self.tocs
        except AttributeError:
            self.tocs = []
            if self.content() is not None:
                self.tocs = self.content().find_all("table", {"id": "toc"})
            return self.tocs

    def links(self, type=None):
        if type is None:
            type = "all"
        try:
            self.links_all
        except AttributeError:
            hrefs = self.content_clean().find_all("a")
            hrefs2 = self.category_box().find_all("a")
            hrefs.extend(hrefs2)
            self.links_all = [Link(h) for h in hrefs]
        if type == "all":
            return self.links_all

        if type == "uniq":
            tmp = [l for l in self.links_all]
        elif type == "wiki":
            tmp = [l for l in self.links_all if l.is_wikipedia_article()]
        elif type == "category":
            tmp = [l for l in self.links_all if l.is_category_page()]
        else:
            tmp = [l for l in self.links_all]
        lst = []
        seen = {}
        for l in tmp:
            if not l.url in seen:
                l.count = 1
                lst.append(l)
                seen[l.url] = l
            else:
                seen[l.url].count += 1
        return lst

    def tables(self):
        try:
            return self.tables_att
        except AttributeError:
            self.tables_att = [Table(t) for t in
                               self.content_clean().find_all("table")]
            self.tables_att = [t for t in self.tables_att if len(t.rows) > 1]
            return self.tables_att

    def list_items(self):
        try:
            return self.list_att
        except AttributeError:
            self.list_att = self.content_clean().find_all("li")
            return self.list_att

    def is_disambiguation_page(self):
        if ("(disambiguation)" in self.title or
            "(disambiguation)" in self.url()):
            return True
        for l in self.links(type="category"):
            if "disambiguation_pages" in l.href.lower():
                return True
        return False

    def soup_cleaner(self, c):
        if c is not None:
            # remove comments
            comments = c.find_all(text=lambda text:isinstance(text, Comment))
            [comment.extract() for comment in comments]
            # remove other elements
            for tuple in stripped_elements:
                elements = c.find_all(tuple[0], tuple[1])
                [el.extract() for el in elements]
        return c


class Link(object):

    def __init__(self, soup_object):
        self.href = soup_object.get("href")
        self.title = soup_object.get("title")
        self.surface = soup_object.get_text().strip()
        if self.href is not None:
            self.url = href_cleaner.edit(self.href)
        else:
            self.url = None

    def is_wikipedia_article(self):
        if ("http://en.wikipedia.org/wiki/" in self.url and
            not self.is_wikipedia_project_page()):
            return True
        else:
            return False

    def is_wikipedia_project_page(self):
        if ("http://en.wikipedia.org/wiki/Wikipedia:" in self.url or
            "http://en.wikipedia.org/wiki/Wikipedia_talk:" in self.url or
            "http://en.wikipedia.org/wiki/Category:" in self.url or
            "http://en.wikipedia.org/wiki/Special:" in self.url or
            "http://en.wikipedia.org/wiki/Help:" in self.url):
            return True
        else:
            return False

    def is_category_page(self):
        if "http://en.wikipedia.org/wiki/Category:" in self.url:
            return True
        else:
            return False

    def is_external_link(self):
        if (("http://" in self.url or "ftp://" in self.url) and
            not ".wikipedia.org/" in self.url):
            return True
        else:
            return False

    def wikipedia_resource(self):
        if "http://en.wikipedia.org/wiki/" in self.url:
            return self.url.replace("http://en.wikipedia.org/wiki/", "")
        else:
            return None


class Table(object):

    def __init__(self, table):
        try:
            self.id = table["id"]
        except KeyError:
            self.id = None
        try:
            self.classes = table["class"]
        except KeyError:
            self.classes = []
        self.parse(table)

    def parse(self, table):
        self.rows_all = []
        self.headers = []
        self.rows = []

        self.rows_all = [r.find_all(["td", "th"]) for r in table.find_all("tr")]
        mode = Counter([len(row) for row in self.rows_all]).most_common(1)

        header_rows = []
        for row in self.rows_all:
            row_type = "header"
            for cell in row:
                if cell.name == "td":
                    row_type = "content"
            if row_type == "header":
                header_rows.append([cell.get_text().strip() for cell in row])

        for h in header_rows:
            if len(h) == mode:
                self.headers = h[:]
                break
        if not self.headers:
            for h in header_rows:
                if len(h) > mode:
                    self.headers = h[:]
                    break
        if not self.headers:
            for h in header_rows:
                self.headers = h[:]
                break

        for row in self.rows_all:
            row_type = "header"
            for cell in row:
                if cell.name == "td":
                    row_type = "content"
            if row_type == "content":
                self.rows.append(TableRow(row, self.headers))

    def is_list_table(self):
        list_count = 0
        for row in self.rows:
            for cell in row.cells:
                if cell.find_all("li"):
                    list_count += 1
        if list_count >= 2:
            return True
        else:
            return False


class TableRow(object):

    def __init__(self, cells, headers):
        for i, cell in enumerate(cells):
            try:
                cell.column = headers[i]
            except IndexError:
                cell.column = None
        self.cells = cells

    def as_text(self):
        cell_text = []
        for cell in self.cells:
            text = cell.get_text()
            text = text.replace("\n", "|").strip()
            cell_text.append(text)
        return cell_text

    def as_string(self, separator=None):
        if separator is None:
            return " ".join(self.as_text())
        else:
            return separator.join(self.as_text())

    def as_binary(self):
        if len(self.cells) == 0:
            return ("", "")
        elif len(self.cells) == 1:
            return (self.as_text()[0], "")
        else:
            return (self.as_text()[0], " ".join(self.as_text()[1:]))

    def find_cell(self, col_name, mode=None):
        if mode is None:
            mode = "text"
        col_name = self.column_name_normalizer(col_name)
        for cell in self.cells:
            if (cell.column is not None and
                self.column_name_normalizer(cell.column) == col_name):
                    if mode == "text":
                        return cell.get_text().strip()
                    else:
                        return cell
        return None

    def column_name_normalizer(self, string):
        string = string.lower()
        for char in " _-,.:;":
            string = string.replace(char, "")
        return string.strip()




if __name__ == "__main__":
    j = WikiPage("Charles_Dickens_bibliography")
    print repr(j.content_clean())
    print repr(j.url(type="redirected"))
    print repr(j.title())
    for h in j.links(type="category"):
        print "\t" + h.wikipedia_resource(), repr(h.surface), str(h.count)
    for t in j.tables():
        print repr(t.id)
        for h in t.headers:
            print "\t" + repr(h)
        for row in t.rows:
            for cell in row:
                print repr(cell.column), repr(cell.get_text().strip())
        print str(len(t.rows))
    #for t in j.toc():
    #    print repr(t)

    for z in j.list_items():
        print repr(z.get_text().strip())
