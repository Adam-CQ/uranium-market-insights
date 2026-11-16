# Production readiness review

Review date: 2026-11-16. Scope: current application, source handling and
production deployment configuration. No deployment is claimed.

## Requirements and implementation

| Requirement | Current result |
| --- | --- |
| Spot/term cards and monthly range chart | Implemented with explicit invented values only; real Cameco history is unmet and permission-blocked. |
| EIA contracting | Tables 7–10 implemented, U.S. population, separate report/delivery periods and category controls. 2025 layout validated by fixtures; no multi-year backfill promised. |
| Source dates, units, provenance, revisions | Implemented per value/run. Identical replay is idempotent; changed newer values retain prior versions. Retrieval refers to the artifact that introduced the value, not necessarily the latest check. |
| Missing/withheld data | Nulls and W preserved; totals remain distinct; no suppression reconstruction or mock EIA fallback. |
| Source metadata endpoint | `/api/v1/sources` not implemented. Metadata exists inline; a dedicated catalogue remains a product decision. |
| Combined market summary | Legacy synthetic preview only, unused by current dashboard. Not a real EIA/Cameco aggregate. |
| Supply/demand, nuclear capacity, global contracting | Deferred; no verified licensed dataset or fabricated live feature. |
| Education and accessibility | Product glossary/guides, chart text/table alternatives, labelled controls, status/alert/retry and empty states retained. Browser accessibility still needs a human keyboard/screen-reader review. |


## Security and operational findings

- API is read-only, debug off, no wildcard CORS or unauthenticated write routes.
  Relative browser URLs work through the dev or production proxy. No credentials
  enter the frontend build. Production does not route API documentation publicly.
- Existing Pydantic/query checks validate dates, scope, table numbers and report
  years; frontend runtime validation checks units, status and EIA link origins.
  React escapes text. Parser bounds limit workbook/file size; imports are operator
  commands, not untrusted public uploads. No broad auth system was added.
- Production builds static frontend assets rather than exposing Vite. nginx adds
  security headers/CSP; inline styles remain permitted for ECharts. API/nginx use
  non-root UIDs, dropped capabilities, read-only root filesystems and tmpfs.
  Caddy remains the privileged edge for ports/TLS; PostgreSQL uses its standard
  image startup/user behavior. Avoid mounting the Docker socket.
- Production uses a separate SELECT-only `uranium_reader` role for the API;
  administrator credentials stay in DB/operator services. Initial role grants
  apply only on new production volumes. PostgreSQL TCP health gates migrations; migration completion gates API startup;
  readiness verifies current revision/readable tables. No automatic destructive
  schema migration or source scraping. The current revision check must be updated
  with a future Alembic revision. Readiness does not assert data freshness.
- DB connections time out in five seconds and SQL parameters are hidden by
  SQLAlchemy. Public DB errors are generic. Logs remain operator-private;
  importer CLI errors can contain source cells, so do not publish tracebacks.
- No tracked `.env`, `data/raw`, or `data/processed` files were found. No `.env`
  or secret was read or changed. Build contexts exclude `.env*` and caches.
  This is a working-tree review, not certification that all Git history is free
  of secrets; separately scan the final product export before publication.
- Runtime dependency versions are pinned. npm's locked installation reported zero
  vulnerabilities at review time; a complete Python/base-image vulnerability
  scan was not performed. Moving image tags and action major tags require supply
  chain review before public release; use reviewed immutable digests/SHAs.
- Source rights checked on 2026-11-16: [EIA government data reuse](https://www.eia.gov/about/copyrights_reuse.php)
  supports these survey tables with attribution/publication date, excluding
  separately protected material/logos. [Cameco terms](https://www.cameco.com/terms-of-use)
  require prior written consent beyond their limited personal-use grant.
  Real Cameco publication is blocked, not authorised by a permission string.
- No project code licence exists. Owner must choose one before public source
  publication. Third-party data rights and software licensing are separate.

## Remaining release decisions and blockers

Approve the EIA/synthetic-price scope, code licence, region/domain/budget,
image digests and vulnerability review, alert recipient, patch responsibility,
and tested off-host backup/restore. Real Cameco publication requires permission
and separately implemented/reviewed integration. Public use of EIA-only data
with honest synthetic-price labels does not require resolving Cameco rights,
because no Cameco observations are served. Real Cameco price history remains unavailable.

Single-host downtime and manual refresh are explicit tradeoffs. An open read API
has no per-user quota; nginx timeouts/body limits and bounded input validation
are baseline protection, not measured DDoS capacity. Load testing and stronger
edge controls depend on expected public traffic. No paid protection service was
added speculatively.

## Verification

Reproduction commands: [verification-commands.md](verification-commands.md).

| Command/check | Result |
| --- | --- |
| `uv run --directory backend --locked pytest` | 66 passed, 22 PostgreSQL tests skipped without a host DB. |
| Isolated PostgreSQL container: `uv run --locked pytest tests` | **88 passed, none skipped**. |
| `npm --prefix frontend test` | **10 passed**. |
| `npm --prefix frontend run build` | Passed TypeScript and build. |
| Production API/frontend image builds | Passed. |
| Chromium against production static assets, desktop/mobile | **8 passed**, using intercepted API fixtures. |
| Clean production Compose startup and nginx/API routing | Passed; readiness and typed empty EIA response verified. |
| `alembic check`, repeated migration, read-only role privilege checks | Passed. |
| `git diff --check`, local Markdown link check | Passed. |

The source tree contains no standalone demos or demo-only dependencies. Database
integrity helpers live in the test suite; frontend test prices are outside the
application source. Retained package versions did not change when removing the
two unused optional dependencies.

Known warnings: Starlette's HTTPX test-client integration is deprecated, and the
frontend build reports a 794 kB JavaScript chunk (263 kB gzip). No dependency was
added to address these warnings. Full reproduction commands are linked above.

The isolated verification stack was stopped; its named volumes remain. Existing
local services and data were untouched. No commit, push, deployment or Git history
change was performed.
