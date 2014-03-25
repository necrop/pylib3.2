#-------------------------------------------------------------------------------
# Name: FixtureBuilder
# Purpose: Draws data from GEL1 to build Django fixtures, used to
#   populate database
#
# Author: James McCracken
#-------------------------------------------------------------------------------

import os
import string
from collections import defaultdict
from datetime import datetime
import json

from ..gel2config import GEL2config
from lex.gel.shared.dataiterator import DataIterator
from .topics import TopicManager
from .soundfiles import SoundfileManager


config = GEL2config()
def_length = 55 # number of characters in definition
lemma_length = 50
soundfile_length = 50
dictionaries = ("oed", "ode", "noad",)
isodate = datetime.now().isoformat()


class FixtureBuilder(object):

    def __init__(self, **kwargs):
        self.gel1_dir = kwargs.get("gel1Dir")
        self.out_dir = kwargs.get("outDir")
        self.topics_dir = kwargs.get("topics")
        self.soundfile_dir = kwargs.get("soundfiles")

    def make_fixtures(self, **kwargs):
        letters = kwargs.get("letters", string.ascii_lowercase)
        self.null_cache()

        for i, d in enumerate(dictionaries):
            self.cache["resources"].append(ResourceModel(d, i + 1))
        for t in self.topic_manager().taxonomy():
            self.cache["topics"].append(TopicModel(t))
        self.topic_manager().load_entry_data(self.topics_dir)
        self.flush_cache("ancillary")

        gel1_iterator = DataIterator(self.gel1_dir)
        for letter in letters:
            for entry in gel1_iterator.iterate(letter=letter):
                links = self.list_links(entry)
                self.store_links(links)

                soundfiles = self.soundfile_manager().find_soundfile(
                             entry.lemma, pos=entry.primary_wordclass())
                for k, v in soundfiles.items():
                    if v is not None:
                        soundfiles[k] = v[0:soundfile_length]

                emodel = EntryModel(entry, soundfiles)
                emodel.topics = self.collect_topics(links)
                self.cache["entries"].append(emodel)

                us_variant = entry.us_variant()
                for wcset in entry.wordclass_sets:
                    self.cache["wordclasses"].append(WordclassModel(wcset, entry.id))
                    self.store_types(wcset, entry.lemma, us_variant)
            self.flush_cache(letter)

    def flush_cache(self, filename):
        out_file = os.path.join(self.out_dir, filename + ".json")
        first = True
        with (open(out_file, "w")) as fh:
            fh.write("[\n")
            for k in sorted(self.cache.keys()):
                for obj in self.cache[k]:
                    if not first:
                        fh.write(",\n")
                    fh.write(obj.json())
                    first = False
            fh.write("]\n")
            fh.close()
        self.null_cache()

    def store_types(self, wcset, lemma, us_variant):
        typecats = defaultdict(list)
        for i, morphset in enumerate(wcset.morphsets):
            if (i == 0 or
                morphset.form == lemma or
                morphset.form == us_variant or
                morphset.types[0].has_frequency_table()):
                for type in morphset.types:
                    t = TypeModel(type, wcset.id)
                    if morphset.form == us_variant:
                        t.variant = "u"
                    else:
                        t.variant = "s"
                    typecats[type.wordclass].append(t)

                    # Store the type's frequency table (if any)
                    if type.has_frequency_table():
                        self.cache["freqTables"].append(
                            FreqTableModel(type.frequency_table(), type.id))

        # For all types belongng to a given p.o.s, the first can stay
        #  as variant=s (standard); the rest become variant=v (variant)
        for typeset in typecats.values():
            for i, t in enumerate(typeset):
                if i > 0 and t.variant == "s":
                    t.variant = "v"
                self.cache["types"].append(t)

    def list_links(self, entry):
        class LinkRaw(object):
            def __init__(self, gel_id, d, target):
                self.gel_id = gel_id
                self.dict_label = d
                self.target_entry = target[0]
                self.target_node = target[1]
            def target_signature(self):
                return self.target_entry + "#" + (self.target_node or "0")

        links = []
        seen = set()
        for wcset in entry.wordclass_sets:
            for d in dictionaries:
                ids = wcset.link(target=d, asTuple=True)
                target_type = wcset.link(target=d, targetType=True)
                if ids[0] is not None:
                    # Strip nodeID if the target is a main entry
                    if target_type == "entry":
                        ids = (ids[0], None)
                    lr = LinkRaw(entry.id, d, ids)
                    if not lr.target_signature() in seen:
                        links.append(lr)
                        seen.add(lr.target_signature())
        return links

    def store_links(self, links):
        for link in links:
            self.cache["links"].append(LinkModel(link))

    def collect_topics(self, links):
        ode_linked = False
        for link in links:
            if link.dict_label in ("ode", "noad"):
                ode_linked = True
        topix = set()
        for link in links:
            if link.dict_label in ("ode", "noad"):
                dtype = "odo"
            else:
                dtype = "oed"
            if link.dict_label == "oed" and ode_linked:
                pass
            else:
                topix = topix.union(self.topic_manager().find_entry_data(
                        link.target_entry, link.target_node, dtype))
        return topix

    def null_cache(self):
        self.cache = {
            "resources": [],
            "entries": [],
            "wordclasses": [],
            "types": [],
            "freqTables": [],
            "links": [],
            "topics": [],
        }

    def topic_manager(self):
        try:
            return self.tp
        except AttributeError:
            self.tp = TopicManager(
                odoTaxonomy=os.path.join(self.topics_dir, "ode_domains.txt"),
                oedTaxonomy=os.path.join(self.topics_dir, "oed_domains.txt"),
            )
            return self.tp

    def soundfile_manager(self):
        try:
            return self.sfm
        except AttributeError:
            self.sfm = SoundfileManager(dir=self.soundfile_dir)
            return self.sfm


class ResourceModel(object):

    def __init__(self, dict_name, id):
        self.pk = int(id)
        self.label = dict_name

    def json(self):
        obj = {
            "pk": self.pk,
            "model": "gel2.resource",
            "fields": {
                "label": self.label.upper(),
                "title": config.get("resource_names", self.label),
                "homepage": config.get("resource_urls", self.label),
                "url_template_entry": config.get("resource_templates_entry", self.label),
                "url_template_node": config.get("resource_templates_node", self.label),}
        }
        return json.dumps(obj, sort_keys=True, indent=2)


class TopicModel(object):

    def __init__(self, t):
        self.pk = int(t.id)
        self.name = t.name
        if t.parent is not None:
            self.parent_id = t.parent.id
        else:
            self.parent_id = None

    def json(self):
        obj = {
            "pk": self.pk,
            "model": "gel2.topic",
            "fields": {
                "name": self.name,
                "description": None,
                "superordinate": self.parent_id,}
        }
        return json.dumps(obj, sort_keys=True, indent=2)


class EntryModel(object):

    def __init__(self, entry, soundfiles):
        self.pk = int(entry.id)
        self.label = entry.lemma
        self.alphasort = entry.dictionary_sort
        self.topics = set()
        self.soundfile_uk = soundfiles["ode"]
        self.soundfile_us = soundfiles["noad"]

    def json(self):
        obj = {
            "pk": self.pk,
            "model": "gel2.entry",
            "fields": {
                "datestamp": isodate,
                "label": self.label[0:lemma_length],
                "alphasort": self.alphasort[0:lemma_length],
                "topics": list(self.topics),
                "soundfile_us": self.soundfile_us,
                "soundfile_uk": self.soundfile_uk,
                "custom": None,}
        }
        return json.dumps(obj, sort_keys=True, indent=2)


class WordclassModel(object):

    def __init__(self, wcset, entry_id):
        self.parent_id = int(entry_id)
        self.pk = int(wcset.id)
        self.definition = wcset.definition() or None
        if self.definition is not None:
            self.definition = self.definition[:def_length]
        self.penn = wcset.wordclass

        if wcset.date is not None and wcset.date.is_marked_obsolete():
            self.obs = True
        elif (wcset.date is not None and
              wcset.date.last_documented > 0 and
              wcset.date.last_documented < 1750):
            self.obs = True
        else:
            self.obs = False

    def json(self):
        obj = {
            "pk": self.pk,
            "model": "gel2.wordclass",
            "fields": {
                "entry": self.parent_id,
                "penn": self.penn,
                "definition": self.definition,
                "obsolete": self.obs,
                "custom": None,
                "datestamp": isodate,}
        }
        return json.dumps(obj, sort_keys=True, indent=2)


class TypeModel(object):

    def __init__(self, type, wcset_id):
        self.parent_id = int(wcset_id)
        self.pk = int(type.id)
        self.penn = type.wordclass
        self.form = type.form

    def json(self):
        obj = {
            "pk": self.pk,
            "model": "gel2.type",
            "fields": {
                "wordclass": self.parent_id,
                "form": self.form[0:lemma_length],
                "penn": self.penn,
                "variant": self.variant,
                "custom": None,
                "datestamp": isodate,}
        }
        return json.dumps(obj, sort_keys=True, indent=2)


class FreqTableModel(object):
    count = 0

    def __init__(self, table, type_id):
        FreqTableModel.count += 1
        self.pk = FreqTableModel.count
        self.parent_id = int(type_id)
        self.table = table

    def json(self):
        fields = {"type": self.parent_id, "datestamp": isodate,}
        for label, values in self.table.data().items():
            if label == "modern":
                pass
            else:
                col = "f" + label.split("-")[0]
                fields[col] = values["f"] or None
        obj = {
            "pk": self.pk,
            "model": "gel2.freqtable",
            "fields": fields,
        }
        return json.dumps(obj, sort_keys=True, indent=2)


class LinkModel(object):
    count = 0

    def __init__(self, link_raw):
        LinkModel.count += 1
        self.source_id = int(link_raw.gel_id)
        self.dict_label = link_raw.dict_label
        self.target_id = link_raw.target_entry
        self.target_node = link_raw.target_node or None
        self.pk = LinkModel.count

    def json(self):
        target_pk = 0
        for i, d in enumerate(dictionaries):
            if d == self.dict_label:
                target_pk = i + 1
        obj = {
            "pk": self.pk,
            "model": "gel2.link",
            "fields": {
                "entry": self.source_id,
                "target_resource": target_pk,
                "target_id": self.target_id,
                "target_node": self.target_node,}
        }
        return json.dumps(obj, sort_keys=True, indent=2)
