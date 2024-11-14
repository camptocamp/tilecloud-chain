import os
from datetime import datetime, timedelta

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
def tilestore() -> PostgresqlTileStore:
    return get_postgresql_queue_store(DatedConfig({}, 0, "config.yaml"))


@pytest.fixture
def SessionMaker() -> sessionmaker:
    engine = create_engine(os.environ["TILECLOUD_CHAIN_SQLALCHEMY_URL"])
    SessionMaker = sessionmaker(engine)  # noqa
    return SessionMaker


@pytest.fixture
def queue(SessionMaker: sessionmaker, tilestore: PostgresqlTileStore) -> tuple[int, int, int]:
    tilestore.create_job("test", "generate-tiles", "config.yaml")
    with SessionMaker() as session:
        job = session.query(Job).filter(Job.name == "test").one()
        job.status = _STATUS_STARTED
        job_id = job.id
        session.commit()

    tilestore.put_one(
        Tile(
            TileCoord(0, 0, 0),
            metadata={
                "job_id": job_id,
            },
        )
    )
    tilestore.put_one(
        Tile(
            TileCoord(1, 0, 0),
            metadata={
                "job_id": job_id,
            },
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


def test_retry(queue: tuple[int, int, int], SessionMaker: sessionmaker, tilestore: PostgresqlTileStore):
    job_id, _, _ = queue

    tile_1 = next(tilestore.list())
    tile_2 = next(tilestore.list())

    tile_1.error = "test error"

    tilestore.delete_one(tile_1)
    tilestore.delete_one(tile_2)

    with SessionMaker() as session:
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 1
        assert metatiles[0].error == "test error"

    tilestore._maintenance()

    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_ERROR

    tilestore.retry(job_id, "config.yaml")

    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_STARTED
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 1
        assert metatiles[0].status == _STATUS_CREATED


def test_cancel(queue: tuple[int, int, int], SessionMaker: sessionmaker, tilestore: PostgresqlTileStore):
    job_id, _, _ = queue

    tile_1 = next(tilestore.list())

    tilestore.delete_one(tile_1)

    with SessionMaker() as session:
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 1

    tilestore.cancel(job_id, "config.yaml")

    with SessionMaker() as session:
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 0
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_CANCELLED


def test_maintenance_status_done(
    queue: tuple[int, int, int], SessionMaker: sessionmaker, tilestore: PostgresqlTileStore
):
    job_id, _, _ = queue

    tile_1 = next(tilestore.list())
    tile_2 = next(tilestore.list())

    tilestore.delete_one(tile_1)
    tilestore.delete_one(tile_2)

    with SessionMaker() as session:
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 0

    tilestore._maintenance()

    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_DONE


def test_maintenance_pending_tile(
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

    tilestore._maintenance()
    with SessionMaker() as session:
        metatile_0 = session.query(Queue).filter(Queue.id == metatile_0_id).one()
        assert metatile_0.status == _STATUS_CREATED
        metatile_1 = session.query(Queue).filter(Queue.id == metatile_1_id).one()
        assert metatile_1.status == _STATUS_CREATED


def test_maintenance_pending_job(
    queue: tuple[int, int, int], SessionMaker: sessionmaker, tilestore: PostgresqlTileStore
):
    job_id, metatile_0_id, metatile_1_id = queue
    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        job.status = _STATUS_PENDING
        job.started_at = datetime.now() - timedelta(hours=1)

    tilestore._maintenance()

    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_STARTED
