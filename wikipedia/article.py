import re

import mwparserfromhell

from . import wikipediaconfig
from .ontology.infoboxtyper import InfoboxTyper
from .ontology.categoryclassifier import CategoryClassifier
from .articletitle import ArticleTitle
from .wikilink import Wikilink
from .category import Category, CategoryCollection


INFOBOX_TYPER = InfoboxTyper()
INFOBOXES = wikipediaconfig.INFOBOXES
CATEGORY_CLASSIFIER = CategoryClassifier()
COORD_NAMES = ('latitude', 'longitude', 'latd', 'longd', 'coordinates',
               'lat_deg', 'lon_deg')
INFOBOX_PATTERN = re.compile(r'^\{\{[Ii]nfobox ([a-zA-Z -]+)')
MAIN_ARTICLE_END = wikipediaconfig.MAIN_ARTICLE_END


class Article(object):

    """
    Wikipedia article
    """

    def __init__(self, node):
        self.node = node
        self._wikitext = None
        self._wikicode = None
        self._title = None
        self._wikilinks_all = None
        self._wikilinks = None
        self._categories = None
        self._topics = None
        self._references = None
        self._images = None

        self._infobox = None
        self._infobox_type = None
        self._infobox_name = None
        self._infobox_checked = False

        self._classification_checked = False
        self._classification = None

    @property
    def title(self):
        if not self._title:
            title_node = self.node.find('./title')
            if title_node is not None:
                self._title = ArticleTitle(title_node.text)
            else:
                self._title = ArticleTitle('')
        return self._title

    @property
    def wikitext(self):
        """
        Return the unparsed wikitext (string)
        """
        if self._wikitext is None:
            text_node = self.node.find('./revision/text')
            if text_node is not None:
                self._wikitext = text_node.text or ''
            else:
                self._wikitext = ''
        return self._wikitext

    @property
    def wikicode(self):
        """
        Return the parsed wikitext (mwparserfromhell.wikicode.Wikicode object)
        """
        if not self._wikicode:
            try:
                self._wikicode = mwparserfromhell.parse(self.wikitext)
            except SystemError:
                self._wikicode = mwparserfromhell.parse('')
        return self._wikicode

    def wikicode_parses(self):
        """
        Check that the wikicode is valid, and parses under mwparserfromhell
        """
        try:
            [n for n in self.wikicode.ifilter()]
        except AttributeError:
            return False
        else:
            return True

    @property
    def length(self):
        """
        Return the number of characters in the wikicode
        (./revision/text element). We use this as our usual metric for the
        size of the article
        """
        return len(str(self.wikicode))

    size = length

    #----------------------------------------------------------
    # Infobox
    #----------------------------------------------------------

    @property
    def infobox(self):
        if not self._infobox_checked:
            self._collect_infobox()
        return self._infobox

    @property
    def infobox_type(self):
        if not self._infobox_checked:
            self._collect_infobox()
        return self._infobox_type

    @property
    def infobox_name(self):
        if not self._infobox_checked:
            self._collect_infobox()
        return self._infobox_name

    def _collect_infobox(self):
        boxtemplate = None
        boxtype = None
        for template in self.wikicode.ifilter_templates():
            tname = str(template.name).replace('Automatic ', '').strip().lower()
            if tname:
                firstword = tname.split()[0].lower()
                if (firstword in INFOBOXES or
                        'infobox' in tname or
                        'taxobox' in tname):
                    boxtemplate = template
                    if firstword in INFOBOXES:
                        boxtype = firstword
                    else:
                        boxtype = 'infobox'
                    break
        if boxtemplate:
            self._infobox = boxtemplate
            self._infobox_type = boxtype
            name = template.name.strip()
            name = name.replace(boxtype, '').replace(boxtype.capitalize(), '')
            name = name.split('<')[0]  # Get rid of trailing comments
            name = name.strip()
            if name:
                self._infobox_name = name
        else:
            # If we've failed to find an infobox so far, it may be that the
            #  wikitext is not properly structured, so it may have failed
            #  to parse correctly. So we try the crude pattern-matching way
            #  instead.
            match = INFOBOX_PATTERN.search(self.wikitext)
            if match:
                self._infobox_type = 'infobox'
                self._infobox_name = match.group(1).strip()

        self._infobox_checked = True

    #----------------------------------------------------------
    # Wikilinks-related functions
    #----------------------------------------------------------

    @property
    def wikilinks(self):
        """
        Return only standard (non-namespaced) wikilinks
        """
        if self._wikilinks is None:
            self._wikilinks = [w for w in self.wikilinks_all
                               if not w.namespace]
        return self._wikilinks

    @property
    def wikilinks_all(self):
        """
        Return all wikilinks (including namespaced wikilinks, except Categories)
        """
        if self._wikilinks_all is None:
            self._collect_wikilinks()
        return self._wikilinks_all

    @property
    def images(self):
        if self._images is None:
            self._collect_wikilinks()
        return self._images

    def _collect_wikilinks(self):
        self._wikilinks_all = []
        self._categories = []
        self._images = []
        for w in self.wikicode.filter_wikilinks():
            title = str(w.title).strip().lower()
            if title.startswith('category:'):
                self._categories.append(Category(w.title))
            elif title.startswith('image:') or title.startswith('file:'):
                self._images.append(w)
            else:
                self._wikilinks_all.append(Wikilink(w.title, w.text))

    #----------------------------------------------------------
    # Categories
    #----------------------------------------------------------

    @property
    def categories(self):
        if self._categories is None:
            self._collect_wikilinks()
        return self._categories

    @property
    def salient_categories(self):
        cat_classified = [c for c in self.categories
                          if c.has_topic_classification()]
        cat_set = CategoryCollection(cat_classified, self.title)
        return cat_set.salient_categories()

    @property
    def topics(self):
        """
        Return a set of topic classifications based on the article's
        categories
        """
        if self._topics is None:
            self._topics = set()
            for category in self.salient_categories:
                self._topics = self._topics.union(category.topics)
        return self._topics

    #----------------------------------------------------------
    # Functions used to classify an article
    #----------------------------------------------------------

    @property
    def classification(self):
        """
        Return a string indicating the general classification of this article
        (or None if it has not been categorized).

        Possible return values are:
         - 'person'
         - 'place'
         - 'event'
         - 'artwork'
         - 'organization'
         - 'fictional' (fictional characters, places, etc.)
         - 'product'
         - 'chemical'
         - 'language'
         - 'species'
         - None
        """
        if not self._classification_checked:
            if self.is_a_person():
                cls = 'person'
            elif self.is_an_event():
                cls = 'event'
            elif self.is_a_place():
                cls = 'place'
            elif self.is_an_artwork():
                cls = 'artwork'
            elif self.is_fictional():
                cls = 'fictional'
            elif self.is_an_organization():
                cls = 'organization'
            elif self.is_astronomical():
                cls = 'astronomical'
            elif self.is_a_species():
                cls = 'species'
            elif self.is_a_language():
                cls = 'language'
            elif self.is_a_named_animal():
                cls = 'namedanimal'
            elif self.is_a_product():
                cls = 'product'
            elif self.is_a_chemical():
                cls = 'chemical'
            elif self.has_coordinates():
                cls = 'place'
            else:
                cls = None

            if not cls and self.title.qualifier_superordinate:
                if INFOBOX_TYPER.is_a_person(self.title):
                    cls = 'person'
                elif INFOBOX_TYPER.is_a_place(self.title):
                    cls = 'place'
                elif INFOBOX_TYPER.is_an_artwork(self.title):
                    cls = 'artwork'
                elif INFOBOX_TYPER.is_an_organization(self.title):
                    cls = 'organization'
                elif INFOBOX_TYPER.is_astronomical(self.title):
                    cls = 'astronomical'

            if not cls:
                candidates = self.classification_by_category()
                if candidates:
                    cls = candidates[0][0]
            if (not cls and
                    (self.title.is_competition() or
                    self.title.contains_date())):
                cls = 'event'

            self._classification = cls
            self._classification_checked = True
        return self._classification

    def has_persondata(self):
        if self.wikicode.filter_templates(matches='Persondata'):
            return True
        else:
            return False

    def is_a_person(self):
        if self.has_persondata():
            return True
        elif (self.infobox_type == 'infobox' and
                INFOBOX_TYPER.is_a_person(self.infobox_name)):
            return True
        return False

    def is_a_language(self):
        if self.title.is_language():
            return True
        elif (self.infobox_type == 'infobox' and
                self.infobox_name == 'language'):
            return True
        else:
            return False

    def is_a_place(self):
        if self.infobox_type == 'geobox':
            return True
        elif (self.infobox_type == 'infobox' and
                INFOBOX_TYPER.is_a_place(self.infobox_name)):
            return True
        return False

    def has_coordinates(self):
        if (self.infobox and
                self.infobox_type in ('infobox', 'geobox') and
                any(self.infobox.has(param) for param in COORD_NAMES)):
            return True

        # Articles without infobox but with title-level coordinates
        coords = (self.wikicode.filter_templates(matches='coord') or
                  self.wikicode.filter_templates(matches='coords'))
        try:
            display_position = coords[0].get('display').value
        except (IndexError, ValueError):
            pass
        else:
            if display_position == 'title':
                return True

        # Articles without coordinates, but marked as needing coordinates
        if self.wikicode.filter_templates(matches='coord missing'):
            return True

        return False

    def is_fictional(self):
        if (self.infobox_type == 'infobox' and
                INFOBOX_TYPER.is_fictional(self.infobox_name)):
            return True
        elif self.infobox_type in ('superherobox', 'superteambox'):
            return True
        for category in self.categories:
            if 'fictional' in category.main.lower():
                return True
        return False

    def is_an_organization(self):
        if (self.infobox_type == 'infobox' and
                INFOBOX_TYPER.is_an_organization(self.infobox_name)):
            return True
        else:
            return False

    def is_an_artwork(self):
        if (self.infobox_type == 'infobox' and
                INFOBOX_TYPER.is_an_artwork(self.infobox_name)):
            return True
        else:
            return False

    def is_an_event(self):
        if (self.infobox_type == 'infobox' and
                INFOBOX_TYPER.is_an_event(self.infobox_name)):
            return True
        elif self.infobox_type == 'warbox':
            return True
        elif (self.infobox_type == 'infobox' and
                self.infobox_name and
                self.infobox_name.lower().endswith(' event')):
            return True
        else:
            return False

    def is_astronomical(self):
        if self.infobox_type in ('starbox', 'galaxybox', 'planetbox'):
            return True
        elif (self.infobox_type == 'infobox' and
                INFOBOX_TYPER.is_astronomical(self.infobox_name)):
            return True
        return False

    def is_a_chemical(self):
        if self.infobox_type == 'chembox':
            return True
        elif (self.infobox_type == 'infobox' and
                INFOBOX_TYPER.is_a_chemical(self.infobox_name)):
            return True
        elif (self.wikicode.filter_templates(matches='PBB') or
                self.wikicode.filter_templates(matches='PBB_Controls')):
            return True
        else:
            return False

    def is_a_species(self):
        if self.infobox_type in ('taxobox', 'speciesbox', 'subspeciesbox'):
            return True
        else:
            return False

    def is_a_drug(self):
        if self.infobox_type == 'drugbox':
            return True
        else:
            return False

    def is_a_product(self):
        if (self.infobox_type == 'infobox' and
                INFOBOX_TYPER.is_a_product(self.infobox_name)):
            return True
        else:
            return False

    def is_a_named_animal(self):
        if (self.infobox_type == 'infobox' and
                INFOBOX_TYPER.is_a_named_animal(self.infobox_name)):
            return True
        else:
            return False

    def classification_by_category(self):
        return CATEGORY_CLASSIFIER.classification_of(self)

    #----------------------------------------------------------
    # References, images
    #----------------------------------------------------------

    @property
    def references(self):
        if self._references is None:
            self._references = [r for r in self.wikicode.filter_tags()
                                if r.tag == 'ref']
        return self._references

    #----------------------------------------------------------
    # Functions relating to the full text of the article (as plain text,
    #  rather than as wikicode)
    #----------------------------------------------------------

    @property
    def plaintext_full(self):
        return self.wikicode.strip_code()

    @property
    def plaintext_norefs(self):
        for ref in self.references:
            try:
                self.wikicode.remove(ref, recursive=True)
            except ValueError:
                pass
        for image in self.images:
            try:
                self.wikicode.remove(image, recursive=True)
            except ValueError:
                pass
        return self.wikicode.strip_code()

    @property
    def plaintext_main(self):
        text = self.plaintext_norefs
        lines = [l.strip() for l in text.split('\n')]
        lines2 = []
        for line in lines:
            line = line.strip()
            if (line.lower() in MAIN_ARTICLE_END or
                    line.startswith('Category:')):
                break
            else:
                lines2.append(line)
        return '\n'.join(lines2)


class ArticleTest(Article):

    """
    Wikipedia article -- test version. Initialized by passing in a title
    and some wikitest (both as strings), not an actual XML node.
    """

    def __init__(self, title,  wikitext):
        Article.__init__(self, None)
        self._wikitext = wikitext
        self._title = ArticleTitle(title)
