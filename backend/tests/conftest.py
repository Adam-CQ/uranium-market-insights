"""Shared isolated PostgreSQL schema, rolled back after each integration test."""
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.dialects.postgresql import insert

from app.db.connection import database_url
from app.db.schema import metrics, observations, runs, sources


@pytest.fixture
def database():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url and os.environ.get("RUN_POSTGRES_TESTS") == "1":
        url = database_url()
    if not url:
        pytest.skip("Set TEST_DATABASE_URL or RUN_POSTGRES_TESTS=1 to run PostgreSQL tests")
    engine = sa.create_engine(url)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                schema = "test_" + uuid4().hex
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
                connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
                yield connection
            finally:
                transaction.rollback()  # Includes the isolated schema and all DDL/data.
    finally:
        engine.dispose()


def _insert_fixture(connection) -> int:
    source_id = connection.execute(insert(sources).values(
        name="Synthetic test source", url="https://example.invalid/test-source",
        cadence="monthly", notes="Synthetic; not Cameco observations",
    ).on_conflict_do_update(index_elements=[sources.c.name], set_={"notes": "Synthetic; not Cameco observations"}).returning(sources.c.id)).scalar_one()
    metric_id = connection.execute(insert(metrics).values(
        source_id=source_id, series_id="test_mock_spot", label="Mock spot indicator",
        unit="USD/lb U3O8", currency="USD", geography="Global (illustrative only)",
        covered_population="No surveyed population", measure_type="price_indicator",
        methodology_notes="Invented fixture; observation_date is a month-end date",
    ).on_conflict_do_nothing(index_elements=[metrics.c.series_id]).returning(metrics.c.id)).scalar_one_or_none()
    if metric_id is None:
        metric_id = connection.execute(sa.select(metrics.c.id).where(metrics.c.series_id == "test_mock_spot")).scalar_one()
    checksum = sha256(b"synthetic fixture June 2025: 76.00").hexdigest()
    run_id = connection.execute(runs.insert().values(
        source_id=source_id, source_url="https://example.invalid/test-source",
        source_table="mock prices", source_vintage="test-mock-v1",
        retrieved_at=datetime.now(timezone.utc), artifact_sha256=checksum,
        artifact_path="generated:test-fixture", method_version="test-v1",
        status="succeeded", notes="Generated locally, not retrieved from a publisher",
    ).returning(runs.c.id)).scalar_one()
    values = dict(metric_id=metric_id, source_id=source_id, ingestion_run_id=run_id,
                  artifact_sha256=checksum, observation_date=date(2025, 6, 30),
                  raw_value="76.00", normalized_value=Decimal("76.00"),
                  value_status="available", data_status="mock", quality_notes="Invented test value")
    observation_id = connection.execute(insert(observations).values(**values).on_conflict_do_nothing(
        constraint="uq_observation_artifact_period"
    ).returning(observations.c.id)).scalar_one_or_none()
    if observation_id is None:
        observation_id = connection.execute(sa.select(observations.c.id).where(
            observations.c.metric_id == metric_id, observations.c.artifact_sha256 == checksum,
            observations.c.observation_date == date(2025, 6, 30),
        )).scalar_one()
    return observation_id


@pytest.fixture
def insert_fixture():
    """Create a synthetic record inside the caller's isolated transaction."""
    return _insert_fixture
