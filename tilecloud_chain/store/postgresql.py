"""PostgreSQL queue."""

# Copyright (c) 2023-2025 by Camptocamp
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 3. Neither the name of Camptocamp nor the names of its contributors may
# be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import asyncio
import datetime
import gc
import io
import logging
import os
import shlex
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import objgraph
import sqlalchemy
import sqlalchemy.schema
import sqlalchemy.sql.functions
from prometheus_client import Counter, Gauge, Summary
from sqlalchemy import JSON, Column, DateTime, Integer, Unicode, and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from tilecloud import Tile, TileCoord

from tilecloud_chain import DatedConfig, configuration, controller, generate
from tilecloud_chain.store import AsyncTileStore

_LOGGER = logging.getLogger(__name__)

_NB_MESSAGE_COUNTER = Gauge(
    "tilecloud_postgresql_nb_messages",
    "Number of messages in PostgreSQL",
    ["job_id", "config_filename"],
)
_PENDING_COUNTER = Gauge(
    "tilecloud_postgresql_pending",
    "Number of pending messages in PostgreSQL",
    ["job_id", "config_filename"],
)
_READ_ERROR_COUNTER = Counter(
    "tilecloud_postgresql_read_error",
    "Number of read errors on PostgreSQL",
    ["job_id", "config_filename"],
)
_MAINTENANCE_SUMMARY = Summary("tilecloud_postgresql_maintenance", "Time spent in PostgreSQL maintenance")

# Job status:
# - created: the job has been created
# - pending: during the queue creation
# - started: the job queue is created
# - error: the job finish with an error
# - done: the job is done
# - cancelled: the job is cancelled
# Queue status:
# - created: the meta tile job is created
# - pending: the meta tile is processing
# - error: the meta tile is in error
_STATUS_CREATED = "created"
_STATUS_STARTED = "started"
_STATUS_ERROR = "error"
_STATUS_DONE = "done"
_STATUS_CANCELLED = "cancelled"
_STATUS_PENDING = "pending"

_schema = os.environ.get("TILECLOUD_CHAIN_POSTGRESQL_SCHEMA", "tilecloud_chain")


def _encode_message(metatile: Tile) -> dict[str, Any]:
    metadata = dict(metatile.metadata)
    metadata.pop("postgresql_id", None)
    return {
        "z": metatile.tilecoord.z,
        "x": metatile.tilecoord.x,
        "y": metatile.tilecoord.y,
        "n": metatile.tilecoord.n,
        "metadata": metadata,
    }


def _decode_tilecoord(body: dict[str, Any]) -> TileCoord:
    z = cast("int", body.get("z"))
    x = cast("int", body.get("x"))
    y = cast("int", body.get("y"))
    n = cast("int", body.get("n"))
    return TileCoord(z, x, y, n)


def _decode_message(body: dict[str, Any], **kwargs: Any) -> Tile:
    tilecoord = _decode_tilecoord(body)
    metadata = body.get("metadata", {})
    return Tile(tilecoord, metadata=metadata, **kwargs)


class PostgresqlTileStoreError(Exception):
    """PostgreSQL TileStore Exception."""


class Base(DeclarativeBase):
    """Base class for the SQLAlchemy models."""


class Job(Base):
    """SQLAlchemy model for the jobs."""

    __tablename__ = "job"
    __table_args__ = {"schema": _schema}  # noqa: RUF012

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(Unicode, nullable=False)
    command = Column(Unicode, nullable=False)
    config_filename = Column(Unicode, nullable=False)
    status = Column(Unicode, nullable=False, default=_STATUS_CREATED, index=True)
    message = Column(Unicode)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sqlalchemy.sql.functions.now(),
        index=True,
    )
    started_at = Column(DateTime(timezone=True), index=True)

    def __repr__(self) -> str:
        """Return the representation of the job."""
        return f"Job {self.id} {self.name} [{self.status}]"


class Queue(Base):
    """SQLAlchemy model for the queue entries."""

    __tablename__ = "queue"
    __table_args__ = {"schema": _schema}  # noqa: RUF012

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    job_id = Column(Integer, nullable=False, index=True)
    zoom = Column(Integer, nullable=False, index=True)
    status = Column(Unicode, nullable=False, default=_STATUS_CREATED, index=True)
    error = Column(Unicode)
    started_at = Column(DateTime, index=True)
    # Like this:
    # {
    #     "x": 0,
    #     "y": 0,
    #     "z": 0,
    #     "n": 5,
    #     "metadata": {},
    # }
    meta_tile = Column(JSON, nullable=False)

    def __repr__(self) -> str:
        """Return the representation of the queue entry."""
        return f"Queue {self.job_id}.{self.id} zoom={self.zoom} [{self.status}]"


async def _start_job(
    job_id: int,
    sqlalchemy_url: str,
    allowed_commands: list[str],
    allowed_arguments: list[str],
) -> None:
    engine = create_async_engine(sqlalchemy_url)
    SessionMaker = async_sessionmaker(engine)  # noqa

    async with SessionMaker() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar()
    assert job is not None

    command = shlex.split(job.command)
    command0 = command[0].replace("_", "-")

    if command0 not in allowed_commands:
        job.status = _STATUS_ERROR  # type: ignore[assignment]
        job.error = (  # type: ignore[attr-defined]
            f"The given command '{command0}' is not allowed, allowed command are: "
            f"{', '.join(allowed_commands)}"
        )
        return

    add_role = False
    arguments = {c.split("=")[0]: c.split("=")[1:] for c in command[1:]}
    if command0 == "generate-tiles":
        add_role = "--get-hash" not in arguments and "--get-bbox" not in arguments

    for arg in arguments:
        if arg.startswith("-") and arg not in allowed_arguments:
            async with SessionMaker() as session:
                result = await session.execute(select(Job).where(Job.id == job_id))
                job = result.scalar()
                assert job is not None
                job.status = _STATUS_ERROR  # type: ignore[assignment]
                job.error = (  # type: ignore[attr-defined]
                    f"The argument {arg} is not allowed, allowed arguments are: {', '.join(allowed_arguments)}"
                )
            return

    final_command = [
        command0,
        f"--config={job.config_filename}",
    ]
    if add_role:
        final_command += ["--role=master", "--quiet", f"--job-id={job.id}"]
    final_command += command[1:]

    display_command = shlex.join(final_command)
    env: dict[str, str] = {**os.environ, "FRONTEND": "noninteractive"}

    main = None
    if final_command[0] in ["generate-tiles", "generate_tiles"]:
        main = generate.async_main
    elif final_command[0] in ["generate-controller", "generate_controller"]:
        main = controller.async_main
    if main is not None:
        # Delete potentially already existing queue entries
        async with SessionMaker() as session:
            await session.execute(delete(Queue).where(Queue.job_id == job_id))
            await session.commit()

        display_command = shlex.join(final_command)
        error = False
        out = io.StringIO()
        try:
            for key, value in env.items():
                os.environ[key] = value
            _LOGGER.info("Running the command `%s` using the function directly", display_command)
            await main(final_command, out)
            _LOGGER.info("Successfully ran the command `%s` using the function directly", display_command)
        except SystemExit as exception:
            if exception.code is not None and exception.code != 0:
                _LOGGER.exception("Error while running the command `%s`", display_command)
                error = True
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.exception("Error while running the command `%s`", display_command)
            error = True

        async with SessionMaker() as session:
            result = await session.execute(select(Job).where(Job.id == job_id).with_for_update(of=Job))
            job = result.scalar()
            job.status = _STATUS_ERROR if error else _STATUS_STARTED  # type: ignore[union-attr]
            job.message = out.getvalue()[: int(os.environ.get("TILECLOUD_CHAIN_MAX_OUTPUT_LENGTH", "1000"))]  # type: ignore[union-attr]
            await session.commit()
        return

    _LOGGER.info("Run the command `%s`", display_command)

    completed_process = await asyncio.create_subprocess_exec(
        *final_command,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await completed_process.communicate()

    async with SessionMaker() as session:
        result = await session.execute(select(Job).where(Job.id == job_id).with_for_update(of=Job))
        job = result.scalar()
        assert job is not None
        job.status = _STATUS_DONE if completed_process.returncode == 0 else _STATUS_ERROR  # type: ignore[assignment]
        job.message = stdout.decode()  # type: ignore[assignment]
        if stderr:
            job.message += "\nError:\n" + stderr.decode()  # type: ignore[assignment]

    if completed_process.returncode != 0:
        _LOGGER.warning(
            "The command `%s` exited with an error code: %s\nstdout:\n%s\nstderr:\n%s",
            display_command,
            completed_process.returncode,
            stdout.decode(),
            stderr.decode(),
        )


class PostgresqlTileStore(AsyncTileStore):
    """PostgreSQL queue."""

    def __init__(
        self,
        allowed_commands: list[str],
        allowed_arguments: list[str],
        max_pending_minutes: int,
        sqlalchemy_url: str,
    ) -> None:
        self.sqlalchemy_url = sqlalchemy_url

        # Used to mix the generation for each the projects
        self.jobs: dict[str, int] = {}

        self.allowed_commands = allowed_commands
        self.allowed_arguments = allowed_arguments
        self.max_pending_minutes = max_pending_minutes
        self.SessionMaker: async_sessionmaker[AsyncSession] | None = None  # pylint: disable=invalid-name

    async def init(self) -> None:
        """Initialize the store."""
        engine = create_async_engine(self.sqlalchemy_url)

        async with engine.connect() as connection:
            await connection.execute(sqlalchemy.schema.CreateSchema(_schema, if_not_exists=True))
            await connection.run_sync(Base.metadata.create_all)
            await connection.commit()

        self.SessionMaker = async_sessionmaker(engine)  # pylint: disable=invalid-name

    async def create_job(self, name: str, command: str, config_filename: Path) -> None:
        """Create a job."""
        assert self.SessionMaker is not None
        async with self.SessionMaker() as session:
            job = Job(name=name, command=command, config_filename=config_filename.as_posix())
            session.add(job)
            await session.commit()

    async def retry(self, job_id: int, config_filename: Path) -> None:
        """Retry a job."""
        assert self.SessionMaker is not None
        async with self.SessionMaker() as session:
            nb_job = await session.scalar(
                select(sqlalchemy.sql.functions.count(Job.id)).where(
                    and_(
                        Job.id == job_id,
                        Job.status == _STATUS_ERROR,
                        Job.config_filename == config_filename.as_posix(),
                    ),
                ),
            )
            if nb_job == 0:
                message = f"Job {job_id} not found with the correct status, for the host"
                raise PostgresqlTileStoreError(message)
            await session.execute(
                update(Queue)
                .where(and_(Queue.job_id == job_id, Queue.status == _STATUS_ERROR))
                .values(status=_STATUS_CREATED, error=""),
            )
            await session.execute(update(Job).where(Job.id == job_id).values(status=_STATUS_CREATED))
            await session.commit()

    async def cancel(self, job_id: int, config_filename: Path) -> None:
        """Cancel a job."""
        assert self.SessionMaker is not None
        async with self.SessionMaker() as session:
            result = await session.execute(
                select(Job).where(
                    and_(
                        Job.id == job_id,
                        Job.status == _STATUS_STARTED,
                        Job.config_filename == config_filename.as_posix(),
                    ),
                ),
            )
            job = result.scalar()
            if job is None:
                message = f"Job {job_id} not found, with the correct status, for the host"
                raise PostgresqlTileStoreError(message)
            await session.execute(
                delete(Queue).where(and_(Queue.job_id == job_id, Queue.status == _STATUS_CREATED)),
            )
            await session.execute(update(Job).where(Job.id == job_id).values(status=_STATUS_CANCELLED))
            await session.commit()

    async def get_status(self, config_filename: Path) -> list[tuple[Job, list[dict[str, int]], list[str]]]:
        """
        Get the jobs.

        Return a list of tuple with:
        - the job
        - the status of the job
        - the last 5 meta tiles errors
        """
        assert self.SessionMaker is not None
        result = []
        async with self.SessionMaker() as session:
            jobs_result = await session.execute(
                select(Job)
                .where(Job.config_filename == config_filename.as_posix())
                .order_by(Job.created_at.desc()),
            )
            for job in jobs_result.scalars():
                result_by_zoom_level: dict[int, dict[str, int]] = {}

                nb_tiles_zoom_results = await session.scalar(
                    select(sqlalchemy.sql.functions.count(Queue.id), Queue.zoom)
                    .where(and_(Queue.status == _STATUS_CREATED, Queue.job_id == job.id))
                    .group_by(Queue.zoom),
                )
                for nb_tiles, zoom in nb_tiles_zoom_results or []:
                    result_by_zoom_level.setdefault(zoom, {})["generate"] = nb_tiles

                nb_tiles_zoom_results = await session.scalar(
                    select(sqlalchemy.sql.functions.count(Queue.id), Queue.zoom)
                    .where(and_(Queue.status == _STATUS_PENDING, Queue.job_id == job.id))
                    .group_by(Queue.zoom),
                )
                for nb_tiles, zoom in nb_tiles_zoom_results or []:
                    result_by_zoom_level.setdefault(zoom, {})["pending"] = nb_tiles

                nb_tiles_zoom_results = await session.scalar(
                    select(sqlalchemy.sql.functions.count(Queue.id), Queue.zoom)
                    .where(and_(Queue.status == _STATUS_ERROR, Queue.job_id == job.id))
                    .group_by(Queue.zoom),
                )
                for nb_tiles, zoom in nb_tiles_zoom_results or []:
                    result_by_zoom_level.setdefault(zoom, {})["error"] = nb_tiles

                status = [{"zoom": zoom, **data} for zoom, data in result_by_zoom_level.items()]
                status = sorted(status, key=lambda x: x["zoom"])

                queue_results = await session.execute(
                    select(Queue)
                    .where(and_(Queue.job_id == job.id, Queue.status == _STATUS_ERROR))
                    .order_by(Queue.started_at.desc())
                    .limit(5),
                )
                result.append(
                    (
                        job,
                        status,
                        [
                            f"{_decode_tilecoord(sqlalchemy_tile.meta_tile)}: {sqlalchemy_tile.error}"  # type: ignore[arg-type]
                            for sqlalchemy_tile in queue_results.scalars()
                        ],
                    ),
                )
        return result

    async def _maintenance(self) -> None:
        """
        Manage the queue.

        - Create the job queue
        - Update the job status (error or done) on finish
        - manage the too long pending tile generation
        - Create the job list to be process
        """
        assert self.SessionMaker is not None
        with _MAINTENANCE_SUMMARY.time():
            # Restart the too long pending jobs (queue generation)
            async with self.SessionMaker() as session:
                await session.execute(
                    update(Job)
                    .where(
                        and_(
                            Job.status == _STATUS_PENDING,
                            Job.started_at
                            < datetime.datetime.now(tz=datetime.timezone.utc)
                            - datetime.timedelta(minutes=self.max_pending_minutes),
                        ),
                    )
                    .values(status=_STATUS_CREATED),
                )
                await session.commit()

            # Create the job queue
            job_id = -1
            async with self.SessionMaker() as session:
                result = await session.execute(
                    select(Job)
                    .with_for_update(of=Job, skip_locked=True)
                    .where(Job.status == _STATUS_CREATED),
                )
                job = result.scalar()
                if job is not None:
                    job_id = job.id  # type: ignore[assignment]
                    job.status = _STATUS_PENDING  # type: ignore[assignment]
                    job.started_at = datetime.datetime.now(tz=datetime.timezone.utc)  # type: ignore[assignment]
                    await session.commit()
            if job_id != -1:
                await _start_job(
                    job_id,
                    self.sqlalchemy_url,
                    self.allowed_commands,
                    self.allowed_arguments,
                )

            # Update the job status (error or done) on finish
            async with self.SessionMaker() as session:
                result = await session.execute(
                    select(Job)
                    .with_for_update(of=Job, skip_locked=True)
                    .where(Job.status == _STATUS_STARTED),
                )
                for job in result.scalars():
                    nb_messages = await session.scalar(
                        select(sqlalchemy.sql.functions.count(Queue.id)).where(
                            and_(Queue.status == _STATUS_CREATED, Queue.job_id == job.id),
                        ),
                    )
                    assert nb_messages is not None
                    _NB_MESSAGE_COUNTER.labels(job.id, job.config_filename).set(1.0 * nb_messages)
                    nb_pending = await session.scalar(
                        select(sqlalchemy.sql.functions.count(Queue.id)).where(
                            and_(Queue.status == _STATUS_PENDING, Queue.job_id == job.id),
                        ),
                    )
                    assert nb_pending is not None
                    _PENDING_COUNTER.labels(job.id, job.config_filename).set(1.0 * nb_pending)
                    if nb_messages == 0 and nb_pending == 0:
                        count_result = await session.scalar(
                            select(sqlalchemy.sql.functions.count(Queue.id)).where(
                                and_(
                                    Queue.status == _STATUS_ERROR,
                                    Queue.job_id == job.id,
                                ),
                            ),
                        )
                        if count_result != 0:
                            job.status = _STATUS_ERROR  # type: ignore[assignment]
                        else:
                            job.status = _STATUS_DONE  # type: ignore[assignment]
                await session.commit()
            async with self.SessionMaker() as session:
                result = await session.execute(select(Job).where(Job.status == _STATUS_STARTED))
                for job in result.scalars():
                    # Restart the too long pending metatiles
                    result = await session.execute(
                        update(Queue)
                        .where(
                            and_(
                                Queue.status == _STATUS_PENDING,
                                Queue.started_at
                                < datetime.datetime.now(tz=datetime.timezone.utc)
                                - datetime.timedelta(minutes=self.max_pending_minutes),
                            ),
                        )
                        .values(status=_STATUS_CREATED),
                    )
                    # Add the job as to be processed
                    if job.config_filename not in self.jobs:
                        self.jobs[job.config_filename] = job.id  # type: ignore[index,assignment]
                await session.commit()

        if not self.jobs:
            await asyncio.sleep(10)

    async def list(self) -> AsyncIterator[Tile]:
        """List the meta tiles in the queue."""
        assert self.SessionMaker is not None
        while True:
            if not self.jobs:
                await self._maintenance()

            if self.jobs:
                config_filename = None
                try:
                    config_filename = next(iter(self.jobs))
                except StopIteration:
                    pass

                if config_filename is None:
                    continue
                job_id = self.jobs.pop(config_filename)
                try:
                    if os.environ.get("TILECLOUD_CHAIN_OBJGRAPH_POSTGRESQL", "0").lower() in (
                        "1",
                        "true",
                        "on",
                    ):
                        for generation in range(3):
                            gc.collect(generation)
                        values = [
                            f"{name}: {number} {diff}"
                            for name, number, diff in objgraph.growth(
                                limit=int(os.environ.get("TILECLOUD_CHAIN_OBJGRAPH_LIMIT", "10")),
                            )
                        ]
                        if values:
                            _LOGGER.debug("Objgraph growth in postgresql:\n%s", "\n".join(values))

                    async with self.SessionMaker() as session:
                        result = await session.execute(
                            select(Queue)
                            .with_for_update(of=Queue, skip_locked=True)
                            .order_by(Queue.id.asc())
                            .where(and_(Queue.status == _STATUS_CREATED, Queue.job_id == job_id)),
                        )
                        sqlalchemy_tile = result.scalar()
                        if sqlalchemy_tile is None:
                            continue
                        sqlalchemy_tile.status = _STATUS_PENDING  # type: ignore[assignment]
                        sqlalchemy_tile.started_at = datetime.datetime.now(tz=datetime.timezone.utc)  # type: ignore[assignment]
                        meta_tile = _decode_message(
                            sqlalchemy_tile.meta_tile,  # type: ignore[arg-type]
                            postgresql_id=sqlalchemy_tile.id,
                        )
                        await session.commit()
                    yield meta_tile
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Error while reading from Postgres")
                    _READ_ERROR_COUNTER.labels(job_id, config_filename).inc()
                    await asyncio.sleep(1)

    async def put_one(self, tile: Tile) -> Tile:
        """Put the meta tile in the queue."""
        assert self.SessionMaker is not None
        async with self.SessionMaker() as session:
            session.add(
                Queue(
                    job_id=tile.metadata["job_id"],
                    zoom=tile.tilecoord.z,
                    meta_tile=_encode_message(tile),
                ),
            )
            await session.commit()
        return tile

    async def delete_one(self, tile: Tile) -> Tile:
        """Delete the meta tile from the queue."""
        assert self.SessionMaker is not None
        async with self.SessionMaker() as session:
            if tile.error:
                if isinstance(tile.error, Exception):
                    _LOGGER.warning(
                        "Error while processing the tile %s %s",
                        tile.tilecoord,
                        tile.formated_metadata,
                        exc_info=tile.error,
                    )

                if not hasattr(tile, "postgresql_id"):
                    _LOGGER.error(
                        "The tile %s %s does not have the postgresql_id attribute",
                        tile.tilecoord,
                        tile.formated_metadata,
                    )
                    return tile
                result = await session.execute(
                    select(Queue)
                    .where(and_(Queue.status == _STATUS_PENDING, Queue.id == tile.postgresql_id))
                    .with_for_update(of=Queue),
                )
                sqlalchemy_tile = result.scalar()
                if sqlalchemy_tile is not None:
                    sqlalchemy_tile.status = _STATUS_ERROR  # type: ignore[assignment]
                    sqlalchemy_tile.error = str(tile.error)  # type: ignore[assignment]
                    await session.commit()
            else:
                if not hasattr(tile, "postgresql_id"):
                    _LOGGER.error(
                        "The tile %s %s does not have the postgresql_id attribute",
                        tile.tilecoord,
                        tile.formated_metadata,
                    )
                    return tile

                await session.execute(
                    delete(Queue).where(
                        and_(Queue.status == _STATUS_PENDING, Queue.id == tile.postgresql_id),
                    ),
                )
                await session.commit()
        return tile

    async def get_one(self, tile: Tile) -> Tile:
        """Get the meta tile from the queue."""
        raise NotImplementedError


async def get_postgresql_queue_store(config: DatedConfig) -> PostgresqlTileStore:
    """Get the postgreSQL queue tile store."""
    conf = config.config.get("postgresql", {})
    sqlalchemy_url = os.environ.get("TILECLOUD_CHAIN_SQLALCHEMY_URL", conf.get("sqlalchemy_url"))
    assert sqlalchemy_url is not None

    tilestore = PostgresqlTileStore(
        max_pending_minutes=conf.get("max_pending_minutes", configuration.MAX_PENDING_MINUTES_DEFAULT),
        sqlalchemy_url=sqlalchemy_url,
        allowed_commands=config.config.get("server", {}).get(
            "allowed_commands",
            configuration.ALLOWED_COMMANDS_DEFAULT,
        ),
        allowed_arguments=config.config.get("server", {}).get(
            "allowed_arguments",
            configuration.ALLOWED_ARGUMENTS_DEFAULT,
        ),
    )
    await tilestore.init()
    return tilestore
