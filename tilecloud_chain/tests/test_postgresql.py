import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import and_
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from tilecloud import Tile, TileCoord

from tilecloud_chain import DatedConfig
from tilecloud_chain.store.postgresql import (
    _STATUS_CANCELLED,
    _STATUS_CREATED,
    _STATUS_DONE,
    _STATUS_ERROR,
    _STATUS_PENDING,
    _STATUS_STARTED,
    Job,
    PostgresqlTileStore,
    Queue,
    get_postgresql_queue_store,
)


@pytest.fixture
def tilestore(event_loop: asyncio.AbstractEventLoop) -> PostgresqlTileStore:
    return event_loop.run_until_complete(get_postgresql_queue_store(DatedConfig({}, 0, "config.yaml")))


@pytest.fixture
def SessionMaker() -> sessionmaker:
    engine = create_engine(os.environ["TILECLOUD_CHAIN_SQLALCHEMY_URL"])
    return sessionmaker(engine)  # noqa


@pytest.fixture
def queue(SessionMaker: sessionmaker, tilestore: PostgresqlTileStore) -> tuple[int, int, int]:
    with SessionMaker() as session:
        for job in session.query(Job).filter(Job.name == "test").all():
            session.delete(job)
        session.commit()
    asyncio.get_event_loop().run_until_complete(tilestore.create_job("test", "generate-tiles", "config.yaml"))
    with SessionMaker() as session:
        job = session.query(Job).filter(Job.name == "test").one()
        job.status = _STATUS_STARTED
        job_id = job.id
        session.commit()

    asyncio.get_event_loop().run_until_complete(
        tilestore.put_one(
            Tile(
                TileCoord(0, 0, 0),
                metadata={
                    "job_id": job_id,
                },
            )
        )
    )
    asyncio.get_event_loop().run_until_complete(
        tilestore.put_one(
            Tile(
                TileCoord(1, 0, 0),
                metadata={
                    "job_id": job_id,
                },
            )
        )
    )

    with SessionMaker() as session:
        metatile_0_id = session.query(Queue.id).filter(and_(Queue.job_id == job_id, Queue.zoom == 0)).one()[0]
        metatile_1_id = session.query(Queue.id).filter(and_(Queue.job_id == job_id, Queue.zoom == 1)).one()[0]

    yield job_id, metatile_0_id, metatile_1_id

    with SessionMaker() as session:
        session.query(Queue).filter(Queue.job_id == job_id).delete()
        session.query(Job).filter(Job.id == job_id).delete()
        session.commit()


async def test_retry(queue: tuple[int, int, int], SessionMaker: sessionmaker, tilestore: PostgresqlTileStore):
    job_id, _, _ = queue

    tile_1 = await anext(tilestore.list())
    tile_2 = await anext(tilestore.list())

    tile_1.error = "test error"

    await tilestore.delete_one(tile_1)
    await tilestore.delete_one(tile_2)

    with SessionMaker() as session:
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 1
        assert metatiles[0].error == "test error"

    await tilestore._maintenance()

    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_ERROR

    await tilestore.retry(job_id, Path("config.yaml"))

    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_CREATED
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 1
        assert metatiles[0].status == _STATUS_CREATED


async def test_cancel(
    queue: tuple[int, int, int], SessionMaker: sessionmaker, tilestore: PostgresqlTileStore
):
    job_id, _, _ = queue

    tile_1 = await anext(tilestore.list())

    await tilestore.delete_one(tile_1)

    with SessionMaker() as session:
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 1

    await tilestore.cancel(job_id, Path("config.yaml"))

    with SessionMaker() as session:
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 0
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_CANCELLED


async def test_maintenance_status_done(
    queue: tuple[int, int, int], SessionMaker: sessionmaker, tilestore: PostgresqlTileStore
):
    job_id, _, _ = queue

    tile_1 = await anext(tilestore.list())
    tile_2 = await anext(tilestore.list())

    await tilestore.delete_one(tile_1)
    await tilestore.delete_one(tile_2)

    with SessionMaker() as session:
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 0

    await tilestore._maintenance()

    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_DONE


async def test_maintenance_pending_tile(
    queue: tuple[int, int, int], SessionMaker: sessionmaker, tilestore: PostgresqlTileStore
):
    job_id, metatile_0_id, metatile_1_id = queue

    with SessionMaker() as session:
        metatile_0 = session.query(Queue).filter(Queue.id == metatile_0_id).one()
        metatile_0.status = _STATUS_PENDING
        metatile_0.started_at = datetime.now() - timedelta(hours=1)
        metatile_1 = session.query(Queue).filter(Queue.id == metatile_1_id).one()
        metatile_1.status = _STATUS_PENDING
        metatile_1.started_at = datetime.now() - timedelta(hours=1)
        session.commit()

    await tilestore._maintenance()
    with SessionMaker() as session:
        metatile_0 = session.query(Queue).filter(Queue.id == metatile_0_id).one()
        assert metatile_0.status == _STATUS_CREATED
        metatile_1 = session.query(Queue).filter(Queue.id == metatile_1_id).one()
        assert metatile_1.status == _STATUS_CREATED


async def test_maintenance_pending_job(
    queue: tuple[int, int, int], SessionMaker: sessionmaker, tilestore: PostgresqlTileStore
):
    job_id, metatile_0_id, metatile_1_id = queue
    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        job.status = _STATUS_PENDING
        job.started_at = datetime.now() - timedelta(hours=1)

    await tilestore._maintenance()

    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_STARTED
