#-------------------------------------------------------------------------------
# Name: Url
# Purpose:
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import re
import urlparse

bloglike_url = re.compile(r"(blog|typepad|wordpress|livejournal)")


class Url(object):

    def __init__(self, url):
        if url is not None:
            self.original = url.strip()
        else:
            self.original = ""
        if self.original.startswith("www."):
            self.parsed = urlparse.urlparse("http://" + self.original)
        else:
            self.parsed = urlparse.urlparse(self.original)

    def cleaned(self):
        return self.parsed.geturl()

    def defragged(self):
        return urlparse.urldefrag(self.cleaned())[0]

    def comparable(self):
        return self.defragged().lower().replace("www.", "").rstrip("/")

    def is_absolute(self):
        if self.parsed.netloc:
            return True
        else:
            return False

    def netloc(self):
        return self.parsed.netloc

    def netloc_normalized(self):
        return re.sub(r"^www\.", "", self.netloc().lower())

    def is_external(self, comparison):
        if not self.original or not self.netloc():
            return False
        if isinstance(comparison, str):
            comparison = Url(comparison)
        if self.netloc_normalized() == comparison.netloc_normalized():
            return False
        else:
            return True

    def is_blog(self):
        if not self.original:
            return False
        elif bloglike_url.search(self.defragged().lower()):
            return True
        else:
            return False

    def homepage(self):
        if self.is_absolute():
            return self.parsed.scheme + "://" + self.parsed.netloc
        else:
            return None

    def base(self):
        if self.is_absolute():
            return self.parsed.scheme + "://" + self.parsed.netloc + "/"
        else:
            return None


class HrefLink(Url):

    def __init__(self, link):
        # argument should be a BeautifulSoup object for a HTML <a> element
        # or <option> element (with a URL as its value)
        url = link.get("href") or link.get("value")
        Url.__init__(self, url)
        self.title = link.get("title")
        self.surface = link.get_text().strip()




if __name__ == "__main__":
    j = Url("www.BAkersdaughterwrites.wordpress.com/jimble/jumble#hash")
    print j.parsed.scheme
    print j.netloc()
    print j.netloc_normalized()
    #print j.parsed.path
    #print j.cleaned
    print j.is_external("http://BAkersdaughterwrites.wordpress.com/blah")
    print j.homepage()
