"""
ProperNames -- functions for checking if a string is a proper name

@author: James McCracken
"""

import os
from collections import defaultdict

NAMES = defaultdict(set)
COMMON = set()


def is_proper_name(string):
    """
    Return True if the argument is a proper name.
    """
    _load_names()
    typelist = []
    for name_type, name_dict in NAMES.items():
        if name_type == 'brand':
            continue
        if string in name_dict:
            typelist.append(name_type)
    if typelist:
        return typelist
    else:
        return False

def is_first_name(string):
    """
    Return True if the argument is a first name.
    """
    _load_names()
    if string in NAMES['firstname']:
        return True
    else:
        return False

def is_surname(string):
    """
    Return True if the argument is a surname.
    """
    _load_names()
    if string in NAMES['surname']:
        return True
    else:
        return False

def is_place_name(string):
    """
    Return True if the argument is a place name.
    """
    _load_names()
    if string in NAMES['placename']:
        return True
    else:
        return False

def is_brand_name(string):
    """
    Return True if the argument is a brand name.
    """
    _load_names()
    if string in NAMES['brand']:
        return True
    else:
        return False

def is_common(string):
    """
    Return True if the argument is a common first name.
    """
    _load_names()
    if string in COMMON:
        return True
    else:
        return False

def names_list(name_type):
    """
    Return the set of all the names in a given list.
    """
    _load_names()
    name_type = name_type.lower().replace(' ', '').replace('_', '')
    name_type = name_type.rstrip('s')
    try:
        return NAMES[name_type]
    except KeyError:
        return set()

def _load_names():
    """
    Load all the names data from files.
    """
    if not NAMES:
        directory = os.path.dirname(__file__)
        for filename in [f for f in os.listdir(directory)
                         if f.endswith('.txt')]:
            name_type = filename.split('.')[0]
            if name_type.endswith('_common'):
                name_type = name_type.split('_')[0]
            with (open(os.path.join(directory, filename))) as filehandle:
                for line in filehandle:
                    line = line.strip()
                    if line[0].isupper():
                        NAMES[name_type].add(line)
                        j = line.split(' & ')
                        if len(j) == 2:
                            NAMES['unknown'].add(j[0])
                            NAMES['unknown'].add(j[1])

                        if '_common' in filename:
                            COMMON.add(line)
