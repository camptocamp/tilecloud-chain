# -*- coding: utf-8 -*-

import logging
from argparse import ArgumentParser

from tilecloud_chain import TileGeneration, DropEmpty, \
    HashDropper, Count, add_comon_options
from tilecloud_chain.format import size_format, duration_format

logger = logging.getLogger(__name__)


class Copy:
    count = None

    def copy(self, options, gene, layer, source, dest, task_name):
        # desable metatiles
        gene.layers[layer]['meta'] = False
        count_tiles_dropped = Count()

        gene.set_layer(layer, options)
        source_tilestore = gene.get_tilesstore(source)
        dest_tilestore = gene.get_tilesstore(dest)
        gene.init_tilecoords()
        gene.add_geom_filter()
        gene.add_logger()
        gene.get(source_tilestore, "Get the tiles")
        gene.ifilter(DropEmpty(gene))
        # Discard tiles with certain content
        if 'empty_tile_detection' in gene.layer:
            empty_tile = gene.layer['empty_tile_detection']

            gene.imap(HashDropper(
                empty_tile['size'], empty_tile['hash'], store=dest_tilestore,
                count=count_tiles_dropped,
            ))

        if options.process:
            gene.process(options.process)

        gene.ifilter(DropEmpty(gene))
        self.count = gene.counter(size=True)
        gene.put(dest_tilestore, "Store the tiles")
        gene.add_error_filters()
        gene.consume()
        if not options.quiet:
            print """The tile %s of layer '%s' is finish
Nb %s tiles: %i
Nb errored tiles: %i
Nb dropped tiles: %i
Total time: %s
Total size: %s
Time per tiles: %i ms
Size per tile: %i o
""" % \
                (
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


def main():
    parser = ArgumentParser(
        description='Used to copy the tiles from a cache to an other', prog='./buildout/bin/generate_copy'
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
        for layer in gene.config['generation']['default_layers']:
            copy = Copy()
            copy.copy(options, gene, layer, options.source, options.dest, 'copy')


def process():
    parser = ArgumentParser(
        description='Used to copy the tiles from a cache to an other', prog='./buildout/bin/generate_copy'
    )
    add_comon_options(parser, near=False, time=False, dimensions=True)
    parser.add_argument(
        'process', metavar="PROCESS",
        help='The process name to do'
    )

    options = parser.parse_args()

    gene = TileGeneration(options.config, options)

    if (options.layer):  # pragma: no cover
        copy = Copy()
        copy.copy(options, gene, options.layer, options.cache, options.cache, 'process')
    else:
        for layer in gene.config['generation']['default_layers']:
            copy = Copy()
            copy.copy(options, gene, layer, options.cache, options.cache, 'process')
