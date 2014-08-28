

import csv
import json
from collections import namedtuple, defaultdict

from lex.oed.thesaurus.taxonomymanager import TaxonomyManager

Coordinates = namedtuple('Coordinates', ['x', 'y', 'width', 'height'])
OUTPUT_COLUMNS = ('id', 'root', 'level', 'size', 'ratio', 'x', 'y',
                  'w', 'h', 'sort', 'label', 'breadcrumb')


class Treemap(object):

    """
    Build data used for displaying the Historical Thesaurus as a treemap.

    Optional named arguments to init are:
     - taxonomy_dir: path to the HTOED taxonomy directory
     - depth: number of levels to go down (defaults to 4)
     - orientation: 'horizontal' (default) or 'vertical'
     - width: defaults to 1
     - height: defaults to 1
    """

    def __init__(self, **kwargs):
        self.args = {key: value for key, value in kwargs.items()}
        self.rectangles = []
        self.total_size = None

    def write_to_csv(self, **kwargs):
        """
        Write the treemap data to a CSV file.

        Named argument:
         - out_file: path to the output CSV file
        """
        for key, value in kwargs.items():
            self.args[key] = value

        columns = OUTPUT_COLUMNS[:]
        omit_breadcrumb = self.args.get('omit_breadcrumb', False)
        omit_label = self.args.get('omit_label', True)
        if omit_breadcrumb:
            columns = [c for c in columns if c != 'breadcrumb']
        if omit_label:
            columns = [c for c in columns if c != 'label']

        if not self.rectangles:
            self.compute_rectangles()
        self._set_rounder()
        with open(self.args['out_file'], 'w') as filehandle:
            writer = csv.writer(filehandle)
            writer.writerow(columns)
            for thesaurus_class in self.rectangles:
                writer.writerow(self._data_row(thesaurus_class))

    def _convert_to_json(self, **kwargs):
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
                            zip(OUTPUT_COLUMNS,
                                self._data_row(thesaurus_class))}
            outputlist.append(datablob)
        return outputlist

    def return_json(self, **kwargs):
        outputlist = self._convert_to_json(**kwargs)
        return json.dumps(outputlist)

    def write_to_json(self, **kwargs):
        """
        Write the treemap data to a JSON file.

        Named arguments:
         - out_file: path to the output JSON file
         - mode: 'array' (default) or 'dict', which changes how the
            data for each element is stored; 'dict' is more verbose
            and explicit.
        """
        for key, value in kwargs.items():
            self.args[key] = value
        outputlist = self._convert_to_json(**kwargs)
        with open(self.args.get('out_file'), 'w') as filehandle:
            json.dump(outputlist, filehandle)

    def _data_row(self, thesaurus_class):
        omit_breadcrumb = self.args.get('omit_breadcrumb', False)
        omit_label = self.args.get('omit_label', True)
        ratio = thesaurus_class.branch_size / self.total_size
        ratio = float('%.3g' % ratio)
        row = [
            thesaurus_class.id(),
            thesaurus_class.root(),
            thesaurus_class.level(),
            thesaurus_class.branch_size,
            ratio,
            self._rounder(thesaurus_class.rectangle.x),
            self._rounder(thesaurus_class.rectangle.y),
            self._rounder(thesaurus_class.rectangle.width),
            self._rounder(thesaurus_class.rectangle.height),
            thesaurus_class.sort,
        ]
        if not omit_label:
            row.append(thesaurus_class.label())
        if not omit_breadcrumb:
            row.append(thesaurus_class.breadcrumb())
        return row

    def compute_rectangles(self, **kwargs):
        for key, value in kwargs.items():
            self.args[key] = value
        in_dir = self.args.get('taxonomy_dir', None)
        self.taxonomy_manager = TaxonomyManager(dir=in_dir,
                                                levels=self.args.get('depth', 4),
                                                verbosity=None,
                                                lazy=True,)

        self._set_sizes(self.taxonomy_manager.classes)
        root_classes = [c for c in self.taxonomy_manager.classes
                        if c.level() == 1]
        self.total_size = sum([c.branch_size for c in root_classes])

        self.sort_order = 0
        self._iterate_tree(classes=root_classes,
                           orientation=self.args.get('orientation', 'horizontal'),
                           x=self.args.get('x', 0),
                           y=self.args.get('y', 0),
                           width=self.args.get('width', 1),
                           height=self.args.get('height', 1),)

    def _iterate_tree(self, **kwargs):
        classes = kwargs.get('classes')
        orientation = kwargs.get('orientation')
        x_coord = kwargs.get('x')
        y_coord = kwargs.get('y')
        width = kwargs.get('width')
        height = kwargs.get('height')
        total_size = sum([thesaurus_class.branch_size for
                          thesaurus_class in classes])

        if total_size == 0:
            scale = 0
        elif orientation == 'horizontal':
            scale = width / total_size
        elif orientation == 'vertical':
            scale = height / total_size

        for thesaurus_class in classes:
            rect_size = thesaurus_class.branch_size * scale
            if orientation == 'horizontal':
                thesaurus_class.rectangle = Coordinates(x_coord, y_coord, rect_size, height)
                x_coord += rect_size
            else:
                thesaurus_class.rectangle = Coordinates(x_coord, y_coord, width, rect_size)
                y_coord += rect_size
            thesaurus_class.sort = self.sort_order
            self.rectangles.append(thesaurus_class)
            self.sort_order += 1

            minimum_size = thesaurus_class.size(branch=True) * 0.01
            offspring = [child for child in
                         self.taxonomy_manager.children_of(thesaurus_class.id())
                         if child.wordclass() is None and
                         child.size(branch=True) > minimum_size]
            if offspring:
                if orientation == 'horizontal':
                    new_orientation = 'vertical'
                else:
                    new_orientation = 'horizontal'
                self._iterate_tree(classes=offspring,
                                   orientation=new_orientation,
                                   x=thesaurus_class.rectangle.x,
                                   y=thesaurus_class.rectangle.y,
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
        except KeyError:
            for thesaurus_class in classes:
                thesaurus_class.branch_size = thesaurus_class.size(branch=True)
        else:
            for thesaurus_class in classes:
                if thesaurus_class.id() in self.args['class_sizes']:
                    thesaurus_class.branch_size = self.args['class_sizes'][thesaurus_class.id()]
                else:
                    thesaurus_class.branch_size = thesaurus_class.size(branch=True)


def load_csv_treemap(csvfile):
    """
    Load a treemap CSV file created by the above process back into memory,
    using the column headers as attribute names for each object
    """
    nodes = []
    with open(csvfile) as filehandle:
        csvreader = csv.reader(filehandle)
        for row in csvreader:
            if row[0] == 'id':
                Classdata = namedtuple('Classdata', row)
            else:
                for i in (0, 1, 2, 3, 9):
                    row[i] = int(row[i])
                for i in (4, 5, 6, 7, 8):
                    row[i] = float(row[i])
                nodes.append(Classdata(*row))
    return nodes
