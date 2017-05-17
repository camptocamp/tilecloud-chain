# -*- coding: utf-8 -*-

import sys
import logging
from argparse import ArgumentParser

from tilecloud_chain import TileGeneration, DropEmpty, \
    HashDropper, Count, add_comon_options
from tilecloud_chain.format import size_format, duration_format

logger = logging.getLogger(__name__)


class Copy:
    count = None

    def copy(self, options, gene, layer, source, dest, task_name):
        if gene.layers[layer]['type'] == 'wms':
            all_dimensions = gene.get_all_dimensions(gene.layers[layer])

            for dimensions in all_dimensions:
                self._copy(options, gene, layer, source, dest, task_name, dimensions)
        else:  # pragma: no cover
            self._copy(options, gene, layer, source, dest, task_name)

    def _copy(self, options, gene, layer, source, dest, task_name, dimensions=None):
        # disable metatiles
        if dimensions is None:  # pragma: no cover
            dimensions = {}
        del gene.layers[layer]['meta']
        count_tiles_dropped = Count()

        gene.set_layer(layer, options)
        source_tilestore = gene.get_tilesstore(source, dimensions)
        dest_tilestore = gene.get_tilesstore(dest, dimensions)
        gene.init_tilecoords()
        gene.add_geom_filter()
        gene.add_logger()
        gene.get(source_tilestore, "Get the tiles")
        gene.ifilter(DropEmpty(gene))
        # Discard tiles with certain content
        if gene.layer and 'empty_tile_detection' in gene.layer:
            empty_tile = gene.layer['empty_tile_detection']

            gene.imap(HashDropper(
                empty_tile['size'], empty_tile['hash'], store=dest_tilestore, count=count_tiles_dropped))

        if options.process:
            gene.process(options.process)

        gene.ifilter(DropEmpty(gene))
        self.count = gene.counter(size=True)
        gene.put(dest_tilestore, "Store the tiles")
        gene.add_error_filters()
        gene.consume()
        if not options.quiet:
            print(
                """The tile {} of layer '{}' is finish
Nb {} tiles: {}
Nb errored tiles: {}
Nb dropped tiles: {}
Total time: {}
Total size: {}
Time per tile: {} ms
Size per tile: {} o
""".format(
                    task_name,
                    gene.layer['name'],
                    task_name,
                    self.count.nb,
                    count_tiles_dropped.nb,
                    gene.error,
                    duration_format(gene.duration),
                    size_format(self.count.size),
                    (gene.duration / self.count.nb * 1000).seconds if self.count.nb != 0 else 0,
                    self.count.size / self.count.nb if self.count.nb != 0 else -1
                )
            )


def main():
    parser = ArgumentParser(
        description='Used to copy the tiles from a cache to an other', prog=sys.argv[0]
    )
    add_comon_options(parser, near=False, time=False, dimensions=True, cache=False)
    parser.add_argument(
        '--process', dest='process', metavar="NAME",
        help='The process name to do'
    )
    parser.add_argument(
        'source',
        metavar="SOURCE",
        help='The source cache'
    )
    parser.add_argument(
        'dest',
        metavar="DEST",
        help='The destination cache'
    )

    options = parser.parse_args()

    gene = TileGeneration(options.config, options)

    if (options.layer):  # pragma: no cover
        copy = Copy()
        copy.copy(options, gene, options.layer, options.source, options.dest, 'copy')
    else:
        layers = gene.config['generation']['default_layers'] \
            if 'default_layers' in gene.config['generation'] \
            else gene.config['layers'].keys()
        for layer in layers:
            copy = Copy()
            copy.copy(options, gene, layer, options.source, options.dest, 'copy')


def process():
    parser = ArgumentParser(
        description='Used to copy the tiles from a cache to an other', prog=sys.argv[0]
    )
    add_comon_options(parser, near=False, time=False, dimensions=True)
    parser.add_argument(
        'process', metavar="PROCESS",
        help='The process name to do'
    )

    options = parser.parse_args()

    gene = TileGeneration(options.config, options)

    copy = Copy()
    if (options.layer):  # pragma: no cover
        copy.copy(options, gene, options.layer, options.cache, options.cache, 'process')
    else:
        layers_name = gene.config['generation']['default_layers'] \
            if 'default_layers' in gene.config.get('generation', {}) \
            else gene.layers.keys()
        for layer in layers_name:
            copy.copy(options, gene, layer, options.cache, options.cache, 'process')
