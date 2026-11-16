# Uranium Market Insights

A dashboard for readers researching uranium market context: U.S. utility
contracting, delivery commitments, and the definitions and source dates behind
each measure. Educational market information, not investment advice.

**Prices are synthetic.** The two price cards and monthly price chart contain
invented values in USD/lb U3O8. Real Cameco ingestion/display is blocked pending
written reuse permission. EIA views show imported government data when available;
a clean database shows unavailable data, never an invented EIA fallback.

## Capabilities and limitations

- Interactive ECharts charts with accessible tables, range and category controls.
- EIA Tables 7–10: actual deliveries with reported price, newly signed contracts
  with same-year deliveries, and future contractual minimum/maximum quantities.
- U.S. civilian reactor owners/operators only; no global contracting series.
- Per-value provenance, observation/reporting/delivery periods, publication date,
  retrieval time, source checksum, revisions, and withheld/missing-value status.
- Manual annual EIA refresh; browser refresh does not fetch publisher data.
  Freshness reminders use a 400-day heuristic, not a publisher guarantee.
- Current parser fixtures cover the 2025 report layout. Older/new layouts require
  review. No live feed, forecasts, stock screening, or investment recommendations.

No product screenshot is bundled. After importing permitted EIA data, open the
app at desktop and mobile widths, capture the dashboard with mock notices and
source dates visible, review it for private information, and add the approved
image as `docs/images/dashboard.png`. Do not use a Cameco chart screenshot.

## Local setup

Prerequisites: Ubuntu/WSL2, Git, uv 0.12.2, Python 3.13 (uv can provision it),
Node.js 24/npm, and Docker with Compose v2. Docker Desktop needs Ubuntu WSL
integration enabled. Run commands from the repository root.

```bash
uv sync --directory backend --locked
npm --prefix frontend ci
read -rsp 'Local database password: ' POSTGRES_PASSWORD
export POSTGRES_PASSWORD
printf '\n'
docker compose config --quiet
docker compose up --build -d
docker compose exec api alembic upgrade head
curl --fail --retry 10 --retry-connrefused --retry-delay 1 http://localhost:8000/ready
```

Open http://localhost:5173; API docs: http://localhost:8000/docs. Then follow
[data/eia.md](data/eia.md) to download, preview, and import permitted workbooks.
The original password is required for an existing database volume; changing an
environment variable does not rotate the stored password.

For frontend/backend development without application containers:

```bash
uv run --directory backend --locked uvicorn app.main:app --reload --port 8000
# Separate terminal:
npm --prefix frontend run dev -- --port 5173 --strictPort
```

This supports the synthetic-price view without a database. EIA requires a
reachable PostgreSQL 18 server: set `DATABASE_URL`, run
`uv run --directory backend --locked alembic upgrade head`, then import EIA.
The Compose database has no host-published port; run DB commands inside Compose
or use a separately provisioned local server.

Stop local containers with `docker compose down`; it preserves the database.

## Configuration and architecture

Browser → Vite proxy (development) or nginx (production) → FastAPI → PostgreSQL.
Offline file importers write normalized facts, ingestion runs, revisions and
private checksum-named artifacts. There is no HTTP ingestion/upload endpoint.
Prices use a deterministic Python fixture, independent of the database.

| Variable | Use |
| --- | --- |
| `DATABASE_URL` | Optional full SQLAlchemy psycopg URL; overrides DB fallback settings. Keep secret; percent-encode URL credentials. |
| `POSTGRES_PASSWORD` | Required by Compose; no default. Used by DB and API fallback connection. |
| `DB_HOST`, `DB_PORT`, `DB_USER` | Python fallback host/port, defaults localhost/5432; default user `dashboard`, database `uranium`. |
| `API_PROXY_TARGET` | Vite only; defaults `http://127.0.0.1:8000`, Compose uses `http://api:8000`. |
| `APP_DOMAIN`, `RELEASE_TAG`, `API_DB_PASSWORD` | Production hostname, unique image release tag and separate read-only API password; see AWS guide. |
| `TEST_DATABASE_URL`, `RUN_POSTGRES_TESTS` | Opt-in database integration tests. Use an isolated test DB. |

The frontend uses relative URLs; there is no frontend secret or build-time API
hostname. Same-origin routing needs no CORS middleware. FastAPI debug is off.
`/health` checks process liveness; `/ready` checks DB connection, current migration,
and readable tables. Readiness does not promise imported or fresh observations.
Update its expected revision when adding a schema migration.

## Verification

```bash
uv run --directory backend --locked pytest
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
git diff --check
```

Playwright needs Chromium; use the existing browser container or the install
commands in [verification](docs/verification-commands.md).
Local pytest skips PostgreSQL tests unless explicitly configured.
For the full suite using the running local Compose database:

```bash
docker compose run --rm --no-deps -T --user 0 -e UV_CACHE_DIR=/tmp/uv -e RUN_POSTGRES_TESTS=1 \
  -v "$PWD/backend/tests:/app/tests:ro" \
  api uv run --locked pytest tests
```

The disposable test command uses root so uv can install the locked test dependencies
inside that container; the production API continues to run without root.
Database tests create and roll back isolated schemas. CI checks database tests,
frontend tests/build/browser tests, and production image startup. CI runs only
when the owner later enables it by publishing this reviewed copy.

## Sources and rights

EIA: [Uranium Marketing Annual Report](https://www.eia.gov/uranium/marketing/index.php),
with publication/revision date displayed per observation. Quantities are **thousand
lb U3O8 equivalent**, delivery prices **USD/lb U3O8 equivalent**, counts **contracts**.
Missing/withheld values are null, never zero. Totals overlap their components;
contractual bounds are not probability forecasts. Keep report vintages separate.

The [EIA reuse policy](https://www.eia.gov/about/copyrights_reuse.php) permits
reuse of government data with acknowledgement and publication date; protected
third-party content and the EIA logo have separate restrictions. The retained
fixtures are attributed in `backend/tests/fixtures/eia/sources.json`.

[Cameco terms](https://www.cameco.com/terms-of-use) do not grant this app permission
to republish price data. No real Cameco observations are served. The file-based
adapter is retained for offline testing; a permission-reference string cannot
grant rights. See [source review](data/README.md). Raw artifacts must remain
private and outside web roots. No licence for the application code is asserted
by these source policies; select a code licence before public publication.

## Operations and documentation

- [AWS deployment, backup, rollback and teardown](docs/aws-deployment.md)
- [Production review, specification coverage and verification](docs/review.md)
- [Source publication checklist](docs/publishing.md)
- [EIA source/import guide](data/eia.md)

Troubleshooting: API `/` returns 404 by design. Healthy liveness with EIA 503
usually means missing credentials/migrations or an unreachable DB; check
`docker compose logs --tail=50 api db` locally without sharing unredacted logs.
A typed unavailable response means no matching import. Browser errors with a
working API require checking the proxy target. Withheld chart bars can coexist
with published totals; inspect the table. Never solve these problems by
substituting mock EIA data. See the AWS guide for production-specific commands.
