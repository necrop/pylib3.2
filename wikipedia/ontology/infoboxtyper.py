import os
import re
from functools import lru_cache

from .. import wikipediaconfig
from ..articletitle import ArticleTitle

TEMPLATES_DIR = os.path.join(wikipediaconfig.RESOURCES_DIR, 'infobox_templates')


class InfoboxTyper(object):

    """
    Used to suggest general classification of an article based on the
    infobox template it's using
    """

    template_groups = {}
    qualifier_groups = {}

    def __init__(self):
        if not InfoboxTyper.template_groups:
            load_names()

    def is_a_place(self, arg):
        """
        Return True if this infobox name is in the 'place' group
        """
        return self._belongs_to(arg, 'place')

    def is_a_person(self, arg):
        """
        Return True if this infobox name is in the 'person' group
        """
        return self._belongs_to(arg, 'person')

    def is_an_organization(self, arg):
        """
        Return True if this infobox name is in the 'organization' group
        """
        return self._belongs_to(arg, 'organization')

    is_an_organisation = is_an_organization

    def is_an_event(self, arg):
        """
        Return True if this infobox name is in the 'event' group
        """
        return self._belongs_to(arg, 'event')

    def is_an_artwork(self, arg):
        """
        Return True if this infobox name is in the 'event' group
        """
        return self._belongs_to(arg, 'artwork')

    def is_a_product(self, arg):
        """
        Return True if this infobox name is in the 'product' group
        """
        return self._belongs_to(arg, 'product')

    def is_fictional(self, arg):
        """
        Return True if this infobox name is in the 'fiction' group
        """
        return self._belongs_to(arg, 'fiction')

    def is_astronomical(self, arg):
        """
        Return True if this infobox name is in the 'astronomical' group
        """
        return self._belongs_to(arg, 'astronomical')

    def is_a_chemical(self, arg):
        """
        Return True if this infobox name is in the 'chemical' group
        """
        return self._belongs_to(arg, 'chemical')

    def is_a_named_animal(self, arg):
        """
        Return True if this infobox name is in the 'named animal' group
        """
        return self._belongs_to(arg, 'namedanimal')

    def _belongs_to(self, arg, group):
        if isinstance(arg, ArticleTitle):
            return self._qualifier_belongs_to(arg, group)
        else:
            return self._template_belongs_to(arg, group)

    def _template_belongs_to(self, template_name, group):
        if not template_name or not group in InfoboxTyper.template_groups:
            return False
        template_name = clean_template_name(template_name)
        if template_name in InfoboxTyper.template_groups[group]:
            return True
        else:
            return False

    def _qualifier_belongs_to(self, title, group):
        if not title.qualifier or not group in InfoboxTyper.template_groups:
            return False

        q1 = clean_template_name(title.qualifier)
        if (q1 in InfoboxTyper.template_groups[group] or
                q1 in InfoboxTyper.qualifier_groups[group]):
            return True

        if title.qualifier_superordinate:
            q2 = clean_template_name(title.qualifier)
            if (q2 in InfoboxTyper.template_groups[group] or
                    q2 in InfoboxTyper.qualifier_groups[group]):
                return True

        return False


def load_names():
    for filename in os.listdir(TEMPLATES_DIR):
        group = os.path.splitext(filename)[0]
        InfoboxTyper.template_groups[group] = set()
        InfoboxTyper.qualifier_groups[group] = set()
        with open(os.path.join(TEMPLATES_DIR, filename)) as filehandle:
            for line in filehandle:
                if line.startswith('~'):
                    line = line.strip('~ ')
                    target = InfoboxTyper.qualifier_groups[group]
                else:
                    target = InfoboxTyper.template_groups[group]
                line = clean_template_name(line)
                if line:
                    target.add(line)


@lru_cache(maxsize=8)
def clean_template_name(template_name):
    text = template_name.lower().replace('{', '').replace('}', '')\
        .replace('_', ' ').replace('.', '')\
        .replace(' begin', '').strip()
    text = re.sub(r'<!--.*$', '', text)
    text = text.replace('infobox', '').strip()
    text = re.sub(r' \([a-z -]+\)$', '', text)
    text = text.replace(' ', '').replace('-', '').strip()
    return text
