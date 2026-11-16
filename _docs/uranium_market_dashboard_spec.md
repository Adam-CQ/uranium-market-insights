# Uranium Market Insights — Product Specification

## Purpose and scope

Provide traceable uranium market context for readers researching U.S. utility
contracting and delivery commitments. The app provides educational market
information, not investment advice, stock screening or trading recommendations.

The current release combines real imported EIA data with explicitly synthetic
monthly price indicators. Real Cameco prices are not implemented in the read
API and must not be published without written permission covering acquisition,
normalisation, storage and display. Public availability and attribution alone
do not establish reuse rights.

## Product principles

- Display the unit, observation/reporting period, source, publication date,
  retrieval time and geographic scope alongside each measure where available.
- Clearly distinguish observed, revised, synthetic, missing and withheld values.
- Preserve signing year, delivery year and report vintage as separate concepts.
- Never reconstruct withheld data, interpolate missing observations, mix report
  vintages into one forecast, or silently substitute mock EIA data.
- Do not imply real-time updates or represent contractual bounds as probabilities.
- Keep original artifacts private and preserve checksums and revision history.

## Dashboard

### Market snapshot

Show synthetic spot and long-term price indicators in USD/lb U3O8, their latest
observation month and changes over the selected range. Label them as mock in
cards and charts. Do not claim external source retrieval or publication dates.

Show the latest imported EIA Table 8 total contract count with its U.S. scope,
report year, same-year-delivery qualification and source publication/revision
date. Source freshness must identify the relevant measure and source cadence.
The current 400-day freshness reminder is a heuristic, not a publisher guarantee.

### Price history

Plot separate synthetic spot and long-term monthly series, with full-range and
last-three-month selectors and an accessible data table. Explain that published
market indicators differ from privately negotiated transaction prices. The
manual Cameco guide links to the source and its terms; viewing that source does
not import, refresh or validate the app's invented values.

### EIA contracting and deliveries

Keep four views and their units separate:

| Table | Measure | Dimensions |
| --- | --- | --- |
| 7 | Delivered quantities with reported price and weighted-average delivery prices | Material, contract type, reporting/actual delivery year |
| 8 | Contracts signed in the reporting year with deliveries received that year: count, quantity and weighted price | Contract type and reporting/same-year delivery period |
| 9 | Future purchases under contracts signed in the reporting year | Delivery year, minimum/maximum, published horizon totals |
| 10 | Future purchases under contracts in effect at reporting year-end | Supplier scope, delivery year, minimum/maximum, horizon totals |

Population: owners/operators of U.S. civilian nuclear power reactors. Supplier
origin does not change that buyer population. Quantities use thousand pounds
U3O8 equivalent, delivery prices use USD/lb U3O8 equivalent, counts use contracts.
No inflation or scale conversion is applied. Totals overlap their components;
never add them together or sum weighted-average prices. Preserve W as withheld
and null as unavailable, never zero. Published horizon totals remain separate
from annual plotted components.

### Explanations and accessibility

Retain the glossary, source details, signing-versus-delivery explanation, chart
text alternatives and exact-value tables. Label controls and provide accessible
loading, retry, error and empty states. Support desktop and narrow mobile views.
Clarify that nuclear capacity is a demand driver, not a direct uranium-demand
series, and a scenario supply gap does not prove an observed shortage.

## Sources and ingestion

- [EIA Uranium Marketing Annual Report](https://www.eia.gov/uranium/marketing/index.php):
  annual official workbooks, Tables 7–10. The parser currently validates the 2025
  report layout. Verify each report year and publication/revision date before
  import; stable workbook URLs can change. Retain raw bytes and acquisition times.
- [EIA reuse policy](https://www.eia.gov/about/copyrights_reuse.php): acknowledge
  government data and publication dates; separately protected third-party content,
  photographs and logos are not covered by the same permission.
- [Cameco price source](https://www.cameco.com/invest/markets/uranium-price) and
  [terms](https://www.cameco.com/terms-of-use): the offline adapter is tested with
  invented fixtures. No live downloader, schedule or public real-price path is
  enabled. A supplied permission-reference string does not grant permission.

Imports are manual operator commands, not HTTP endpoints. Repeated identical
artifacts must not duplicate facts. Newer changed observations retain prior
versions; invalid layouts, older changed snapshots and invalid units fail for
review. Do not expose raw files as public assets. See [EIA operations](../data/eia.md)
and [source rights](../data/README.md).

## Data model and API

PostgreSQL stores data sources, metric definitions, ingestion runs and observations.
Retain unit, currency, population, measure type, source URL/table, publication date,
vintage, retrieval time, checksum, raw value, normalised value, status and revision
links. Schema changes require a new Alembic migration.

Current read endpoints:

- `/api/v1/prices/uranium?from=YYYY-MM&to=YYYY-MM`: synthetic monthly prices.
- `/api/v1/market/summary`: legacy synthetic preview; not the dashboard's EIA source.
- `/api/v1/contracts/signings?scope=us&report_year=YYYY`: Table 8.
- `/api/v1/contracts/deliveries?scope=us&report_year=YYYY`: Table 7.
- `/api/v1/contracts/future-deliveries?scope=us&report_year=YYYY&table=9`: Table 9 or 10.
- `/health`: process liveness; `/ready`: database connection and expected schema.

Metadata is returned inline. `/api/v1/sources` and a combined real-data summary
are not implemented. Invalid query parameters return 422; unavailable DB access
returns 503. A configured database without matching imports returns typed empty
EIA responses without a mock fallback.

## Architecture and operations

React, TypeScript, Vite and Apache ECharts form the frontend. FastAPI/Pydantic
serve HTTP; SQLAlchemy/psycopg access PostgreSQL; Alembic manages migrations.
Local development uses uv, npm and Docker Compose. Production uses static nginx
assets behind Caddy HTTPS and a separate SELECT-only API database role.

Require deterministic parser/API/schema tests, frontend contract/component and
browser tests, locked builds, migration ordering, private credentials/artifacts,
readiness checks and tested backup/restore. Keep local use independent of AWS.
See [deployment operations](../docs/aws-deployment.md).

## Deferred capabilities

Real Cameco prices require permission and a separately reviewed database-backed
read integration. Supply/demand scenarios, nuclear capacity projections and
global contracting need suitable datasets, source definitions and reuse rights.
No forecasts, continuous ingestion, queues, WebSocket feeds or analytical file
storage are required by the current product. Add infrastructure only when a
concrete product requirement justifies its operational cost.
