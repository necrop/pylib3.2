import os
import re

from wikipedia import wikipediaconfig
from wikipedia.articletitle import ArticleTitle

DISAMBIG_MATCH = re.compile(r'^\{\{(' +
                            '|'.join(wikipediaconfig.DISAMBIGUATION_TEMPLATES) +
                            r')(\||\}\})', re.I)
SIA_MATCH = re.compile(r'^\{\{(' +
                       '|'.join(wikipediaconfig.SIA_TEMPLATES) +
                       r')(\||\}\})', re.I)


class DumpIterator(object):

    """
    DumpIterator -- Quick parser of a wikipedia dump file line by line,
    yielding one entry at a time.

    Kwargs:
        in_file (str): the input XML dump file (if only one).
        in_dir (str): the directory containing the XML dump files (if more
            than one).
        keep_namespaced_articles (bool): (False).
        keep_lists (bool): (False).
        keep_redirects (bool): (False).
        keep_disambiguation_pages (bool): (False).
    """

    def __init__(self, **kwargs):
        input_files = None
        if kwargs.get('in_file') and os.path.isfile(kwargs.get('in_file')):
            input_files = [kwargs.get('in_file'), ]
        elif kwargs.get('in_dir'):
            directory = kwargs.get('in_dir')
            input_files = [os.path.join(directory, f) for f in
                           os.listdir(directory) if f.endswith('.xml')
                           or f.endswith('.XML')]
        if not input_files:
            raise IOError('Input file(s) not specified or not found')

        self.input_files = input_files

        # Filters: if any of the following are set to False,
        # the corresponding articles will be skipped/omitted. Note that
        # these are all set to False by default.
        self.allow_namespaced = kwargs.get('keep_namespaced_articles', False)
        self.allow_listish = kwargs.get('keep_lists', False)
        self.allow_redirects = kwargs.get('keep_redirects', False)
        self.allow_disambiguations = kwargs.get('keep_disambiguation_pages', False)
        self.line_count = 0

    def iterate(self, **kwargs):
        """
        Iterate through the input file(s), yielding one article at a time.

        Note that the return value is a list of strings representing
        all the lines of the article - the XML container, not just
        the wikicode.

        Kwargs:
            offset_line (int): start at a particular line, rather than at
                the beginning of the file.
            offset_byte (int): start at a particular byte position,
                rather than at the beginning of the file.
            offset_ratio (float between 0 and 1): start a certain way
                through the file, rather than at the beginning;
                e.g. offset_ratio=0.5 will start halfway through.

        Yields:
            list
        """
        offset_line = kwargs.get('offset_line') or None
        offset_byte = kwargs.get('offset_byte') or None
        offset_ratio = kwargs.get('offset_ratio') or None
        self.line_count = 0

        for in_file in self.input_files:
            if offset_ratio:
                file_size = os.path.getsize(in_file)
                offset_byte = int(file_size * offset_ratio)

            collect = False
            buffer = []
            with open(in_file) as filehandle:

                # Jump to a particular byte position
                if offset_byte:
                    filehandle.seek(offset_byte)

                for line in filehandle:
                    # Skip until we reach the offset line (if specified)
                    self.line_count += 1
                    if offset_line and self.line_count < offset_line:
                        continue

                    if line.strip().startswith('<page'):
                        collect = True
                        buffer = []
                    if collect and not _line_is_all_comment(line):
                        buffer.append(_cleanup(line))
                    if line.strip().startswith('</page'):
                        if self.article_is_usable(buffer):
                            yield(buffer)
                        collect = False
                        buffer = []

    def article_is_usable(self, article):
        """
        Test if the article is usable; it will be skipped (not yielded)
        if this function returns False.

        Returns:
            bool
        """
        article2 = [line.strip() for line in article]
        title = None
        disambiguation_article = False
        redirect_article = False
        sia_article = False
        list_article = False
        for line in article2:
            if line.startswith('<title>'):
                title = line.replace('<title>', '').replace('</title>', '')
                title = ArticleTitle(title)
            elif DISAMBIG_MATCH.search(line):
                disambiguation_article = True
            elif SIA_MATCH.search(line):
                sia_article = True
            elif line.startswith('<redirect'):
                redirect_article = True
            elif line.lower().startswith('{{day}}'):
                list_article = True
            elif _line_is_list_category(line):
                list_article = True

        if redirect_article and not self.allow_redirects:
            return False
        elif disambiguation_article and not self.allow_disambiguations:
            return False
        elif title and title.namespace and not self.allow_namespaced:
            return False
        elif title and title.is_disambiguation_page() and not self.allow_disambiguations:
            return False
        elif title and title.is_listlike() and not self.allow_listish:
            return False
        elif (list_article or sia_article) and not self.allow_listish:
            return False
        else:
            return True


def _line_is_all_comment(line):
    """
    Remove any line that is just a comment - since these seem to screw
    up the mwparserfromhell parser
    """
    line = line.strip()
    if line.startswith('&lt;!--') and line.endswith('--&gt;'):
        line = re.sub(r'^&lt;!--(.*)--&gt;$', r'\1', line)
        if not '&gt;' in line:
            return True
    return False


def _line_is_list_category(line):
    if line.startswith('[[Category:'):
        parts = line.split('|')
        if (parts and
                ('Lists of' in parts[0] or ' lists' in parts[0])):
            return True
    return False


def _cleanup(line):
    """
    Remove comments at the end of the line
    """
    line2 = line.strip()
    line2 = re.sub(r'&lt;!--[^&]*--&gt;$', r'', line2)
    if not '&lt;!--' in line2:
        return line2.strip() + '\n'
    else:
        return line
