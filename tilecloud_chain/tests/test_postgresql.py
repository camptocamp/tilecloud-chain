import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from anyio import Path as AnyioPath
from sqlalchemy import and_
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from tilecloud import Tile, TileCoord

from tilecloud_chain import DatedConfig, TileGeneration, controller
from tilecloud_chain.settings import settings
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


@pytest_asyncio.fixture
async def tilestore() -> PostgresqlTileStore:
    return await get_postgresql_queue_store(DatedConfig({}, 0, "config.yaml"))


@pytest.fixture
def SessionMaker() -> sessionmaker:
    engine = create_engine(os.environ["TILECLOUD_CHAIN__POSTGRESQL__SQLALCHEMY_URL"])
    return sessionmaker(engine)  # noqa


@pytest_asyncio.fixture
async def queue(SessionMaker: sessionmaker, tilestore: PostgresqlTileStore) -> tuple[int, int, int]:
    with SessionMaker() as session:
        for job in session.query(Job).filter(Job.name == "test").all():
            session.delete(job)
        session.commit()
    await tilestore.create_job("test", "generate-tiles", Path("config.yaml"))
    with SessionMaker() as session:
        job = session.query(Job).filter(Job.name == "test").one()
        job.status = _STATUS_STARTED
        job_id = job.id
        session.commit()

    await tilestore.put_one(
        Tile(
            TileCoord(0, 0, 0),
            metadata={
                "job_id": job_id,
            },
        ),
    )
    await tilestore.put_one(
        Tile(
            TileCoord(1, 0, 0),
            metadata={
                "job_id": job_id,
            },
        ),
    )
    await tilestore.close()

    with SessionMaker() as session:
        metatile_0_id = session.query(Queue.id).filter(and_(Queue.job_id == job_id, Queue.zoom == 0)).one()[0]
        metatile_1_id = session.query(Queue.id).filter(and_(Queue.job_id == job_id, Queue.zoom == 1)).one()[0]

    yield job_id, metatile_0_id, metatile_1_id

    with SessionMaker() as session:
        session.query(Queue).filter(Queue.job_id == job_id).delete()
        session.query(Job).filter(Job.id == job_id).delete()
        session.commit()


@pytest.mark.asyncio
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
        assert job.tiles_started_at is None
        assert job.meta_tiles_total == 1
        metatiles = session.query(Queue).filter(Queue.job_id == job_id).all()
        assert len(metatiles) == 1
        assert metatiles[0].status == _STATUS_CREATED


@pytest.mark.asyncio
async def test_tiles_started_at_set_on_first_tile(
    queue: tuple[int, int, int],
    SessionMaker: sessionmaker,
    tilestore: PostgresqlTileStore,
):
    job_id, _, _ = queue
    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.tiles_started_at is None

    _ = await anext(tilestore.list())

    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.tiles_started_at is not None


@pytest.mark.asyncio
async def test_get_status_with_eta(
    queue: tuple[int, int, int],
    SessionMaker: sessionmaker,
    tilestore: PostgresqlTileStore,
):
    job_id, _metatile_0_id, _metatile_1_id = queue
    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        job.meta_tiles_total = 10
        job.tiles_started_at = datetime.now(tz=UTC) - timedelta(seconds=100)
        session.commit()

    statuses = await tilestore.get_status(Path("config.yaml"))
    status = next(status for status in statuses if status[0].id == job_id)
    assert status[3] is not None


@pytest.mark.asyncio
async def test_get_status_with_eta_when_remaining_exceeds_total(
    queue: tuple[int, int, int],
    SessionMaker: sessionmaker,
    tilestore: PostgresqlTileStore,
):
    job_id, _metatile_0_id, _metatile_1_id = queue
    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        job.meta_tiles_total = 1
        job.tiles_started_at = datetime.now(tz=UTC) - timedelta(seconds=100)
        session.commit()

    statuses = await tilestore.get_status(Path("config.yaml"))
    status = next(status for status in statuses if status[0].id == job_id)
    assert status[3] is None


@pytest.mark.asyncio
async def test_cancel(
    queue: tuple[int, int, int],
    SessionMaker: sessionmaker,
    tilestore: PostgresqlTileStore,
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


@pytest.mark.asyncio
async def test_maintenance_status_done(
    queue: tuple[int, int, int],
    SessionMaker: sessionmaker,
    tilestore: PostgresqlTileStore,
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


@pytest.mark.asyncio
async def test_maintenance_pending_tile(
    queue: tuple[int, int, int],
    SessionMaker: sessionmaker,
    tilestore: PostgresqlTileStore,
):
    _job_id, metatile_0_id, metatile_1_id = queue

    with SessionMaker() as session:
        metatile_0 = session.query(Queue).filter(Queue.id == metatile_0_id).one()
        metatile_0.status = _STATUS_PENDING
        metatile_0.started_at = datetime.now(tz=UTC) - timedelta(hours=1)
        metatile_1 = session.query(Queue).filter(Queue.id == metatile_1_id).one()
        metatile_1.status = _STATUS_PENDING
        metatile_1.started_at = datetime.now(tz=UTC) - timedelta(hours=1)
        session.commit()

    await tilestore._maintenance()
    with SessionMaker() as session:
        metatile_0 = session.query(Queue).filter(Queue.id == metatile_0_id).one()
        assert metatile_0.status == _STATUS_CREATED
        metatile_1 = session.query(Queue).filter(Queue.id == metatile_1_id).one()
        assert metatile_1.status == _STATUS_CREATED


@pytest.mark.asyncio
async def test_maintenance_pending_job(
    queue: tuple[int, int, int],
    SessionMaker: sessionmaker,
    tilestore: PostgresqlTileStore,
):
    job_id, _metatile_0_id, _metatile_1_id = queue
    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        job.status = _STATUS_PENDING
        job.started_at = datetime.now(tz=UTC) - timedelta(hours=1)

    await tilestore._maintenance()

    with SessionMaker() as session:
        job = session.query(Job).filter(Job.id == job_id).one()
        assert job.status == _STATUS_STARTED


@pytest.mark.asyncio
async def test_put_one_batch_insert(SessionMaker: sessionmaker, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings.postgresql, "queue_insert_batch_size", 2)
    tilestore = await get_postgresql_queue_store(DatedConfig({}, 0, "config.yaml"))

    await tilestore.create_job("test-batch", "generate-tiles", Path("config.yaml"))
    with SessionMaker() as session:
        job = session.query(Job).filter(Job.name == "test-batch").one()
        job.status = _STATUS_STARTED
        job_id = job.id
        session.commit()

    await tilestore.put_one(Tile(TileCoord(0, 0, 0), metadata={"job_id": job_id}))
    with SessionMaker() as session:
        assert session.query(Queue).filter(Queue.job_id == job_id).count() == 0

    await tilestore.put_one(Tile(TileCoord(1, 0, 0), metadata={"job_id": job_id}))
    with SessionMaker() as session:
        assert session.query(Queue).filter(Queue.job_id == job_id).count() == 2

    await tilestore.put_one(Tile(TileCoord(2, 0, 0), metadata={"job_id": job_id}))
    with SessionMaker() as session:
        assert session.query(Queue).filter(Queue.job_id == job_id).count() == 2

    await tilestore.close()
    with SessionMaker() as session:
        assert session.query(Queue).filter(Queue.job_id == job_id).count() == 3
        session.query(Queue).filter(Queue.job_id == job_id).delete()
        session.query(Job).filter(Job.id == job_id).delete()
        session.commit()


@pytest.mark.asyncio
async def test_controller_status_postgresql(SessionMaker: sessionmaker) -> None:
    config_filename = AnyioPath(str(Path(__file__).parent / "tilegeneration/test-postgresql.yaml"))
    gene = TileGeneration(config_filename, configure_logging=False)
    await gene.ainit()
    job_id = None
    try:
        status_lines = await controller.get_status(gene)
        assert "Number of jobs: 0" in status_lines

        tilestore = await get_postgresql_queue_store(DatedConfig({}, 0, config_filename))
        await tilestore.create_job(
            "status-job",
            "generate-tiles --layer=point",
            config_filename,
        )
        with SessionMaker() as session:
            job = session.query(Job).filter(Job.name == "status-job").one()
            job.status = _STATUS_STARTED
            job_id = job.id
            session.commit()

        await tilestore.put_one(Tile(TileCoord(0, 0, 0), metadata={"job_id": job_id}))
        await tilestore.close()

        status_lines = await controller.get_status(gene)
        status_text = "\n".join(status_lines)
        assert "Number of jobs:" in status_text
        assert f"Job {job_id} (status-job) [started]" in status_text
        assert "  To generate: 1" in status_text
    finally:
        if job_id is not None:
            with SessionMaker() as session:
                session.query(Queue).filter(Queue.job_id == job_id).delete()
                session.query(Job).filter(Job.id == job_id).delete()
                session.commit()
        await gene.close()
