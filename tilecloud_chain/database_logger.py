"""Log the generated tiles in a database."""

import asyncio
import logging
import sys

import psycopg.sql
from prometheus_client import Summary
from tilecloud import Tile

import tilecloud_chain.configuration

_LOGGER = logging.getLogger(__name__)

_INSERT_SUMMARY = Summary("tilecloud_chain_database_logger", "Number of database inserts", ["layer"])


class DatabaseLoggerCommon:
    """Log the generated tiles in a database."""

    def __init__(self, config: tilecloud_chain.configuration.Logging, daemon: bool) -> None:
        self._db_params = config["database"]
        self._daemon = daemon
        self.connection: psycopg.AsyncConnection | None = None
        self.schema: str | None = None
        self.table: str | None = None

    async def _init(self) -> None:
        while True:
            try:
                self.connection = await psycopg.AsyncConnection.connect(
                    dbname=self._db_params["dbname"],
                    host=self._db_params.get("host"),
                    port=self._db_params.get("port"),
                    user=self._db_params.get("user"),
                    password=self._db_params.get("password"),
                )
                break
            except psycopg.OperationalError:
                _LOGGER.warning("Failed connecting to the database. Will try again in 1s", exc_info=True)
                if self._daemon:
                    await asyncio.sleep(1)
                else:
                    sys.exit(2)
        assert self.connection is not None

        if "." in self._db_params["table"]:
            schema, table = self._db_params["table"].split(".")
        else:
            schema = "public"
            table = self._db_params["table"]

        async with self.connection.cursor() as cursor:
            await cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname=%s AND tablename=%s)",
                (schema, table),
            )
            schema = psycopg.sql.quote(schema, self.connection)
            table = psycopg.sql.quote(table, self.connection)

            elem = await cursor.fetchone()
            assert elem is not None
            if not elem[0]:
                try:
                    await cursor.execute(
                        psycopg.sql.SQL(
                            "CREATE TABLE {}.{} ("
                            "  id BIGSERIAL PRIMARY KEY,"
                            "  layer CHARACTER VARYING(80) NOT NULL,"
                            "  run INTEGER NOT NULL,"
                            "  action CHARACTER VARYING(7) NOT NULL,"
                            "  tile TEXT NOT NULL,"
                            "  UNIQUE (layer, run, tile))",
                        ).format(psycopg.sql.Identifier(schema), psycopg.sql.Identifier(table)),
                    )
                    await self.connection.commit()
                except psycopg.DatabaseError:
                    _LOGGER.exception("Unable to create table %s.%s", schema, table)
                    sys.exit(1)
            else:
                try:
                    await cursor.execute(
                        psycopg.sql.SQL(
                            "INSERT INTO {}.{}(layer, run, action, tile) VALUES (%s, %s, %s, %s)",
                        ).format(psycopg.sql.Identifier(schema), psycopg.sql.Identifier(table)),
                        ("test_layer", -1, "test", "-1x-1"),
                    )
                except psycopg.DatabaseError:
                    _LOGGER.exception("Unable to insert logging data into %s.%s", schema, table)
                    sys.exit(1)
                finally:
                    await self.connection.rollback()

        self.schema = schema
        self.table = table


class DatabaseLoggerInit(DatabaseLoggerCommon):
    """Log the generated tiles in a database."""

    def __init__(self, config: tilecloud_chain.configuration.Logging, daemon: bool) -> None:
        super().__init__(config, daemon)

        self.init = False
        self.run = -1

    async def _init(self) -> None:
        assert self.connection is not None
        assert self.schema is not None
        assert self.table is not None

        async with self.connection.cursor() as cursor:
            await cursor.execute(
                psycopg.sql.SQL("SELECT COALESCE(MAX(run), 0) + 1 FROM {}.{}").format(
                    psycopg.sql.Identifier(self.schema),
                    psycopg.sql.Identifier(self.table),
                ),
            )
            elem = await cursor.fetchone()
            assert elem is not None
            (self.run,) = elem
        self.init = True

    async def __call__(self, tile: Tile) -> Tile:
        """Log the generated tiles in a database."""
        if not self.init:
            await self._init()
        tile.metadata["run"] = self.run  # type: ignore[assignment]
        return tile


class DatabaseLogger(DatabaseLoggerCommon):
    """Log the generated tiles in a database."""

    async def __call__(self, tile: Tile) -> Tile:
        """Log the generated tiles in a database."""
        if self.connection is None:
            await self._init()
        assert self.connection is not None
        assert self.schema is not None
        assert self.table is not None

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

        with _INSERT_SUMMARY.labels(layer).time():
            async with self.connection.cursor() as cursor:
                try:
                    await cursor.execute(
                        psycopg.sql.SQL(
                            "INSERT INTO {} (layer, run, action, tile) "
                            "VALUES (%(layer)s, %(run)s, %(action)s::varchar(7), %(tile)s)",
                        ).format(psycopg.sql.Identifier(self.schema), psycopg.sql.Identifier(self.table)),
                        {"layer": layer, "action": action, "tile": str(tile.tilecoord), "run": run},
                    )
                except psycopg.IntegrityError:
                    await self.connection.rollback()
                    await cursor.execute(
                        psycopg.sql.SQL(
                            "UPDATE {} SET action = %(action)s "
                            "WHERE layer = %(layer)s AND run = %(run)s AND tile = %(tile)s",
                        ).format(psycopg.sql.Identifier(self.schema), psycopg.sql.Identifier(self.table)),
                        {"layer": layer, "action": action, "tile": str(tile.tilecoord), "run": run},
                    )

                await self.connection.commit()

        return tile
