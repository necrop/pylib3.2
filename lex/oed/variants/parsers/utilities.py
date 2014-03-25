"""
Utility functions used by the two forms-list parsers:
 -- find_range
 -- endless_date_range
 -- startless_date_range
 -- unpack_parentheses

@author: James McCracken
"""

import re

from lex.oed.variants import variantsconfig


DATE_CONVERSIONS = variantsconfig.DATE_CONVERSIONS
RANGE_PATTERNS = {'open_r': re.compile('(.+)(-|\u2013)$'),
                  'open_l': re.compile('^(-|\u2013)(.+)$'),
                  'closed': re.compile('^(.+)(-|\u2013)(.+)$')}
PARENTHESIS_PATTERN1 = re.compile(r'^(.+)\(([a-z][a-z]?)$')
PARENTHESIS_PATTERN2 = re.compile(r'^(.+)\(([a-z])\)(.+)$')
MINIMUM_DATE = 1000
MAXIMUM_DATE = 2050


def find_range(string):
    """
    Return the numeric date date_range represented by a <vd> string.

    The argument could come from the <vd>'s text (for an unrevised forms list)
    or from the <vd>'s date attribute (for a revised forms list).
    e.g. 'lOE', 'ME', 'pre-17', 'lME-16' '17-'

    Returns 2ple consisting of (startdate, enddate)
    """
    date_range = (0, 0)
    if string == 'pre-17':
        date_range = (1500, 1700)
    else:
        match1 = RANGE_PATTERNS['open_r'].search(string)
        match2 = RANGE_PATTERNS['open_l'].search(string)
        match3 = RANGE_PATTERNS['closed'].search(string)

        if match1 is not None:
            date_range = _convert_date_code(match1.group(1))
            date_range = endless_date_range(date_range)
        elif match2 is not None:
            date_range = _convert_date_code(match2.group(2))
            date_range = startless_date_range(date_range)
        elif match3 is not None:
            date_range1 = _convert_date_code(match3.group(1))
            date_range2 = _convert_date_code(match3.group(3))
            date_range = (date_range1[0], date_range2[1])
        else:
            date_range = _convert_date_code(string)

    if not date_range[0] or not date_range[1]:
        date_range = (0, 0)
    return date_range


def endless_date_range(date_range):
    """
    Open up a date-range so that it ends at MAXIMUM_DATE
    (i.e. in effect, it has no end date).
    """
    return (date_range[0], MAXIMUM_DATE)

def startless_date_range(date_range):
    """
    Open up a date-range so that it starts at MINIMUM_DATE
    (i.e. in effect, it has no start date).
    """
    return (MINIMUM_DATE, date_range[1])


def _convert_date_code(date_code):
    """
    Return the numeric date range represented by a <vd> date code.
    e.g. 'lOE', 'ME', '17'

    Returns 2ple consisting of (startdate, enddate)
    """
    try:
        return DATE_CONVERSIONS[date_code]
    except KeyError:
        return (0, 0)



def unpack_parentheses(vf_list):
    """
    Unpack any VariantForm whose form has letters in parenthesis,
    so that it's replaced by two VariantForm objects:
     -- one with the parenthesized letters;
     -- one without the parenthesized letters.
    """
    unpacked_list = []
    for variant_form in vf_list:
        match1 = PARENTHESIS_PATTERN1.search(variant_form.original_form)
        match2 = PARENTHESIS_PATTERN2.search(variant_form.original_form)
        if match1 is not None:
            # Adjust the existing VariantForm so that the letters in
            #  parenthesis are removed
            variant_form.reset_form(match1.group(1))
            unpacked_list.append(variant_form)

            # Create a new VariantForm for the version *with* the
            #  parenthesized letters
            variant_form2 = variant_form.clone()
            variant_form2.reset_form(match1.group(1) + match1.group(2))
            unpacked_list.append(variant_form2)
        elif match2 is not None:
            # Adjust the existing VariantForm so that the letters in
            #  parenthesis are removed
            variant_form.reset_form(match2.group(1) + match2.group(3))
            unpacked_list.append(variant_form)

            # Create a new VariantForm for the version *with* the
            #  parenthesized letters
            variant_form2 = variant_form.clone()
            variant_form2.reset_form(match2.group(1) + match2.group(2) + match2.group(3))
            unpacked_list.append(variant_form2)
        else:
            unpacked_list.append(variant_form)
    return unpacked_list

