from fastapi import FastAPI
from fastapi import HTTPException
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError

from app.api.market import router
from app.api.contracts import router as contracts_router
from app.api.contracts import Connection
from app.db.schema import metadata

app = FastAPI(title="Uranium Market Dashboard", version="0.1.0")
app.include_router(router)
app.include_router(contracts_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Report process liveness independently of database availability."""
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
def ready(connection: Connection) -> dict[str, str]:
    """Require the expected migration and readable product tables, not imported data."""
    try:
        revision = connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
        if revision != "0001_provenance":
            raise HTTPException(503, "Database migration is not current")
        for table in metadata.sorted_tables:
            connection.execute(sa.select(table).limit(0))
    except SQLAlchemyError:
        raise HTTPException(503, "Database schema is not ready") from None
    return {"status": "ready"}
