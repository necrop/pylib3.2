

import csv
import json
from collections import namedtuple

from lex.oed.thesaurus.taxonomymanager import TaxonomyManager


class Treemap(object):

    Coordinates = namedtuple('Coordinates', ['x', 'y', 'width', 'height'])
    output_columns = ('id', 'root', 'label', 'lev', 'size', 'x', 'y',
                      'w', 'h', 'sort')

    def __init__(self, **kwargs):
        self.args = {key: value for key, value in kwargs.items()}
        self.rectangles = []

    def write_to_csv(self, **kwargs):
        for key, value in kwargs.items():
            self.args[key] = value
        if not self.rectangles:
            self.compute_rectangles()
        self._set_rounder()
        with open(self.args['out_file'], 'w') as filehandle:
            writer = csv.writer(filehandle)
            writer.writerow(self.output_columns)
            for thesaurus_class in self.rectangles:
                writer.writerow(self._data_row(thesaurus_class))

    def write_to_json(self, **kwargs):
        for key, value in kwargs.items():
            self.args[key] = value
        if not self.rectangles:
            self.compute_rectangles()
        self._set_rounder()
        mode = self.args.get('mode', 'array')
        outputlist = []
        for thesaurus_class in self.rectangles:
            if mode in ('array', 'list', 'tuple'):
                datablob = self._data_row(thesaurus_class)
            elif mode in ('dict', 'dictionary', 'hash', 'object'):
                datablob = {key: value for key, value in
                            zip(self.output_columns,
                                self._data_row(thesaurus_class))}
            outputlist.append(datablob)
        with open(self.args['out_file'], 'w') as filehandle:
            json.dump(outputlist, filehandle)

    def _data_row(self, thesaurus_class):
        return (thesaurus_class.id(),
                thesaurus_class.root(),
                thesaurus_class.label(),
                thesaurus_class.level(),
                thesaurus_class.relative_size,
                self._rounder(thesaurus_class.rectangle.x),
                self._rounder(thesaurus_class.rectangle.y),
                self._rounder(thesaurus_class.rectangle.width),
                self._rounder(thesaurus_class.rectangle.height),
                thesaurus_class.count,)

    def compute_rectangles(self, **kwargs):
        for key, value in kwargs.items():
            self.args[key] = value
        self.taxonomy_manager = TaxonomyManager(dir=self.args['taxonomy_dir'],
                                                levels=self.args.get('depth', 4),
                                                verbosity=None,
                                                lazy=True,)
        root_classes = [c for c in self.taxonomy_manager.classes
                        if c.level() == 1]
        self.counter = 0
        self._iterate_tree(classes=root_classes,
                           orientation=self.args.get('orientation', 'horizontal'),
                           x=self.args.get('x', 0),
                           y=self.args.get('y', 0),
                           width=self.args.get('width', 1),
                           height=self.args.get('height', 1),)

    def _iterate_tree(self, **kwargs):
        classes = kwargs.get('classes')
        self._set_sizes(classes)
        orientation = kwargs.get('orientation')
        x_coord = kwargs.get('x')
        y_coord = kwargs.get('y')
        width = kwargs.get('width')
        height = kwargs.get('height')
        total_size = sum([thesaurus_class.relative_size for
                          thesaurus_class in classes])

        if total_size == 0:
            scale = 0
        elif orientation == 'horizontal':
            scale = width / total_size
        elif orientation == 'vertical':
            scale = height / total_size

        for thesaurus_class in classes:
            rect_size = thesaurus_class.relative_size * scale
            if orientation == 'horizontal':
                thesaurus_class.rectangle = self.Coordinates(x_coord, y_coord, rect_size, height)
                x_coord += rect_size
            else:
                thesaurus_class.rectangle = self.Coordinates(x_coord, y_coord, width, rect_size)
                y_coord += rect_size
            thesaurus_class.count = self.counter
            self.rectangles.append(thesaurus_class)
            self.counter += 1

            offspring = [child for child in
                         self.taxonomy_manager.children_of(thesaurus_class.id())
                         if child.wordclass() is None and
                         child.size(branch=True) > thesaurus_class.size(branch=True) * 0.01]
            if offspring:
                if orientation == 'horizontal':
                    new_orientation = 'vertical'
                else:
                    new_orientation = 'horizontal'
                self._iterate_tree(classes=offspring,
                                   orientation=new_orientation,
                                   x_coord=thesaurus_class.rectangle.x,
                                   y_coord=thesaurus_class.rectangle.y,
                                   width=thesaurus_class.rectangle.width,
                                   height=thesaurus_class.rectangle.height,)

    def _set_rounder(self):
        decimals = self.args.get('decimal_places', 4)
        self.rounder_formatter = '%.' + str(decimals) + 'f'

    def _rounder(self, value):
        return float(self.rounder_formatter % value)

    def _set_sizes(self, classes):
        try:
            self.args['class_sizes']
        except AttributeError:
            for thesaurus_class in classes:
                thesaurus_class.relative_size = thesaurus_class.size(branch=True)
        else:
            for thesaurus_class in classes:
                if thesaurus_class.id() in self.args['class_sizes']:
                    thesaurus_class.relative_size = self.args['class_sizes'][thesaurus_class.id()]
                else:
                    thesaurus_class.relative_size = thesaurus_class.size(branch=True)
