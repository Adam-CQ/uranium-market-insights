# Reproduce local verification

No AWS access is required. Use only an isolated test database. These commands
install existing locked dependencies, not new project dependencies. Caches are
kept within this checkout. Docker must be running.

```bash
export UV_CACHE_DIR="$PWD/.cache/uv"
export DOCKER_CONFIG="$PWD/.cache/docker"
uv sync --directory backend --locked
npm --prefix frontend ci --cache "$PWD/.cache/npm"
uv run --directory backend --locked pytest
npm --prefix frontend test
npm --prefix frontend run build
docker build -t uranium-api:review backend
docker build -t uranium-frontend:review --target production frontend
export RELEASE_TAG=review APP_DOMAIN=localhost
read -rsp 'New isolated test DB password: ' POSTGRES_PASSWORD
export POSTGRES_PASSWORD
read -rsp 'Separate test API password: ' API_DB_PASSWORD
export API_DB_PASSWORD
printf '\n'
# Choose a new name, or supply the original password if reusing its DB volume.
export COMPOSE_PROJECT_NAME=uranium-local-review
docker compose -f compose.production.yaml config --quiet
docker compose -f compose.production.yaml up -d db migrate api frontend
docker compose -f compose.production.yaml exec -T frontend \
  wget -q -O - http://127.0.0.1:8080/ready
docker compose -f compose.production.yaml exec -T frontend \
  wget -q -O - 'http://127.0.0.1:8080/api/v1/contracts/signings?scope=us'
docker compose -f compose.production.yaml exec -T api id
docker compose -f compose.production.yaml exec -T frontend id
# Writable disposable test container, not the read-only production API:
docker run --rm --network "${COMPOSE_PROJECT_NAME}_default" --user 0 \
  -e POSTGRES_PASSWORD -e DB_HOST=db -e RUN_POSTGRES_TESTS=1 -e UV_CACHE_DIR=/tmp/uv \
  -v "$PWD/backend/tests:/app/tests:ro" \
  uranium-api:review uv run --locked pytest tests
docker compose -f compose.production.yaml exec -T api alembic check
docker compose -f compose.production.yaml run --rm migrate
# Run only AFTER the up command and readiness check have completed:
docker run --rm --init --ipc=host --network "${COMPOSE_PROJECT_NAME}_default" \
  --user "$(id -u):$(id -g)" -e PLAYWRIGHT_BASE_URL=http://frontend:8080 \
  -v "$PWD/frontend:/work" -w /work \
  mcr.microsoft.com/playwright:v1.65.1-noble npm run test:e2e
docker run --rm -e APP_DOMAIN=localhost \
  -v "$PWD/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker compose -f compose.production.yaml down
git diff --check
```

The Playwright container includes Chromium. Alternatively, run the Vite browser
suite locally after installing Chromium into a checkout-local cache:

```bash
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/playwright"
(cd frontend && npx playwright install chromium)
npm --prefix frontend run test:e2e
```

Browser installation can require additional OS packages; use the container
alternative rather than changing your host if those are absent. Never point the
fixture-intercepting suite at someone else's website. E2E tests intercept EIA and
price API calls; they validate charts and controls against test doubles. Separate
nginx/API and PostgreSQL checks above exercise actual DB-backed routes. They do
not replace a manual live-source-to-chart comparison after production import.

To verify production role separation while the isolated stack is running:

```bash
docker compose -f compose.production.yaml exec -T api python - <<'PY'
import sqlalchemy as sa
from app.db.connection import database_engine
with database_engine().connect() as connection:
    assert connection.scalar(sa.text('SELECT current_user')) == 'uranium_reader'
    for privilege in ('INSERT', 'UPDATE'):
        assert not connection.scalar(sa.text(
            "SELECT has_table_privilege(current_user, 'market_observation', :privilege)"
        ), {'privilege': privilege})
print('Read-only runtime role verified')
PY
```
