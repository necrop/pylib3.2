import os
import re

from .. import wikipediaconfig
from ..dumpiterator import DumpIterator
from ..articletitle import ArticleTitle
from ..category import Category, CategoryCollection
from ..ontology.categoryclassifier import CategoryClassifier


TAXONOMY_DIR = wikipediaconfig.TAXONOMY_DIR
DEFAULT_INPUT = wikipediaconfig.CURRENT_DUMP
DEFAULT_RAW = os.path.join(TAXONOMY_DIR, 'categories_raw.txt')
DEFAULT_FILTERED = os.path.join(TAXONOMY_DIR, 'categories_filtered.txt')

SKIP = {'Articles', 'Wikipedia', 'WikiProject', 'Wikidata', 'Commons', 'AfC',
        'Categories'}
HIDDEN = ('{{tracking category}}', '{{empty category}}',
          '{{monthly clean up category', '{{wikipedia category}}',
          '{{hidden category}}', '{{template category')
STOPWORDS = [' ' + w + ' ' for w in ('in', 'by', 'from', 'at the',)]
category_classifier = CategoryClassifier()


class RawCategoryList(object):

    def __init__(self, **kwargs):
        self.in_file = kwargs.get('in_file') or DEFAULT_INPUT
        self.raw_file = kwargs.get('raw_file') or DEFAULT_RAW
        self.filtered_file = kwargs.get('filtered_file') or DEFAULT_FILTERED
        self.verbose = kwargs.get('verbose') or True

    def list_categories(self):
        _touch_output(self.raw_file)

        buffer = []
        num_categories = 0
        dump_iterator = DumpIterator(in_file=self.in_file,
                                     keep_lists=True,
                                     keep_namespaced_articles=True,
                                     keep_redirects=True)

        for article in dump_iterator.iterate(offset_ratio=0):
            article = [line.strip() for line in article]
            title = None
            for line in article:
                if line.startswith('<title>'):
                    title = line.replace('<title>', '').replace('</title>', '')
                    title = ArticleTitle(title)
                    break

            if title and title.namespace == 'Category':
                row = _parse_article(article, title)
                if row:
                    buffer.append(row)
                    if len(buffer) >= 10000:
                        _purge_buffer(buffer, self.raw_file)
                        num_categories += len(buffer)
                        if self.verbose:
                            print('Input file line #%d.  Categories found: %d'
                                  % (dump_iterator.line_count, num_categories))
                        buffer = []

        # Print anything still left in the buffer
        _purge_buffer(buffer, self.raw_file)

    def filter_categories(self):
        buffer = []
        with open(self.raw_file, 'r') as filehandle:
            for line in filehandle:
                parts = line.strip().split('\t')
                if len(parts) < 2:
                    continue
                category = parts[0]
                if _is_viable_category(category):
                    parents = _uniq_list(parts[1:])
                    parents = [p for p in parents if _is_viable_category(p)]
                    parents = _choose_salient_parents(parents, category)
                    if parents:
                        row = (category + '\t' + '\t'.join(parents) + '\n')
                    else:
                        row = category + '\n'
                    buffer.append(row)
        with open(self.filtered_file, 'w') as filehandle:
            filehandle.writelines(buffer)


def _touch_output(out_file):
    # Touch/truncate the output file
    with open(out_file, 'w') as filehandle:
        filehandle.write('')


def _parse_article(article, title):
    redirect_line = None
    redirect_target = None
    catlines = []
    for line in article:
        line = line.replace('<text xml:space="preserve">', '')\
            .replace('</text>', '')
        if line.startswith('{{Category redirect|'):
            redirect_line = line
        elif line.startswith('[[Category:'):
            catlines.append(line)

    if redirect_line:
        redirect_target = redirect_line.replace('{{Category redirect|', '')\
            .replace('}}', '')

    # We skip redirects, since we assume that these categories are empty
    if (redirect_target or
            _administration_category(title) or
            _hidden_category(article) or
            _stub_category(title)):
        return None
    else:
        parents = []
        for c in catlines:
            c = c.replace('[[', '').replace(']]', '')
            if c:
                c = ArticleTitle(c.split('|')[0])
                if _administration_category(c) or _stub_category(c):
                    pass
                else:
                    parents.append(c)
        row = (title.namespacestripped + '\t' +
               '\t'.join(p.namespacestripped for p in parents) + '\n')
        return row


def _administration_category(title):
    try:
        firstword = title.main.split()[0]
    except IndexError:
        return True

    if firstword.endswith('-Class') or firstword.endswith('-importance'):
        return True
    elif firstword in SKIP:
        return True
    elif 'templates' in title.main.lower():
        return True
    else:
        return False


def _hidden_category(article):
    for line in article:
        for z in HIDDEN:
            if line.lower().startswith(z):
                return True
        if '__HIDDENCAT__' in line:
            return True
    return False


def _stub_category(title):
    if title.full.endswith(' stubs'):
        return True
    else:
        return False


def _purge_buffer(buffer, out_file):
    with open(out_file, 'a') as filehandle:
        filehandle.writelines(buffer)


def _is_viable_category(category):
    catlower = category.lower()
    if re.search(r'^[0-9]', category):
        return False
    for word in STOPWORDS:
        if word in category:
            return False
    for phrase in ('articles', ' lists', 'navigational boxes', 'relations',
                   'involving', 'demograph', 'wikipedia', 'redirects'):
        if phrase in catlower:
            return False
    for phrase in ('words', 'phrases', ' slang', 'metaphors'):
        if phrase in catlower:
            return False
    for word in ('years', 'decades', 'wikipedian', 'user', 'lists of ',
                 'history of ', 'geography of ', 'landforms of ', 'images ',
                 'people '):
        if catlower.startswith(word):
            return False
    for word in (' songs', ' albums', ' singles', ' musical groups',
                 ' relations'):
        if catlower.endswith(word):
            return False

    cat_object = Category('Category:' + category)
    classification = category_classifier.category_to_group(cat_object)
    if classification in ('person', 'place', 'event', 'organization'):
        return False

    return True


def _choose_salient_parents(parents, category):
    cat_collection = CategoryCollection([Category(p) for p in parents],
                                        ArticleTitle(category))
    return [c.full for c in cat_collection.salient_categories()]


def _uniq_list(input):
    """
    Return a uniqed version of the input list (preserving order)
    """
    seen = set()
    output = []
    for item in input:
        if not item in seen:
            output.append(item)
        seen.add(item)
    return output
