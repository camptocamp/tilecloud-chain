# -*- coding: utf-8 -*-

import logging
from argparse import ArgumentParser

from tilecloud_chain import TileGeneration, DropEmpty, add_comon_options
from tilecloud_chain.format import size_format, duration_format

logger = logging.getLogger(__name__)


class Copy:
    count = None

    def copy(self, options, gene, layer):
        # desable metatiles
        gene.layers[layer]['meta'] = False

        gene.set_layer(layer, options)
        source_tilestore = gene.get_tilesstore(options.source)
        dest_tilestore = gene.get_tilesstore(options.dest)
        gene.init_tilecoords()
        gene.add_geom_filter()
        gene.add_logger()
        gene.get(source_tilestore, "Get the tiles")
        gene.ifilter(DropEmpty(gene))
        self.count = gene.counter(size=True)
        gene.put(dest_tilestore, "Store the tiles")
        gene.add_error_filters()
        gene.consume()
        if not options.quiet:
            print """The tile copy of layer '%s' is finish
Nb copyed tiles: %i
Total time: %s
Total size: %s
Time per tiles: %i ms
Size per tile: %i o
""" % \
                (
                    gene.layer['name'],
                    self.count.nb,
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
        copy.copy(options, gene, options.layer)
    else:
        for layer in gene.config['generation']['default_layers']:
            copy = Copy()
            copy.copy(options, gene, layer)
