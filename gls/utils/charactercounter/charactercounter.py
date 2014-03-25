#=======================================================================
# CharacterCounter: a module for checking character counts in
#  GLS conversion projects
#
# version 1.3 (07/09/2013)
#
# James McCracken
# jmccracken@fastmail.fm
#=======================================================================

from __future__ import division
import re
import csv
from lxml import etree

summary = """
Source text: %d characters
Converted text: %d characters
Net variance: %d characters (%.2g%%)

Characters have been lost in %d entries (%.2g%% of all entries)
    (Total characters lost: %d)

Characters have been gained in %d entries (%.2g%% of all entries)
    (Total characters gained: %d)
"""
headers = ('id', 'headword', 'characters in source', 'characters in converted',
    'absolute variance', 'percentage variance', 'diff')
id_guesses = ('xrid', 'id', 'ID', 'lexid')

class CharacterCounter(object):
    """Tests source data and converted (OxMonolingML) data to check that
    character counts are (approximately) preserved.

    Keyword arguments listed below can be passed when initializing the
    CharacterCounter object. They are converted to attributes with the
    same name, so can also be set directly after creating the
    CharacterCounter object.

    Keyword arguments:
        'source_file': The path to the file containing the source XML;
        'converted_file': The path to the file containing the
            converted XML;
        'realign': If True, source and converted entries will be automatically
            realigned, based on ID. Defaults to False.

        'source_entry_tags': A list of tags used to identify an entry in
            the source data.
        'source_headword_tags':
        'source_id_attribute': The name of the ID attribute (assumed
            to be on the entry tag).
        'source_constant_adjustments': A list of adjustments made for extra
            characters deriving from particular elements.
        'source_attribute_adjustments': A list of adjustments made for extra
            characters derived by turning attributes into character data.
        'source_suppressed_elements': A list of elements to be ignored.

    The following  keyword arguments are equivalent to the 'source...'
    arguments listed above, but apply to the converted data:
        'converted_entry_tags'
        'converted_headword_tags'
        'converted_id_attribute'
        'converted_constant_adjustments'
        'converted_attribute_adjustments'
        'converted_suppressed_elements'
    """

    def __init__(self, **kwargs):
        # Set default values
        self.source_file = None
        self.source_entry_tags = ['e',]
        self.source_headword_tags = ['hw',]
        self.source_id_attribute = None
        self.source_constant_adjustments = []
        self.source_attribute_adjustments = []
        self.source_suppressed_elements = []

        self.converted_file = None
        self.converted_entry_tags = ['e',]
        self.converted_headword_tags = ['hw',]
        self.converted_id_attribute = None
        self.converted_constant_adjustments = []
        self.converted_attribute_adjustments = []
        self.converted_suppressed_elements = []
        self.realign = False

        # Override defaults with any keyword arguments
        for k, v in kwargs.items():
            self.__dict__[k] = v

    def _parse_files(self):
        """Parses the source file and converted file into two parallel lists
        of entry nodes
        """
        def parse_file(input_file, entry_tags):
            tree = etree.parse(input_file)
            element_string = ' or '.join(['self::%s' % t for t in entry_tags])
            return tree.xpath('.//*[%s]' % element_string)

        # Generate the Param objects that will be supplied to each entry
        self.source_params = Params(self.__dict__, 'source')
        self.converted_params = Params(self.__dict__, 'converted')

        print '\tParsing source file...'
        self.source_entries = [Entry(n, self.source_params) for n in
            parse_file(self.source_file, self.source_entry_tags)]
        print '\tParsing output file...'
        self.converted_entries = [Entry(n, self.converted_params) for n in
            parse_file(self.converted_file, self.converted_entry_tags)]
        print '...Parsing complete.'

    def entry_counts(self):
        try:
            self.source_entries
        except AttributeError:
            self._parse_files()

        return 'Entry counts:\n\t%s: %d\n\t%s: %d\n' % (self.source_file,
            len(self.source_entries), self.converted_file,
            len(self.converted_entries),)

    def total_variance(self):
        """Returns a string summarizing the total variance in character
        counts between the source and the converted files.
        """
        results = self._compare_entries()
        source_total = sum([n[2] for n in results])
        converted_total = sum([n[3] for n in results])
        if source_total:
            percentage = (100.0/source_total) * converted_total
        else:
            percentage = 100

        (lost_entries, lost_characters, gained_entries,
            gained_characters) = (0, 0, 0, 0)
        for n in results:
            if n[2] > n[3]:
                lost_entries += 1
                lost_characters += (n[2] - n[3])
            elif n[3] > n[2]:
                gained_entries += 1
                gained_characters += (n[3] - n[2])

        return summary % (
            source_total,
            converted_total,
            converted_total - source_total,
            percentage-100,
            lost_entries,
            (100/len(self.source_entries)) * lost_entries,
            lost_characters,
            gained_entries,
            (100/len(self.source_entries)) * gained_entries,
            gained_characters,
        )

    def log_variances(self, **kwargs):
        """Writes a .csv file logging every entry where some variance
        was found (either all variances, or variances above a specified
        threshold).

        Keyword arguments:
            'csv_file': path of the output file (defaults to a file
                called 'variances.csv' in the present working directory).
                Should have a '.csv' extension.
            'absolute_threshold': integer value specifying the minimum
                absolute variance; entries with variance below this
                threshold will not be logged. Defaults to 0.
            'percentage_threshold': integer or float value specifying
                the minimum percentage variance; entries with variance
                below this threshold will not be logged. Defaults to 0.

        The output CSV file has the following columns:
        A: entry ID (actually @xrid), as given in the converted version;
        B: entry headword, as given in the converted version;
        C: number of characters calculated for the source version;
        D: number of characters in the converted version;
        E: absolute variance (number of characters) - positive if
            the converted entry contains more characters than the source,
            negative if it contains fewer;
        F: percentage variance;
        G: short snippet of text showing the first point in the entry
            where a difference between the two entries was observed.
        """
        print '\tWriting variance log file...'
        out_file = kwargs.get('csv_file', 'variances.csv')

        results = self._compare_entries(**kwargs)
        with open(out_file, 'wb') as fh:
            csvwriter = csv.writer(fh)
            csvwriter.writerow([t.encode('utf8') for t in headers])
            for r in results:
                r[1] = r[1].encode('utf8')
                r[6] = r[6].encode('utf8')
                r[5] = '%.2g' % r[5]
                csvwriter.writerow(r)
        print '\t...Variance log file ready at %s' % out_file

    def _compare_entries(self, **kwargs):
        """Iterates through each entry in the source document and in the
        converted document (in parallel), comparing their character
        counts with each other. Entries where variance is found are
        storted in results.

        Returns a list of results (tuples with details of each entry where
        variance was found).
        """
        percentage_threshold = kwargs.get('percentage_threshold')
        absolute_threshold = kwargs.get('absolute_threshold')

        try:
            self.source_entries
        except AttributeError:
            self._parse_files()

        if self.realign:
            self._realign_entries()

        results = []
        for entry1, entry2 in zip(self.source_entries, self.converted_entries):
            source_count = entry1.adjusted_count()
            converted_count = entry2.adjusted_count()
            variance_absolute = converted_count - source_count
            variance_pcnt = ((100.0/source_count) * converted_count) - 100

            # Determine whether this entry should be stored for logging
            #  purposes (i.e. whether its variance exceeds the threshold)
            store_this = False
            if (percentage_threshold is None and
                absolute_threshold is None):
                store_this = True
            elif (percentage_threshold is not None and
                absolute_threshold is not None and
                (abs(variance_pcnt) > percentage_threshold or
                abs(variance_absolute) > absolute_threshold)):
                store_this = True
            elif (percentage_threshold is not None and
                absolute_threshold is None and
                abs(variance_pcnt) > percentage_threshold):
                store_this = True
            elif (percentage_threshold is None and
                absolute_threshold is not None and
                abs(variance_absolute) > absolute_threshold):
                store_this = True

            if store_this:
                diff = find_difference(entry1, entry2)
                result = [
                    entry2.id() or entry1.id(),
                    entry2.headword() or entry1.headword(),
                    source_count,
                    converted_count,
                    variance_absolute,
                    variance_pcnt,
                    diff
                ]
                results.append(result)

        return results

    def _realign_entries(self):
        # Build an ID index of the converted entries
        converted_index = {}
        for e in self.converted_entries:
            converted_index[e.id()] = e
        # Build a new list of converted entries, aligned with source entries
        realigned = []
        for e in self.source_entries:
            if e.id() in converted_index:
                realigned.append(converted_index[e.id()])
            else:
                dummy_node = etree.Element(self.converted_entry_tags[0])
                realigned.append(Entry(dummy_node, self.converted_params))
        self.converted_entries = realigned


class Params(object):

    def __init__(self, parameters, mode):
        for k, v in parameters.items():
            if k.startswith(mode + '_'):
                k2 = k.replace(mode + '_', '')
                self.__dict__[k2] = v
        self._convert_suppressed_tags_to_xpath()

    def _convert_suppressed_tags_to_xpath(self):
        tmp = []
        for s in self.suppressed_elements:
            s = s.strip()
            if re.search(r'^[a-zA-Z0-9_:-]+$', s):
                s = './/' + s
            tmp.append(s)
        self.suppressed_elements = tmp


class Entry(object):

    def __init__(self, node, params):
        self.node = node
        self.params = params

    def id(self):
        if self.params.id_attribute is not None:
            return self.node.get(self.params.id_attribute, '')
        else:
            vals = [self.node.get(att) for att in id_guesses if self.node.get(att)]
            if vals:
                return vals[0]
            else:
                return ''

    def headword(self):
        for t in self.params.headword_tags:
            n = self.node.find('.//%s' % t)
            if n is not None:
                return etree.tostring(n, method='text', encoding=unicode)
        return ''

    def normalized_text(self):
        try:
            return self._normalized_text
        except AttributeError:
            self._strip_node()
            t = etree.tostring(self.node, method='text',
                encoding=unicode)
            t = t.replace(' ', '').replace('\n', '').replace('\t', '').strip()
            self._normalized_text = t
            return self._normalized_text

    def flattened_text(self):
        return re.sub(r'[^a-zA-Z0-9,.;:-]', '.', self.normalized_text())

    def _strip_node(self):
        """Removes all elements identified as 'suppressed'
        """
        # First find all elements matching Xpath expressions,
        #  and convert these to <DELETE> tags
        for xp in self.params.suppressed_elements:
            for n in self.node.xpath(xp):
                n.tag = 'DELETE'
        # Then delete all <DELETE> elements
        etree.strip_elements(self.node, 'DELETE', with_tail=False)

    def character_count(self):
        return len(self.normalized_text())

    def adjusted_count(self):
        return self.character_count()+ self._adjustments()

    def _adjustments(self):
        """Calculates total adjustments which will be added to the raw
        character count.

        Adjustments may be based on:
        (a) occurrence of a given element
        (b) occurrence of an attribute
        """
        supplement = 0
        # Constant adjustments for each occurrence of given elements
        for tag, value in self.params.constant_adjustments:
            supplement += (value * len(self.node.findall('.//%s' % tag)))

        # Adjustments for occurrence of given attributes (value is
        #  the length of the attribute value)
        for tag, attribute in self.params.attribute_adjustments:
            for n in self.node.findall('.//%s' % tag):
                attvalue = n.get(attribute, '')
                supplement += len(attvalue.strip().replace(' ', ''))
            # Special handling of attributes on the entry tag, since
            #  these won't be caught by the xpath above
            if self.node.tag == tag:
                attvalue = self.node.get(attribute, '')
                supplement += len(attvalue.strip().replace(' ', ''))
        return supplement



def find_difference(entry1, entry2):
    """Extracts the first snippet of text where the source text differs from
    the converted text; returns a snippet of text c.20 characters long.

    This may not be entirely accurate, depending on how the two pieces
    of text have been manipulated.
    """
    t1 = entry1.flattened_text()
    t2 = entry2.flattened_text()
    if entry1.node.tag == 'csec':
        print entry1.id()
        print repr(t1)
        print repr(t2)
    idx = None
    for i, char in enumerate(t1):
        if i >= len(t2) or char != t2[i]:
            idx = i
            break
    if idx is not None and not entry2.normalized_text():
        return 'CONVERTED ENTRY NOT FOUND'
    elif idx is not None:
        # Extract a slice of text around the index point
        #  (ideally, 10 characters either side).
        slice_start = max(idx-10, 0)
        return ''.join(entry1.normalized_text()[slice_start:idx+10])
    else:
        return ''


if __name__ == '__main__':
    cc = CharacterCounter(
        source_file='ITDC_MON_CAMP-A-source.xml',
        converted_file='ITDC_MON_CAMP-A-oxMonolingML.xml',
        source_entry_tags=['ENTRY',],
        converted_entry_tags=['e',],
        suppressed_elements=['CatHid', 'EtymHid', 'DateHid', 'sh', 'INFLHID', 'TABS'],
        constant_adjustments=[('DATE', 1),],
        attribute_adjustments=[],
    )
    print cc.entry_counts()
    print cc.total_variance()
    cc.log_variances(percentage_threshold=5)


