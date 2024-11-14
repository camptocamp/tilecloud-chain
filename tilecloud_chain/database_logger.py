"""Log the generated tiles in a database."""

import logging
import sys
import time

import psycopg2.sql
from prometheus_client import Summary
from tilecloud import Tile

import tilecloud_chain.configuration

_LOGGER = logging.getLogger(__name__)

_INSERT_SUMMARY = Summary("tilecloud_chain_database_logger", "Number of database inserts", ["layer"])


class DatabaseLoggerCommon:
    """Log the generated tiles in a database."""

    def __init__(self, config: tilecloud_chain.configuration.Logging, daemon: bool):
        db_params = config["database"]
        while True:
            try:
                self.connection = psycopg2.connect(
                    dbname=db_params["dbname"],
                    host=db_params.get("host"),
                    port=db_params.get("port"),
                    user=db_params.get("user"),
                    password=db_params.get("password"),
                )
                break
            except psycopg2.OperationalError:
                _LOGGER.warning("Failed connecting to the database. Will try again in 1s", exc_info=True)
                if daemon:
                    time.sleep(1)
                else:
                    sys.exit(2)
        if "." in db_params["table"]:
            schema, table = db_params["table"].split(".")
        else:
            schema = "public"
            table = db_params["table"]

        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname=%s AND tablename=%s)", (schema, table)
            )
            schema = psycopg2.extensions.quote_ident(schema, self.connection)
            table = psycopg2.extensions.quote_ident(table, self.connection)

            if not cursor.fetchone()[0]:
                try:
                    cursor.execute(
                        psycopg2.sql.SQL(
                            "CREATE TABLE {}.{} ("
                            "  id BIGSERIAL PRIMARY KEY,"
                            "  layer CHARACTER VARYING(80) NOT NULL,"
                            "  run INTEGER NOT NULL,"
                            "  action CHARACTER VARYING(7) NOT NULL,"
                            "  tile TEXT NOT NULL,"
                            "  UNIQUE (layer, run, tile))"
                        ).format(psycopg2.sql.Identifier(schema), psycopg2.sql.Identifier(table))
                    )
                    self.connection.commit()
                except psycopg2.DatabaseError:
                    logging.exception("Unable to create table %s.%s", schema, table)
                    sys.exit(1)
            else:
                try:
                    cursor.execute(
                        psycopg2.sql.SQL(
                            "INSERT INTO {}.{}(layer, run, action, tile) VALUES (%s, %s, %s, %s)"
                        ).format(psycopg2.sql.Identifier(schema), psycopg2.sql.Identifier(table)),
                        ("test_layer", -1, "test", "-1x-1"),
                    )
                except psycopg2.DatabaseError:
                    logging.exception("Unable to insert logging data into %s.%s", schema, table)
                    sys.exit(1)
                finally:
                    self.connection.rollback()

        self.schema = schema
        self.table = table


class DatabaseLoggerInit(DatabaseLoggerCommon):
    """Log the generated tiles in a database."""

    def __init__(self, config: tilecloud_chain.configuration.Logging, daemon: bool) -> None:
        super().__init__(config, daemon)

        with self.connection.cursor() as cursor:
            cursor.execute(
                psycopg2.sql.SQL("SELECT COALESCE(MAX(run), 0) + 1 FROM {}.{}").format(
                    psycopg2.sql.Identifier(self.schema), psycopg2.sql.Identifier(self.table)
                )
            )
            (self.run,) = cursor.fetchone()

    def __call__(self, tile: Tile) -> Tile:
        """Log the generated tiles in a database."""
        tile.metadata["run"] = self.run
        return tile


class DatabaseLogger(DatabaseLoggerCommon):
    """Log the generated tiles in a database."""

    def __call__(self, tile: Tile) -> Tile:
        """Log the generated tiles in a database."""
        if tile is None:
            _LOGGER.warning("The tile is None")
            return None

        if tile.error:
            action = "error"
        elif tile.data:
            action = "create"
        else:
            action = "delete"

        layer = tile.metadata.get("layer", "- No layer -")
        run = tile.metadata.get("run", -1)

        with _INSERT_SUMMARY.labels(layer).time(), self.connection.cursor() as cursor:
            try:
                cursor.execute(
                    psycopg2.sql.SQL(
                        "INSERT INTO {} (layer, run, action, tile) "
                        "VALUES (%(layer)s, %(run)s, %(action)s::varchar(7), %(tile)s)"
                    ).format(psycopg2.sql.Identifier(self.schema), psycopg2.sql.Identifier(self.table)),
                    {"layer": layer, "action": action, "tile": str(tile.tilecoord), "run": run},
                )
            except psycopg2.IntegrityError:
                self.connection.rollback()
                cursor.execute(
                    psycopg2.sql.SQL(
                        "UPDATE {} SET action = %(action)s "
                        "WHERE layer = %(layer)s AND run = %(run)s AND tile = %(tile)s"
                    ).format(psycopg2.sql.Identifier(self.schema), psycopg2.sql.Identifier(self.table)),
                    {"layer": layer, "action": action, "tile": str(tile.tilecoord), "run": run},
                )

            self.connection.commit()

        return tile
