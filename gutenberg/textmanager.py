
import os

from gutenberg import gutenbergconfig
from gutenberg.htmlparser import fillet_file


class TextManager:

    def __init__(self, idnum):
        self.id = int(idnum)
        self.directory = os.path.join(gutenbergconfig.TEXT_DIR,
                                      str(self.id))
        self.text_file = os.path.join(self.directory, 'text.txt')
        self.metadata_file = os.path.join(self.directory, 'metadata.txt')
        self._metadata = None
        self._text = None

    @property
    def metadata(self):
        if not self._metadata:
            self._metadata = Metadata(self.metadata_file)
        return self._metadata

    def citation(self, **kwargs):
        return self.metadata.citation(**kwargs)

    @property
    def source_file(self):
        html_files = [f for f in os.listdir(self.directory) if
                      f.lower().endswith('.htm') or
                      f.lower().endswith('.html')]
        try:
            return os.path.join(self.directory, html_files[0])
        except IndexError:
            return None

    def convert_source(self, check_first=True):
        """
        Convert the HTML source file to a plain-text file. Returns True
        once the conversion has been carried out.

        If the check_first arg is True, the process will first check
        whether the output text file already exists; if so, no action is taken
        (the source is not re-converted), and the method returns False.
        """
        if check_first and os.path.isfile(self.text_file):
            return False
        else:
            fillet_file(self.source_file, self.text_file)
            return True

    def text(self):
        if self._text is None:
            with open(self.text_file) as filehandle:
                self._text = filehandle.readlines()
        return self._text

    def paragraphs(self):
        for line in self.text():
            line2 = line.strip()
            if line2:
                yield(line2)


class Metadata:

    def __init__(self, file):
        self.file = file
        self.author = None
        self.title = None
        self.year = None
        self.verse = False
        self._read_file()

    def citation(self, format='html'):
        if format.lower() == 'html':
            return '%s, <em>%s</em> (%d)' % (self.author, self.title, self.year)
        else:
            return '%s, _%s_ (%d)' % (self.author, self.title, self.year)

    def _read_file(self):
        with open(self.file) as filehandle:
            lines = [l.strip() for l in filehandle.readlines() if ':' in l]
        for line in lines:
            field, value = [f.strip() for f in line.split(':', 1)]
            field = field.lower()
            if field in ('a', 'author'):
                self.author = value
            elif field in ('t', 'title'):
                self.title = value
            elif field in ('y', 'year, ''date'):
                self.year = int(value)
            elif field in ('v', 'verse'):
                if value.lower() in ('true', 'yes', '1'):
                    self.verse = True