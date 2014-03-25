"""
GoogleBooksApi
"""

import re
import urllib
from collections import defaultdict

from stringtools import dictionary_sort
from lex.gbn.frequency import Frequency

URL_STUB = 'http://books.google.com/ngrams/graph'
CORPORA = {
    'eng_us_2012': 17, 'eng_us_2009': 5, 'eng_gb_2012': 18, 'eng_gb_2009': 6,
    'chi_sim_2012': 23, 'chi_sim_2009': 11,'eng_2012': 15, 'eng_2009': 0,
    'eng_fiction_2012': 16, 'eng_fiction_2009': 4, 'eng_1m_2009': 1,
    'fre_2012': 19, 'fre_2009': 7, 'ger_2012': 20, 'ger_2009': 8,
    'heb_2012': 24, 'heb_2009': 9, 'spa_2012': 21, 'spa_2009': 10,
    'rus_2012': 25, 'rus_2009': 12, 'ita_2012': 22
}
FREQUENCY_MANAGER = Frequency()


class GoogleBooksApi(object):

    """
    Query Google Books NGrams data.

    Based on JB Michel's 'getNgrams.py' script:
    http://www.culturomics.org/Resources/get-ngrams

    Essentially, this screen-scrapes values from the javascript used to
    generate the graph within the HTML page. Hence this may break if Google
    make any changes to the javascript.
    """

    def __init__(self, **kwargs):
        self.query = kwargs.get('query', None)
        self.queries = kwargs.get('queries', [])
        self.corpus = kwargs.get('corpus', 'eng_2012')
        self.start = kwargs.get('start', 1750)
        self.end = kwargs.get('end', 2008)
        self.years = list(range(self.start, self.end + 1))

    def set_param(self, name, value):
        self.__dict__[name.lower()] = value

    def get_ngram_data(self, **kwargs):
        urlquery, url, results = self.get_raw_data(**kwargs)
        if not results:
            return []

        results_list = []
        for ngram, series in results:
            r = GoogleBooksResult(ngram=ngram,
                                  rawData=series,
                                  url=url,
                                  urlquery=urlquery)
            results_list.append(r)
        return results_list

    def get_raw_data(self, **kwargs):
        def clean_query(q):
            q2 = q.replace(',', '')
            q2 = q2.replace('  ', ' ').strip(" '")
            return '[' + urllib.parse.quote_plus(q2, safe='"') + ']'

        query = kwargs.get('query', self.query)
        queries = kwargs.get('queries', self.queries)
        if query:
            qlist = (query,)
        else:
            qlist = queries
        qstring = ','.join([clean_query(q) for q in qlist])

        if isinstance(self.corpus, int):
            corpus_num = self.corpus
        else:
            corpus_num = CORPORA[self.corpus]

        params = ('content=%s&year_start=%d&year_end=%d&corpus=%d&smoothing=0&share='
                  % (qstring, self.start, self.end, corpus_num))
        url = URL_STUB + '?' + params
        try:
            response = urllib.request.urlopen(url).read()
        except urllib.error.HTTPError:
            response = ''
        else:
            response = response.decode('utf-8').replace('\n', '')

        output = []
        match = re.search(r'var data = \[(.*?)</script>', response)
        if match:
            json_data = match.group(1)
            queries = re.findall('"ngram": "([^"]+)",', json_data)
            serieses = re.findall('"timeseries": \[([^\[\]]+)\]', json_data)
            if queries and len(queries) == len(serieses):
                results = []
                for series in serieses:
                    vals = [float(value.strip()) for value in series.split(',')]
                    results.append(zip(self.years, vals))
                output = zip(queries, results)

        return qstring, url, output


class GoogleBooksResult(object):

    def __init__(self, **kwargs):
        self.raw_data = kwargs.get('rawData', [])
        self.ngram = kwargs.get('ngram', '')
        self.url = kwargs.get('url', '')
        self.urlquery = kwargs.get('urlquery', '')
        self.sortcode = dictionary_sort(self.ngram)

    def tostring(self):
        return '\t'.join((self.sortcode, self.ngram, 'ALL',
                          self.decades_string(),))

    def ratio(self, year):
        for d in self.raw_data:
            if d[0] == year:
                return d[1]
        return 0

    def percentage(self, year):
        return self.ratio(year) * 100

    def absolute_counts(self):
        return [_convert_to_count(d) for d in self.raw_data]

    def absolute_count(self, year):
        for d in self.raw_data:
            if d[0] == year:
                return _convert_to_count(d)[1]
        return 0

    def counts_per_decade(self):
        decades = defaultdict(int)
        for d in self.raw_data:
            decade = int(d[0]/10) * 10
            decades[decade] += _convert_to_count(d)[1]
        for dec in decades:
            decades[dec] = int(decades[dec] + 0.5)
        return [(dec, decades[dec]) for dec in sorted(decades.keys())]

    def decades_string(self):
        return '\t'.join(['%d:%d' % (d[0], d[1]) for d in
                          self.counts_per_decade()])

    def initial(self):
        if self.sortcode:
            return self.sortcode[0]
        else:
            return 'z'


def _convert_to_count(year_tuple):
    year, fraction = year_tuple
    total = FREQUENCY_MANAGER.count(year=year)
    count = float(total) * fraction
    return year, count
