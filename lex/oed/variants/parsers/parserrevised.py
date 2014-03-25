"""
ParserRevised -- parser for handling a revised variants section
    (<vfSect>).

@author: James McCracken
"""

from lxml import etree  # @UnresolvedImport

from lex.oed.daterange import DateRange
from lex.oed.variants.variantform import VariantFormFromParser
from lex.oed.variants.parsers import utilities


class ParserRevised(object):

    """
    Parser for handling a revised variants section (<vfSect>).
    """

    def __init__(self, node):
        self.node = node

    def parse(self):
        """
        Parse the forms list and return a list of VariantForm objects.
        """
        vf_list = []
        for vfu_node in self.node.findall('.//vfUnit'):
            vf_node = vfu_node.find('.//vf')
            if vf_node is not None and vf_node.text:
                vf_unit = VfUnit(vfu_node)
                variant_form = VariantFormFromParser(vf_node,
                                                     vf_unit.date().start,
                                                     vf_unit.date().end)
                variant_form.set_grammatical_information(vf_unit.grammatical_text())
                variant_form.label = vf_unit.label()
                vf_list.append(variant_form)

        return utilities.unpack_parentheses(vf_list)


class VfUnit(object):

    """
    vfUnit element within a (revised) forms list.
    """

    def __init__(self, node):
        self.node = node

    @property
    def form(self):
        return self.node.findtext('.//vf')

    def date(self):
        dates_list = _dates_list(self.node)
        if len(dates_list) >= 1:
            return DateRange(start=min(dates_list),
                             end=max(dates_list),
                             hardEnd=True)
        else:
            return DateRange(start=0, end=0, hardEnd=True)

    def grammatical_text(self):
        cm_node = self.node.find('./cm')
        if cm_node is not None:
            return etree.tostring(cm_node, method='text', encoding='unicode')
        else:
            return ''

    def label(self):
        return self.node.findtext('./cm/la') or ''



def _dates_list(node):
    dates_list = []

    # vd_node elements not inside vdRange
    for vd_node in node.findall('./vd'):
        date = vd_node.get('date') or vd_node.text or ''
        dates_list.extend(utilities.find_range(date))

    # vd_node elements inside vdRange
    for wrapper in node.findall('./vdRange'):
        # ignore a 2nd vdRange if it's commented - probably marginal
        if dates_list and wrapper.find('./cm') is not None:
            continue
        vd_list = wrapper.findall('./vd')
        for vd_node in vd_list:
            date = vd_node.get('date') or vd_node.text or ''
            date_range = utilities.find_range(date)
            if (len(vd_list) == 1 and date != 'pre-17'):
                date_range = utilities.endless_date_range(date_range)
            dates_list.extend(date_range)

    # if nothing found so far, hunt for vd_node elements anywhere
    if not dates_list:
        for vd_node in node.findall('.//vd'):
            date = vd_node.get('date') or vd_node.text or ''
            dates_list.extend(utilities.find_range(date))

    return dates_list

