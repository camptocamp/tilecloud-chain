# -*- coding: utf-8 -*-

from argparse import ArgumentParser

import sys
import psycopg2
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import cascaded_union

from tilecloud.grid.quad import QuadTileGrid
from tilecloud_chain import parse_tilecoord


def main():
    parser = ArgumentParser(
        description='Used to import the osm2pgsql expire-tiles file to Postgres',
        prog=sys.argv[0]
    )
    parser.add_argument(
        '--buffer',
        type=float,
        default=0.0,
        help='Extent buffer to the tiles [m], default is 0',
    )
    parser.add_argument(
        '--simplify',
        type=float,
        default=0.0,
        help='Simplify the result geometry [m], default is 0',
    )
    parser.add_argument(
        '--create',
        default=False,
        action="store_true",
        help='create the table if not exists',
    )
    parser.add_argument(
        '--delete',
        default=False,
        action="store_true",
        help='empty the table',
    )
    parser.add_argument(
        'file',
        metavar='FILE',
        help='The osm2pgsql expire-tiles file',
    )
    parser.add_argument(
        'connection',
        metavar='CONNECTION',
        help='The PostgreSQL connection string e.g. "user=www-data password=www-data dbname=sig host=localhost"',
    )
    parser.add_argument(
        'table',
        metavar='TABLE',
        help='The PostgreSQL table to fill',
    )
    parser.add_argument(
        '--schema',
        default='public',
        help='The PostgreSQL schema to use (should already exists), default is public',
    )
    parser.add_argument(
        'column',
        metavar='COLUMN',
        default='geom',
        nargs='?',
        help='The PostgreSQL column, default is "geom"',
    )
    parser.add_argument(
        '--srid',
        type=int,
        default=3857,
        nargs='?',
        help='The stored geometry SRID, no conversion by default (3857)',
    )
    options = parser.parse_args()

    connection = psycopg2.connect(options.connection)
    cursor = connection.cursor()

    if options.create:
        cursor.execute(
            "SELECT count(*) FROM pg_tables WHERE schemaname='{}' AND tablename='{}'".format(
                options.schema, options.table
            )
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute('CREATE TABLE IF NOT EXISTS "{}"."{}" (id serial)'.format(
                options.schema, options.table
            ))
            cursor.execute("SELECT AddGeometryColumn('{}', '{}', '{}', {}, 'MULTIPOLYGON', 2)".format(
                options.schema, options.table, options.column, options.srid
            ))

    if options.delete:
        cursor.execute('DELETE FROM "{}"'.format((options.table)))

    geoms = []
    grid = QuadTileGrid(
        max_extent=(-20037508.34, -20037508.34, 20037508.34, 20037508.34),
    )
    with open(options.file, "r") as f:
        for coord in f:
            extent = grid.extent(parse_tilecoord(coord), options.buffer)
            geoms.append(Polygon((
                (extent[0], extent[1]),
                (extent[0], extent[3]),
                (extent[2], extent[3]),
                (extent[2], extent[1])
            )))
    if len(geoms) == 0:
        print("No coords found")
        connection.commit()
        cursor.close()
        connection.close()
        exit(0)
    geom = cascaded_union(geoms)
    if geom.geom_type == 'Polygon':
        geom = MultiPolygon((geom,))

    if options.simplify > 0:
        geom.simplify(options.simplify)

    sql_geom = "ST_GeomFromText('{}', 3857)".format(geom.wkt)
    if options.srid <= 0:
        sql_geom = "ST_GeomFromText('{}')".format(geom.wkt)  # pragma: no cover
    elif options.srid != 3857:
        sql_geom = 'ST_Transform({}, {})'.format(sql_geom, options.srid)

    cursor.execute('INSERT INTO "{}" ("{}") VALUES ({})'.format(
        options.table, options.column, sql_geom
    ))
    connection.commit()
    cursor.close()
    connection.close()
    print('Import successful')
