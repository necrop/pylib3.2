"""
DateRange -- date range e.g. for an entry or sense

@author: James McCracken
"""

import math

from lxml import etree  # @UnresolvedImport

MINIMUM_DATE = 1200
MINIMUM_DATE_PROXY = 1100
MAXIMUM_DATE = 2050
# Used when fuzzing dates
GRANULARITY = {'me': 100, 'eme': 50, 'mod': 50}


class DateRange(object):

    """
    Date-range class: start and end of a date range, e.g. as defined by the
    first and last quotations of an entry or sense.

    Keyword arguments:
     -- start (int, required): the first date of the range
     -- end (int, required): the last date of the range
     -- lastDocumented (int):
     -- estimated: True if this is an estimated date (defaults to False)
     -- obs: True if the entry, sense, etc. is obsolete (defaults to False)
     -- hardEnd: if True, the value of 'end' will always be used for
         the end date; the projected end date will never be used.
     -- node: a <dateRange> node

    If the 'node' keyword is given, values will be parsed from the XML node.
    All other arguments will be ignored.
    """

    def __init__(self, **kwargs):  #
        node = kwargs.get('node')
        if node is not None:
            self.start = int(node.get('start', 0))
            self.end = int(node.get('end', 0))
            self.is_estimated = bool(node.get('estimate', False))
            self.explicit_obs = bool(node.get('obsolete', False))
            self.last_documented = kwargs.get('lastDocumented', None)
            if self.last_documented is not None:
                self.last_documented = int(self.last_documented)
            self.hard_enddate = False
            if node.get('startExact'):
                self.set_exact('start', node.get('startExact'))
                self.set_exact('end', node.get('endExact'))

        else:
            start = int(kwargs.get('start') or 0)
            end = int(kwargs.get('end') or 0)
            if start > 2099 or start < 500:
                start = 0
            if end > 2099 or end < 500:
                end = 0

            self.start = start
            self.end = end
            self.last_documented = kwargs.get('lastDocumented', None)
            self.is_estimated = bool(kwargs.get('estimated', False))
            self.explicit_obs = bool(kwargs.get('obs', False))
            self.hard_enddate = bool(kwargs.get('hardEnd', False))

        if self.explicit_obs or self.end < 1700:
            self.assumed_obs = True
        else:
            self.assumed_obs = False
        # Keep track of the original start and end dates
        # (in case self.start and self.end get adjusted later on).
        self.src = {'start': self.start, 'end': self.end}

    def __repr__(self):
        return '<DateRange: %s>' % self.to_string()

    def to_string(self, **kwargs):
        """
        Return a string representation of the date range.
        """
        if kwargs.get('exact') and self.exact('start') and self.exact('end'):
            return '%d\u2014%d' % (self.exact('start'), self.exact('end'))
        else:
            return '%d\u2014%d' % (self.start, self.projected_end())

    def year(self, year_type):
        """
        Return the year of the type specified.

        Argument should be one of the following:
         -- 'start' or 'first'
         -- 'end' or 'last'
         -- 'projected' or 'projected_end'
        """
        if year_type in ('start', 'first'):
            return self.start
        elif year_type in ('end', 'last'):
            return self.end
        elif year_type in ('projected', 'projected_end'):
            return self.projected_end()
        else:
            return None

    def _has_hard_end_date(self):
        """
        Return True if the 'hardEnd' flag was set, indicating that
        the end date is absolute and that a projected end should
        not be used.
        """
        return self.hard_enddate

    def projected_end(self):
        """
        Return the projected end date (the MAXIMUM_DATE constant)
        if this is a non-obsolete sense.

        If it's an obsolete sense, or if the 'hardEnd' argument
        was set to True, the actual end date will be returned.
        """
        if self._has_hard_end_date():
            return self.end
        elif not self.is_obsolete():
            return MAXIMUM_DATE
        else:
            return self.end

    projected = projected_end

    def span(self):
        """
        Return the span (number of years between start date and
        (projected) end date).
        """
        if self.projected_end() == self.start:
            return 1
        else:
            return self.projected_end() - self.start

    def reset(self, year_type, value):
        """
        Reset start or end to a new value.
        """
        if value is None:
            value = 0
        if year_type == 'start':
            self.start = int(value)
        elif year_type == 'end':
            self.end = int(value)

    def to_xml(self, **kwargs):
        """
        Return an XML <dateRange> node storing the date-range information.

        If the keyword argument 'serialized' is set to True, returns
        a serialized (string) version of the node.

        Typically looks something like this:
        <dateRange end="1993" start="1425" projected="2050"/>
        <dateRange end="1623" start="1480" projected="1623" obsolete="True"/>
        """
        omit_projected = kwargs.get('omitProjected', False)
        fuzzed = kwargs.get('fuzzed', False)
        serialized = kwargs.get('serialized', False)

        if fuzzed:
            date1, date2, date3 = (self.fuzz('start'),
                                   self.fuzz('end'),
                                   self.fuzz('projected'))
        else:
            date1, date2, date3 = (self.start,
                                   self.end,
                                   self.projected_end())
        if omit_projected:
            date2 = date3

        node = etree.Element('dateRange',
                             start=str(date1),
                             end=str(date2),)
        if not omit_projected:
            node.set('projected', str(date3))
        if fuzzed:
            node.set('startExact', str(self.start))
            node.set('endExact', str(self.end))
        if self.last_documented is not None:
            node.set('lastDocumented', str(self.last_documented))
        if self.is_estimated:
            node.set('estimate', 'True')
        if self.is_marked_obsolete():
            node.set('obsolete', 'True')

        if serialized:
            return etree.tostring(node, encoding='unicode')
        else:
            return node

    xml = to_xml

    def fuzz(self, year_type):
        """
        Return an approximate version of the year.

        Approximates to the nearest 50 years if it's a modern date,
        or to the nearest 100 years if Middle English or earlier.

         -- If it's a start year, this will approximate *down*;
         -- If it's an end year, this will approximate *up*.

        Argument should be one of the following:
         -- 'start' or 'first'
         -- 'end' or 'last'
         -- 'projected' or 'projected_end'
        """
        fuzzed_year = 0
        if year_type in ('start', 'first'):
            fuzzed_year = _fuzz_floor(self.year(year_type))
        elif year_type in ('end', 'last', 'projected', 'projected_end'):
            fuzzed_year = _fuzz_ceil(self.year(year_type))
        if fuzzed_year and fuzzed_year < MINIMUM_DATE:
            return MINIMUM_DATE_PROXY
        elif fuzzed_year and fuzzed_year > MAXIMUM_DATE:
            return MAXIMUM_DATE
        else:
            return fuzzed_year

    def constrain(self, window, in_place=False):
        """
        Constrain the dates to a given start/end window.

        Argument is a 2ple of two ints, representing the start
            and end of the window; or a 3ple of three ints,
            representing the start, end, and projected end of the
            window.

        Returns a 2ple of two ints, representing a start and end date:
         -- The DateRange's own start date or the window start date,
            whichever is the later.
         -- The DateRange's own (projected) end date or the window
            end date, whichever is the earlier.
        """
        window_start, window_end = (window[0], window[-1])
        if (not self.start or
            (window_start and self.start < window_start)):
            start = window_start
        else:
            start = self.start

        if (not self.projected_end() or
            (window_end and self.projected_end() > window_end)):
            end = window_end
        else:
            end = self.projected_end()

        if in_place:
            self.reset('start', start)
            self.reset('end', end)

        return (start, end)

    #==============================================
    # Functions related to obsoleteness
    #==============================================

    def is_obsolete(self):
        """
        Return True if the range appears to be obsolete.

        (Either explicitly marked obsolete, or has an end date
        earlier than 1700.)
        """
        return self.assumed_obs

    def is_marked_obsolete(self):
        """
        Return True if the range is explicitly marked as obsolete.
        """
        return self.explicit_obs

    def set_obsolete(self, value):
        """
        Set obsolete to True or False (overriding what was set
        on initialization).
        """
        self.assumed_obs = bool(value)

    #==============================================
    # Merging/comparison with other DateRange objects
    #==============================================

    def extend_range(self, other):
        """
        Use another DateRange object to extend the range, if the
        new DateRange has an earlier start date or a later end date.
        """
        # If necessary, extend the start date to an earlier start date
        if (other.start != 0 and
            (other.start < self.start or self.start == 0)):
            self.reset('start', other.start)
        # If necessary, extend the end date to a later end date
        if other.end > self.end:
            self.reset('end', other.end)
        # If necessary, reset obsoleteness marker to False
        if self.is_obsolete() and not other.is_obsolete():
            self.set_obsolete(False)

    def overlap(self, other):
        """
        Find the overlap between two DateRange objects.

        Argument: another DateRange object

        Returns None if there's no overlap; otherwise, returns a new
        DateRange object representing the overlap.
        """
        # If one date range is a subset of the other
        if (self.start >= other.start and
            self.projected_end() <= other.projected_end()):
            return DateRange(start=self.start, end=self.end, hardEnd=True)
        if (other.start >= self.start and
            other.projected_end() <= self.projected_end()):
            return DateRange(start=other.start, end=other.end, hardEnd=True)

        # If there's no overlap at all
        if (self.projected_end() and
            other.start and
            self.projected_end() < other.start):
            return None
        if (self.start and
            other.projected_end() and
            self.start > other.projected_end()):
            return None

        # If one date range overlaps the other
        if self.start < other.start:
            start = other.start
        else:
            start = self.start
        if self.projected_end() > other.projected_end():
            end = other.projected_end()
        else:
            end = self.projected_end()
        return DateRange(start=start, end=end, hardEnd=True)

    #===================================================
    # Exact value (used when the main values have been fuzzed)
    #===================================================

    def set_exact(self, year_type, year):
        """
        Store an exact value.
        """
        year = int(year) or 0
        try:
            self._exact
        except AttributeError:
            self._exact = {}
        self._exact[year_type] = year

    def exact(self, year_type):
        """
        Retrieve an exact value (if set previously with set_exact()).
        """
        try:
            return self._exact[year_type]
        except (AttributeError, KeyError):
            return self.year(year_type)


def _fuzz_ceil(year):
    """
    Approximate upwards (to the nearest 50/100 years *above* the date given).
    """
    year = float(year) + 0.5
    if year < 1500:
        return int(math.ceil(year / GRANULARITY['me']) * GRANULARITY['me'])
    elif year < 1700:
        return int(math.ceil(year / GRANULARITY['eme']) * GRANULARITY['eme'])
    else:
        return int(math.ceil(year / GRANULARITY['mod']) * GRANULARITY['mod'])


def _fuzz_floor(year):
    """
    Approximate downwards (to the nearest 50/100 years *below* the date given).
    """
    year = float(year)
    if year < 1500:
        return int(math.floor(year / GRANULARITY['me']) * GRANULARITY['me'])
    elif year < 1700:
        return int(math.floor(year / GRANULARITY['eme']) * GRANULARITY['eme'])
    else:
        return int(math.floor(year / GRANULARITY['mod']) * GRANULARITY['mod'])
