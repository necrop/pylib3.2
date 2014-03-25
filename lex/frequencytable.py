"""
FrequencyTable -- Table of frequency values, for a range of periods.

@author: James McCracken
"""

from collections import defaultdict, namedtuple
import math

import numpy
from lxml import etree  # @UnresolvedImport

from regexcompiler import ReMatcher

PARSED_LABELS = dict()
VALID_YEARS = range(1750, 2020, 10)
MOVING_AVERAGE_WINDOWSIZE = ((1900, 6), (1950, 4), (2050, 2))
YEAR_TO_PERIOD_CACHE = dict()


class FrequencyTable(object):

    """
    Table of frequency values, for a range of periods.

    Can be initialized from an existing table (XML node) or from a
    dictionary of frequency values mapped to periods
    """

    PeriodValues = namedtuple('PeriodValues', ['frequency', 'log',
                                               'band', 'estimate'])

    def __init__(self, **kwargs):
        self._wordclass_method = None
        if kwargs.get('node') is not None:
            node = kwargs.get('node')
            self.data = self._parse_node(node)
            self._wordclass_method = node.get('wcMethod', None)
            if self._wordclass_method == 'singleton':
                self._wordclass_method = None
        else:
            for kw in ('data', 'values', 'frequencies'):
                if kwargs.get(kw):
                    self.data = self._parse_values(kwargs.get(kw))
                    break
            else:
                self.data = {}
        self.recalculate_logs()

    def _parse_node(self, node):
        """
        Populate the table by parsing values from a XML node.

        The XML node should be a <frequency> table; see self.xml()
        for the form this takes.
        """
        table = {}
        for period_node in node.findall('./period'):
            period = period_node.get('label')
            estimate = period_node.get('estimate')

            if estimate is None or estimate.lower() == 'false':
                estimate = False
            else:
                estimate = True

            log_value = period_node.get('fLog', None)
            if log_value is not None:
                log_value = float(log_value)

            table[period] = self.PeriodValues(float(
                period_node.get('fPerMillion', 0)), log_value,
                int(period_node.get('band', 15)), estimate)
        return table

    def _parse_values(self, input_data):
        """
        Populate the table by parsing values from input data.

        The input data should be a dictionary where keys are periods,
        and each value is one of:
         -- a dictionary;
         -- a PeriodValues namedtuple object;
         -- a float representing the raw frequency.
        """
        table = {}
        for period, values in input_data.items():
            if isinstance(values, dict):
                estimate = False
                for est_label in ('e', 'est', 'estimate', 'estimated'):
                    if est_label in values:
                        estimate = values[est_label]
                        break
                fpm = float(0)
                for f_label in ('f', 'fpm', 'frequency', 'fPerMillion'):
                    if f_label in values:
                        fpm = values[f_label]
                        break
                table[period] = self.PeriodValues(fpm, None, None, estimate)
            elif isinstance(values, self.PeriodValues):
                table[period] = values
            elif isinstance(values, float):
                table[period] = self.PeriodValues(values, None, None, False)
        return table

    def frequencies(self):
        """
        Return simple dictionary of periods and their frequencies
        """
        return {period: values.frequency for period, values
                in self.data.items()}

    def interpolated(self):
        try:
            return self._interpolated
        except AttributeError:
            self._interpolated = _calculate_interpolation(self)
            return self._interpolated

    def moving_average(self):
        try:
            return self._moving_average
        except AttributeError:
            self._moving_average = _calculate_moving_average(self)
            return self._moving_average

    def wordclass_method(self):
        """
        ???
        """
        try:
            self._wordclass_method
        except AttributeError:
            return None
        else:
            if self._wordclass_method is None:
                return 'singleton'
            else:
                return self._wordclass_method

    def frequency(self, **kwargs):
        """
        Return a raw frequency value from the frequency table.

        Keyword arguments:
         -- 'period'
         -- 'year'
         -- 'interpolated' (defaults to False)
        Defaults to 'modern' if no arguments are supplied.
        """
        period = kwargs.get('period', None)
        year = kwargs.get('year', None)
        interpolated = kwargs.get('interpolated', False)

        if year is not None and interpolated:
            fvalue = numpy.interp(year, [i[0] for i in self.interpolated()],
                                  [i[1] for i in self.interpolated()])
        elif year is not None:
            period = _year_to_period(year, self.data)
            if period is not None and period in self.data:
                fvalue = self.data[period].frequency
            else:
                fvalue = self.data['modern'].frequency
        elif period is not None and period in self.data:
            fvalue = self.data[period].frequency
        elif period is not None:
            start, end = _parse_label(period)
            years = range(start, end)
            vals = numpy.interp(years, [i[0] for i in self.interpolated()],
                                [i[1] for i in self.interpolated()])
            if len(vals) > 0:
                fvalue = numpy.mean(vals)
            else:
                fvalue = 0
        else:
            fvalue = self.data['modern'].frequency
        return fvalue

    def band(self, **kwargs):
        """
        Return the logarithmic band for a given period from the frequency table.

        Keyword arguments:
         -- 'period'
         -- 'year'
        Defaults to 'modern' if no arguments are supplied.
        """
        period = kwargs.get('period', None)
        year = kwargs.get('year', None)
        if year is not None:
            period = _year_to_period(year, self.data)
        if period in self.data:
            return self.data[period].band
        else:
            return self.data['modern'].band

    def log(self, **kwargs):
        """
        Return the log-10 frequency for a given period from the frequency table.

        Keyword arguments:
         -- 'period'
         -- 'year'
        Defaults to 'modern' if no arguments are supplied.
        """
        period = kwargs.get('period', None)
        year = kwargs.get('year', None)
        if year is not None:
            period = _year_to_period(year, self.data)
        if period in self.data:
            return self.data[period].log
        else:
            return self.data['modern'].log

    def delta(self, period1, period2):
        """
        Return change from one period to another
        (as a ratio of the frequency at the start).
        """
        if isinstance(period1, int) and isinstance(period2, int):
            frequency1 = self.frequency(year=period1)
            frequency2 = self.frequency(year=period2)
        else:
            frequency1 = self.frequency(period=period1)
            frequency2 = self.frequency(period=period2)
        if frequency1 < 0.00000001:
            return None
        else:
            return frequency2 / frequency1

    def xml(self, **kwargs):
        """
        Return a <frequency> XML node representing the frequency table.

        As document, the XML node would look something like this:

        <frequency>
          <period label="1750-59" fPerMillion="0.15" band="5" fLog="-0.824"/>
          <period label="1760-69" fPerMillion="0.14" band="5" fLog="-0.854"/>
          [...]
          <period label="1990-99" fPerMillion="0.95" band="5" fLog="-0.0223"/>
          <period label="2000-" fPerMillion="0.97" band="5" fLog="-0.0132"/>
          <period label="modern" fPerMillion="0.88" band="5" fLog="-0.0555"/>
        </frequency>

        Keyword arguments:
         -- frequency (defaults to True): if True, raw frequency values
              are included ('fPerMillion' attribute)
         -- band (defaults to True): if True, logarithmic band values
              are included ('band' attribute)
         -- log (defaults to True): if True, logarithmic frequency values
              are included ('fLog' attribute)
         -- estimate (defaults to True): if True, an 'estimate=True'
              attribute is included for values which have been estimated.
         -- serialized (defaults to False): if True, a serialized
              string is returned, rather than a node.
        """
        include_frequency = kwargs.get('frequency', True)
        include_band = kwargs.get('band', True)
        include_log = kwargs.get('log', True)
        include_estimate = kwargs.get('estimate', True)

        node = etree.Element('frequency')
        for period, values in sorted(self.data.items()):
            pnode = etree.SubElement(node, 'period', label=period,)
            if include_frequency:
                pnode.set('fPerMillion', '%0.2g' % values.frequency)
            if include_band:
                pnode.set('band', str(values.band))
            if include_log and values.log is not None:
                pnode.set('fLog', '%0.3g' % values.log)
            if include_estimate and values.estimate == True:
                pnode.set('estimate', 'True')

        if bool(kwargs.get('serialized')):
            return etree.tounicode(node)
        else:
            return node

    to_xml = xml

    def display(self):
        """
        Return a human-readable string giving a quick summary of
        the table (mainly for debugging purposes).
        """
        lines = []
        for period, values in sorted(self.data.items()):
            line = '%s: %.2g per million (band %d)' % (period,
                                                       values.frequency,
                                                       values.band)
            lines.append(line)
        return '\n'.join(lines)

    def trace(self):
        """
        Print the output produced by self.display() to the console.
        """
        print('-----------------------------------')
        print(self.display())
        print('-----------------------------------')

    def recalculate_logs(self):
        """
        Recalculate the log-frequency and band values for each element
        in the table (useful if raw values have been adjusted).
        """
        for period, values in self.data.items():
            new_values = self.PeriodValues(values.frequency,
                                           _log_frequency(values.frequency),
                                           _log_band(values.frequency),
                                           values.estimate)
            self.data[period] = new_values

    def mean_average(self, **kwargs):
        """
        Return the mean average frequency across the period range.

        The keyword argument ignoreZeroes=True causes zero values to be
        ignored (before the word was coined, or after it went obsolete).
        """
        if kwargs.get('ignoreZeroes', True):
            return numpy.mean([d[1] for d in self.interpolated() if d[1] > 0])
        else:
            return numpy.mean([d[1] for d in self.interpolated()])

    def max_frequency(self):
        """
        Return the highest frequency in the table.
        """
        return max([d[1] for d in self.interpolated()])

    def min_frequency(self):
        """
        Return the lowest frequency in the table.
        """
        return min([d[1] for d in self.interpolated()])

    #=========================================================
    # Interaction with other another FrequencyTable instance
    #=========================================================

    def compare(self, other, **kwargs):
        """
        Compare frequencies between two tables, for a given period.

        First argument should be another FrequencyTable object.
        """
        if other.frequency(**kwargs) < 0.00000001:
            return None
        else:
            return self.frequency(**kwargs) / other.frequency(**kwargs)

    def sum_with(self, other):
        """
        Add self to anther frequency table, and return the result
        as a new FrequencyTable object.

        (Wrapper for sum_frequency_tables().)
        """
        return sum_frequency_tables([self, other])


def sum_frequency_tables(tables):
    """
    Add to together the values contained in a list of FrequencyTables,
    and return a new FrequencyTable containing the results
    """
    sum_data = defaultdict(lambda: {'frequency': 0, 'estimate': False})
    for table in tables:
        for period, values in table.data.items():
            sum_data[period]['frequency'] += values.frequency
            if values.estimate:
                sum_data[period]['estimate'] = True
    summed = FrequencyTable(data=sum_data)
    return summed


def band_limits(mode=None):
    """
    Return a list showing the boundaries for each band, i.e. what
    range of raw frequencies each band value covers.

    Each element in the list is a 4-ple consisting of:
    (band, human-readable string, lower frequency, upper frequency)
    """
    def range_string(frequency1, frequency2):
        """
        Return a human-readable string showing the frequency range.
        """
        if frequency1 < 0.000001:
            return '0\u2014%.2g' % (frequency2,)
        elif frequency1 == frequency2:
            return '%.2g' % (frequency1,)
        else:
            return '%.2g\u2014%.2g' % (frequency1, frequency2,)

    if mode is None:
        mode = 'list'

    values = []
    frequency = 0.0000001
    last_band = 20
    while last_band > 1:
        last_band = _log_band(frequency)
        values.append((frequency, last_band,))
        frequency *= 1.01

    boundaries = {}
    for frequency, band in values:
        if not band in boundaries:
            boundaries[band] = [frequency, frequency]
        boundaries[band][1] = frequency
    for band, freq_range in boundaries.items():
        boundaries[band].append(range_string(freq_range[0], freq_range[1]))

    if mode == 'dictionary':
        return boundaries
    else:
        return [(band, values[0], values[1], values[2])
                for band, values in sorted(boundaries.items())]


#==================================================
# Private functions follow (functions used by FrequencyTable() methods)
#==================================================

def _log_frequency(frequency):
    """
    Return the log-10 value of a given raw frequency.
    """
    if frequency > 0:
        return math.log10(frequency)
    else:
        return None


def _log_band(frequency):
    """
    Return the band (1-8) into which a given raw frequency
    is binned, based on its log-10 value.
    """
    if frequency > 0:
        band = int(math.floor(math.log10(frequency)))
        if band >= 3:
            band = 3
        band = abs(band - 4)
        if band > 7:
            band = 7
    else:
        band = 8
    return band


def _log_e_band(frequency):
    """
    Like _log_band(), but based on log-e to give a 1-15 band scheme.
    """
    if frequency > 0:
        band = int(math.floor(math.log10(frequency)))
        if band >= 6:
            band = 6
        band = abs(band - 7)
        if band > 14:
            band = 14
    else:
        band = 15
    return band


def _parse_label(label):
    """
    Parse a date-range label of the kind given in the XML representation
    of a frequency table; return a (start, end) tuple corresponding
    to the label string.
    """
    try:
        return PARSED_LABELS[label]
    except KeyError:
        label_lower = label.lower().strip(' .')
        match = ReMatcher(label_lower)
        if match.search(r'^(modern|mod)$'):
            start = 1970
            end = 2008
        elif match.search(r'^(\d{4})-(\d\d)$'):
            start = int(match.group(1))
            end = (int(start / 100) * 100) + int(match.group(2))
        elif match.search(r'^(\d{4})-(\d)$'):
            start = int(match.group(1))
            end = (int(start / 10) * 10) + int(match.group(2))
        elif match.search(r'^(\d{4})-$'):
            start = int(match.group(1))
            end = 2008
        elif match.search(r'^(\d{4})$'):
            start = end = int(match.group(1))
        else:
            start = end = 0
        PARSED_LABELS[label] = (start, end)
        return PARSED_LABELS[label]


def _year_to_period(year, freq_dict):
    """
    Convert a year (int) to the best-matching period given in the
    frequency table.
    """
    if not year in YEAR_TO_PERIOD_CACHE:
        match = None
        for period in freq_dict.keys():
            if period != 'modern':
                start, end = _parse_label(period)
                if start <= year <= end:
                    match = period
                    break
        if match is not None:
            YEAR_TO_PERIOD_CACHE[year] = match
        else:
            YEAR_TO_PERIOD_CACHE[year] = 'out of range'
    return YEAR_TO_PERIOD_CACHE[year]


def _calculate_interpolation(instance):
    """
    Return a list of interpolated values. This will include any explicit
    values in the table itself, plus all other decades in the period
    from 1750 to 2010.

    Each element of the list is a 2ple consisting of (year, frequency).
    """
    xpoints = list()  # periods
    ypoints = list()  # frequencies
    for start, end in [_parse_label(label) for label in
                       sorted(instance.data.keys())
                       if label != 'modern']:
        midpoint = int(numpy.mean((start, end,)))
        xpoints.append(midpoint)
        ypoints.append(instance.frequency(year=midpoint))

    # Pad date range with zeroes up to the first non-zero value - this
    #  is to forestall the interpolation of non-zero values before
    #  the actual first non-zero value, which would give the
    #  impression that the first use was earlier
    first_nonzero_year = None
    for year, frequency in zip(xpoints, ypoints):
        if frequency > 0.0000001:
            first_nonzero_year = year
            break
    if (first_nonzero_year is not None and
            first_nonzero_year > xpoints[0]):
        zeroes = [(y, 0) for y in
                  range(xpoints[0], first_nonzero_year, 10)]
        nonzeroes = [(y, f) for y, f in zip(xpoints, ypoints)
                     if y >= first_nonzero_year]
        xpoints = [d[0] for d in zeroes] + [d[0] for d in nonzeroes]
        ypoints = [d[1] for d in zeroes] + [d[1] for d in nonzeroes]

    frequencies = numpy.interp(VALID_YEARS, xpoints, ypoints)
    return [(y, f) for y, f in zip(VALID_YEARS, frequencies)]


def _calculate_moving_average(instance):
    """
    Return a list of frequency values smoothed using a moving-average
    algorithm.

    Each element of the list is a 2ple consisting of (year, frequency).
    """
    averaged_y = []
    for i, datapoint in enumerate(instance.interpolated()):
        windowsize = None
        for block in MOVING_AVERAGE_WINDOWSIZE:
            if datapoint[0] < block[0]:
                windowsize = block[1]
                break
        span = windowsize // 2
        first = max(i - span, 0)
        last = min(i + span + 1, len(instance.interpolated()))
        window = instance.interpolated()[first:last]
        if datapoint[1] == 0 or not window:
            average = 0
        else:
            average = numpy.mean([datapoint[1] for datapoint in window])
        averaged_y.append(average)

    return [(yr, f) for yr, f in
            zip([d[0] for d in instance.interpolated()], averaged_y)]
