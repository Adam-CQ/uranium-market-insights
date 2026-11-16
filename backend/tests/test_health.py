from fastapi.testclient import TestClient

from app.main import app
from app.api.contracts import contract_connection
import pytest
import sqlalchemy as sa
from fastapi import HTTPException


@pytest.mark.parametrize("revision,broken,expected", [
    ("0001_provenance", False, 200),
    ("older", False, 503),
    ("0001_provenance", True, 503),
])
def test_readiness_requires_current_readable_schema(revision, broken, expected):
    class Connection:
        def scalar(self, query):
            return revision

        def execute(self, query):
            if broken:
                raise sa.exc.SQLAlchemyError("private database detail")

    app.dependency_overrides[contract_connection] = lambda: Connection()
    try:
        with TestClient(app) as client:
            response = client.get("/ready")
        assert response.status_code == expected
        assert "private database detail" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_readiness_does_not_claim_ready_without_database():
    def unavailable():
        raise HTTPException(503, "Database unavailable")

    app.dependency_overrides[contract_connection] = unavailable
    try:
        with TestClient(app) as client:
            assert client.get("/ready").status_code == 503
            assert client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_health_returns_ok():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
