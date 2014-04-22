"""
VariantsLister - System for caching variant-forms lists as XML.

@author: James McCracken
"""

import os

from lxml import etree  # @UnresolvedImport

from lex.entryiterator import EntryIterator
from lex.oed.daterange import DateRange
from lex.lemma import Lemma
from lex.inflections.spellingconverter import SpellingConverter
from lex.oed.variants import variantscache
from lex.oed.variants import variantsconfig
from lex import lexconfig

DEFAULT_INPUT = lexconfig.OEDLATEST_TEXT_DIR
DEFAULT_OUTPUT = lexconfig.OED_VARIANTS_DIR

BASECLASSES = variantsconfig.BASECLASSES
FILE_SIZE = variantsconfig.CACHE_FILE_SIZE

# Since prefix/suffix entries have arbitrary quotation evidence (if any),
#  we use this to supply a usable date range
AFFIX_DATE = DateRange(start=variantsconfig.AFFIX_DATES[0],
                       end=variantsconfig.AFFIX_DATES[0])
US_CONVERTER = SpellingConverter()


class VariantsLister(object):

    """
    Method for iterating through the OED, generating a parsed
    variant-forms list for each entry, and storing the results as a series
    of XML documents.

    This can then be read back into memory using VariantsCache.

    >>> lister = VariantsLister(in_dir, out_dir)
    >>> lister.list_variants()
    """

    def __init__(self, **kwargs):
        self.in_dir = kwargs.get('in_dir') or DEFAULT_INPUT
        self.out_dir = kwargs.get('out_dir') or DEFAULT_OUTPUT
        self.filecount = 0
        self.entry = None
        self.root = None
        self.buffersize = 0

    def list_variants(self):
        """
        Main process for iterating through OED and writing output
        XML documents.

        >>> VariantsLister(in_dir, out_dir).list_variants()
        """
        self._clear_outdir()
        self._initialize_root()
        iterator = EntryIterator(path=self.in_dir,
                                 dictType='oed',
                                 verbosity='low',
                                 # fileFilter='oed_[K].xml',
                                 fixLigatures=True)
        for entry in iterator.iterate():
            self.entry = entry
            self._process_entry()
            if self.buffersize >= FILE_SIZE:
                self._writebuffer()
                self._initialize_root()
        # Write a file for anything still left in the buffer after the
        #  entry iterator has completed
        self._writebuffer()

    def _clear_outdir(self):
        """
        Delete everything from the directory to which output is
        is going to be written.
        """
        for filename in os.listdir(self.out_dir):
            os.unlink(os.path.join(self.out_dir, filename))

    def _initialize_root(self):
        """
        Start a new XML root (for a new output document).
        """
        self.root = etree.Element('entries')
        self.buffersize = 0

    def _process_entry(self):
        """
        Process an individual OED entry:
         -- turn its <vfSect> or <vfSectLoose> into a variant-forms list;
         -- turn this into a XML node;
         -- append this XML node to the current XML root.
        """
        entry_tree = etree.Element('e',
                                   id=self.entry.id,
                                   vfsect=self.entry.variants().revised_status(),
                                   size=str(self.entry.num_quotations_main()))
        hw_node = etree.Element('hw')
        hw_node.text = self.entry.headword
        entry_tree.append(hw_node)
        entry_tree.append(self.entry.date().xml())

        # Add entry headwords to the list of unmarked variants
        for headword in self.entry.headwords():
            if (headword.is_affix() and
                not self.entry.lemma_manager().is_affix()):
                pass
            else:
                self.entry.variants().append('unmarked',
                                             headword,
                                             self.entry.date().start,
                                             self.entry.date().projected_end())
        # Check that the variant matching the headword is marked
        #  appropriately (shouldn't be regional, irregular, etc.)
        self._check_headword_marking()

        # Add US spelling of the headword if not already included
        self._add_us_spelling()

        for block in self.entry.s1blocks():
            # Set the date range window, and number of quotations
            if self.entry.lemma_manager().is_affix():
                s1date = AFFIX_DATE
                num_quotations = self.entry.num_quotations()
            elif len(self.entry.s1blocks()) == 1:
                s1date = self.entry.date()
                num_quotations = self.entry.num_quotations_main()
            else:
                s1date = block.date()
                num_quotations = block.num_quotations()

            # Set the wordclass
            if (block.primary_wordclass().source == 'prefix' or
                block.primary_wordclass().source == 'suffix'):
                wordclass = block.primary_wordclass().source
                inflection_set = ['affix', ]
            else:
                wordclass = block.primary_wordclass().penn
                inflection_set = block.primary_wordclass().inflections_max()

            if wordclass is not None:
                s1_node = etree.Element('s1',
                                        lexid=block.node_id(),
                                        size=str(num_quotations),
                                        wordclass=wordclass)
                df_node = etree.Element('def')
                df_node.text = block.definition(length=50)
                s1_node.append(s1date.xml())
                s1_node.append(df_node)

                # Create forms lists for each grammatical revised_status
                for inflection in inflection_set:
                    vf_list = self._filter_by_inflection(inflection, s1date)
                    if vf_list:
                        variants_node = variantscache.to_xml(inflection,
                                                             vf_list)
                        s1_node.append(variants_node)
                        self.buffersize += len(vf_list)
                entry_tree.append(s1_node)

        # Append the xml for this entry to the main root node
        self.root.append(entry_tree)

    def _filter_by_inflection(self, inflection, block_date):
        if inflection in BASECLASSES or inflection == 'affix':
            mode = 'unmarked'
        else:
            mode = inflection
        if self.entry.variants().num_forms(mode) > 0:
            self.entry.variants().sortlist(mode)
            vf_list = self.entry.variants().formslist(mode)[:]

            for variant_form in vf_list:
                # Check if a verb form has a -en ending
                variant_form.check_en_ending(inflection, self.entry.headword)
                # Restrict dates to the dates of
                #  the containing block
                variant_form.date.constrain(
                    (block_date.start, block_date.projected_end()),
                    in_place=True)

            # Filter out stuff we don't want: anything that's
            #  still truncated or where the dates have gone wrong.
            vf_list = [vf for vf in vf_list
                       if vf.date.start <= vf.date.end]
            vf_list = [vf for vf in vf_list
                       if (not vf.is_truncated() or
                           self.entry.lemma_manager().is_affix())]
        else:
            vf_list = []
        return vf_list

    def _add_us_spelling(self):
        """
        Check if this entry should have a US spelling, and ensure that this
        is included among the variant forms.
        """
        if self.entry.date().projected_end() > 1900:
            us_form = US_CONVERTER.us_spelling(self.entry.headword)
            if us_form != self.entry.headword:
                matched = False
                for variant_form in self.entry.variants().formslist('unmarked'):
                    if variant_form.form == us_form:
                        variant_form.regional = False
                        variant_form.date.reset('end',
                                                self.entry.date().projected_end())
                        matched = True
                if not matched:
                    node = etree.XML('<vf>%s</vf>' % us_form)
                    self.entry.variants().append('unmarked',
                                                 Lemma(node),
                                                 self.entry.date().start,
                                                 self.entry.date().projected_end())

    def _check_headword_marking(self):
        """
        Make sure that the variant form corresponding to the entry headword
        is not marked as regional, irregular, etc.
        """
        for variant_form in self.entry.variants().formslist('unmarked'):
            if variant_form.form == self.entry.headword:
                variant_form.regional = False
                variant_form.irregular = False
                variant_form.date.reset('end', self.entry.date().projected_end())

    def _writebuffer(self):
        """
        Write the current root to file
        """
        fname = self._next_filename()
        with open(fname, 'w') as filehandle:
            filehandle.write(etree.tostring(self.root,
                                            # xml_declaration=True,
                                            pretty_print=True,
                                            encoding='unicode'))

    def _next_filename(self):
        """
        Return the filename to be used for the next output file.
        """
        self.filecount += 1
        filename = '%04d.xml' % self.filecount
        return os.path.join(self.out_dir, filename)


if __name__ == '__main__':
    VariantsLister().list_variants()

