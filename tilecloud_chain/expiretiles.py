"""Import the osm2pgsql expire-tiles file to Postgres."""

import logging
import sys
from argparse import ArgumentParser
from pathlib import Path

import psycopg2.sql
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from tilecloud.grid.quad import QuadTileGrid

from tilecloud_chain import parse_tilecoord

logger = logging.getLogger(__name__)


def main() -> None:
    """Import the osm2pgsql expire-tiles file to Postgres."""
    try:
        parser = ArgumentParser(
            description="Used to import the osm2pgsql expire-tiles file to Postgres",
            prog=sys.argv[0],
        )
        parser.add_argument(
            "--buffer",
            type=float,
            default=0.0,
            help="Extent buffer to the tiles [m], default is 0",
        )
        parser.add_argument(
            "--simplify",
            type=float,
            default=0.0,
            help="Simplify the result geometry [m], default is 0",
        )
        parser.add_argument(
            "--create",
            default=False,
            action="store_true",
            help="create the table if not exists",
        )
        parser.add_argument(
            "--delete",
            default=False,
            action="store_true",
            help="empty the table",
        )
        parser.add_argument(
            "file",
            type=Path,
            metavar="FILE",
            help="The osm2pgsql expire-tiles file",
        )
        parser.add_argument(
            "connection",
            metavar="CONNECTION",
            help=(
                "The PostgreSQL connection string e.g. "
                '"user=www-data password=www-data dbname=sig host=localhost"'
            ),
        )
        parser.add_argument(
            "table",
            metavar="TABLE",
            help="The PostgreSQL table to fill",
        )
        parser.add_argument(
            "--schema",
            default="public",
            help="The PostgreSQL schema to use (should already exists), default is public",
        )
        parser.add_argument(
            "column",
            metavar="COLUMN",
            default="geom",
            nargs="?",
            help='The PostgreSQL column, default is "geom"',
        )
        parser.add_argument(
            "--srid",
            type=int,
            default=3857,
            nargs="?",
            help="The stored geometry SRID, no conversion by default (3857)",
        )
        options = parser.parse_args()

        connection = psycopg2.connect(options.connection)
        cursor = connection.cursor()

        if options.create:
            cursor.execute(
                "SELECT count(*) FROM pg_tables WHERE schemaname=%(schema)s AND tablename=%(table)s",
                {"schema": options.schema, "table": options.table},
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    psycopg2.sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} (id serial)").format(
                        psycopg2.sql.Identifier(options.schema),
                        psycopg2.sql.Identifier(options.table),
                    ),
                )
                cursor.execute(
                    "SELECT AddGeometryColumn(%(schema)s, %(table)s, %(column)s, %(srid)s, 'MULTIPOLYGON', 2)",
                    {
                        "schema": options.schema,
                        "table": options.table,
                        "column": options.column,
                        "srid": options.srid,
                    },
                )

        if options.delete:
            cursor.execute(psycopg2.sql.SQL("DELETE FROM {}").format(psycopg2.sql.Identifier(options.table)))

        geoms = []
        grid = QuadTileGrid(
            max_extent=(-20037508.34, -20037508.34, 20037508.34, 20037508.34),
        )
        with options.file.open(encoding="utf-8") as f:
            for coord in f:
                extent = grid.extent(parse_tilecoord(coord), options.buffer)
                geoms.append(
                    Polygon(
                        (
                            (extent[0], extent[1]),
                            (extent[0], extent[3]),
                            (extent[2], extent[3]),
                            (extent[2], extent[1]),
                        ),
                    ),
                )
        if len(geoms) == 0:
            print("No coords found")
            connection.commit()
            cursor.close()
            connection.close()
            sys.exit(0)
        geom = unary_union(geoms)
        if geom.geom_type == "Polygon":
            geom = MultiPolygon((geom,))

        if options.simplify > 0:
            geom.simplify(options.simplify)

        if options.srid <= 0:
            cursor.execute(
                psycopg2.sql.SQL("INSERT INTO {} ({}) VALUES (ST_GeomFromText(%(geom)s))").format(
                    psycopg2.sql.Identifier(options.table),
                    psycopg2.sql.Identifier(options.column),
                ),
                {
                    "geom": geom.wkt,
                },
            )

        elif options.srid != 3857:
            cursor.execute(
                psycopg2.sql.SQL(
                    "INSERT INTO {} ({}) VALUES (ST_Transform(ST_GeomFromText(%(geom)s, 3857), %(srid)s))",
                ).format(
                    psycopg2.sql.Identifier(options.table),
                    psycopg2.sql.Identifier(options.column),
                ),
                {
                    "geom": geom.wkt,
                    "srid": options.srid,
                },
            )
        else:
            cursor.execute(
                psycopg2.sql.SQL("INSERT INTO {} ({}) VALUES (ST_GeomFromText(%(geom)s, 3857))").format(
                    psycopg2.sql.Identifier(options.table),
                    psycopg2.sql.Identifier(options.column),
                ),
                {
                    "geom": geom.wkt,
                    "srid": options.srid,
                },
            )

        connection.commit()
        cursor.close()
        connection.close()
        print("Import successful")
    except SystemExit:
        raise
    except:  # pylint: disable=bare-except
        logger.exception("Exit with exception")
        sys.exit(1)
