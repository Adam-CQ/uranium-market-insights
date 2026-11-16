# AWS deployment runbook — review before executing

Checked against official AWS documentation on **2026-11-16**. No AWS commands
were executed during preparation. The commands below are future operator steps;
creating infrastructure incurs charges. Local verification is in [review.md](review.md).

## Architecture and decision

Recommend one **Lightsail Linux/Unix Ubuntu VM** for a small, public, read-only
initial release. Run `compose.production.yaml`: Caddy terminates HTTPS → nginx
serves React assets and proxies relative `/api`, `/health`, `/ready` paths →
FastAPI reads PostgreSQL 18. Only 80/443 are published. PostgreSQL and the API
have no public port. Manual ingestion runs in a one-off API container. Persistent
Docker volumes retain PostgreSQL and TLS state; private raw artifacts live on
the VM outside web roots. The application has no AWS SDK dependency.

This is a single-host design: host failure causes downtime, releases briefly
interrupt service, and the owner patches Ubuntu, Docker, PostgreSQL and images.
Start with an x86_64 bundle with at least 2 GB RAM; 4 GB is a safer starting
point if building on-host. Measure memory, disk and response times before choosing
final capacity. These sizes are recommendations, not measured capacity guarantees.

| Alternative | Tradeoff |
| --- | --- |
| EC2 + the same Compose stack | More flexible IAM/network/storage controls; more infrastructure decisions and separately billed resources. |
| ECS/Fargate + ALB + RDS PostgreSQL | Managed tasks/database, better availability options; substantially more networking, IAM, migration-task and billing complexity for this small app. Prefer if uptime requirements justify it. |
| Lightsail container service | Managed container deployments; durable database/artifact storage must be external. The current private artifact path model needs adaptation before using it. |

No load balancer, NAT gateway, Redis, queue, CDN or scheduled scraper is needed
for this first release. Charges can include the VM bundle, excess transfer,
snapshots, public IPv4/static IP under applicable pricing, optional extra disks,
DNS/domain registration and external backup storage. Stopping an instance is
not teardown. Check the selected region's current prices and set a budget alert
before provisioning; no free-tier assumptions or fixed cost estimate is made.

## Official references

These support the infrastructure procedure; package-specific instructions should
also be reviewed when selecting host software versions.

- [Create a Linux/Unix Lightsail instance](https://docs.aws.amazon.com/lightsail/latest/userguide/getting-started-with-amazon-lightsail.html)
- [CLI instance creation parameters](https://docs.aws.amazon.com/cli/latest/reference/lightsail/create-instances.html)
- [Create and attach a static IP](https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-create-static-ip.html)
- [Lightsail firewall scope](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html)
- [Automatic snapshots and seven-day retention](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-configuring-automatic-snapshots.html)
- [Restore an instance from a snapshot](https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-create-instance-from-snapshot.html)
- [Snapshot storage billing](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-snapshots-in-amazon-lightsail.html)
- [Managed Lightsail container service alternative](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services.html)

## Before any public release

1. Approve **EIA + explicitly synthetic prices** as the release scope. Real Cameco
   acquisition, storage or publication remains blocked until written permission
   covers that intended use and a separately reviewed real-price read path exists.
   No production task invokes the Cameco importer.
2. Select region, hostname, VM capacity, budget, uptime objective, and an operator.
   This runbook assumes one host and manual annual EIA refresh.
3. Decide recovery targets. A proposed minimum is daily off-host backups (up to
   24 hours data loss) and restoration within one working day; these are targets,
   not validated service guarantees. Perform a restore drill before release.
4. Review source policies and application/dependency licensing. There is no
   project licence file; the owner must select one before publishing source.
5. Resolve image tags to reviewed immutable digests for release. Python, Node,
   uv, PostgreSQL, nginx and Caddy bases currently use tags; no invented digests
   are supplied. Record resolved digests, scan final images with your approved
   scanner, and retain previous application images. Never change PostgreSQL's
   major version against an existing volume without a tested upgrade plan.
6. Obtain AWS access yourself using MFA and least privilege. Do not put AWS
   credentials on this VM or in the app. Provision via the console below; the
   running application needs no AWS permissions.

## Provisioning, performed later by the owner

1. In Lightsail, create a Linux/Unix **OS-only Ubuntu LTS**, x86_64 instance in
   the approved region. Choose the reviewed bundle and SSH key. Enable daily
   automatic snapshots. Name it `uranium-production` or record your chosen name.
2. Allocate and attach a static IPv4 in that region. Create the chosen DNS A
   record pointing to it. Only add AAAA if IPv6 routing/firewall is configured.
3. Configure IPv4 **and IPv6** public firewalls: TCP 80/443 open for the website;
   TCP 22 restricted to the operator's source CIDR. Remove other inbound rules.
   Confirm no 5432, 8000, 8080 or 5173 public access. AWS's public firewall does
   not govern private-IP traffic; published ports and host rules still matter.
4. Connect over SSH. Install supported Docker Engine and Compose v2 using
   [Docker's Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
   Apply host security updates and arrange unattended security patches/reboots.
   Docker access is privileged; limit it to operators.
5. Create a private application directory, transfer only the reviewed production
   files, and keep release artifacts for rollback. Do not copy `.git`, `.env`,
   local data, caches, test outputs or credentials. A reviewed file export can
   include `backend/{app,migrations,alembic.ini,pyproject.toml,uv.lock,Dockerfile,.dockerignore}`,
   `frontend/{src,index.html,package.json,package-lock.json,tsconfig.json,vite.config.ts,Dockerfile,nginx.conf,.dockerignore}`,
   `deploy/{Caddyfile,init-reader.sh}` and `compose.production.yaml`. Preserve these paths.

## Build and validate privately

Run inside the application directory on the VM. Supply a unique release tag
and a DNS hostname you control, without a URL scheme/path. The password prompt
avoids command-line literals and shell history. Retain the credential in your
approved password manager; it is also accessible to privileged Docker operators.
Do not run `docker compose config` without `--quiet` or share container inspect
output: environment values include the database password.

```bash
export RELEASE_TAG=release-20261116-1
export APP_DOMAIN=uranium.example.com   # replace with your actual hostname
read -rsp 'Database password: ' POSTGRES_PASSWORD
export POSTGRES_PASSWORD
read -rsp 'Separate read-only API password: ' API_DB_PASSWORD
export API_DB_PASSWORD
printf '\n'
docker compose -f compose.production.yaml config --quiet
docker compose -f compose.production.yaml build --pull
# Optional image inventory; no environment values:
docker image inspect uranium-api:"$RELEASE_TAG" uranium-frontend:"$RELEASE_TAG" \
  --format '{{.Id}} {{json .RepoDigests}}'
docker compose -f compose.production.yaml up -d db
# Explicit migration step fails before replacing the running application:
docker compose -f compose.production.yaml run --rm migrate
docker compose -f compose.production.yaml up -d api frontend
docker compose -f compose.production.yaml exec -T frontend \
  wget -q -O - http://127.0.0.1:8080/ready
docker compose -f compose.production.yaml exec -T frontend \
  wget -q -O - http://127.0.0.1:8080/api/v1/contracts/signings?scope=us
```

The second command may need retrying while API readiness becomes healthy. A
new database should return EIA `data_status=unavailable`; this is valid, but
public launch should wait for a verified EIA import. Migration is a one-off
service gated on PostgreSQL health; API startup additionally depends on its
successful completion. Runtime does not install packages or run migrations in
each web worker. Never run multiple migration jobs concurrently.

The shipped configuration passes separate administrator and API passwords as
environment variables. `deploy/init-reader.sh` creates `uranium_reader` on a
new database volume and grants SELECT on tables created by the migration owner.
The API cannot write data or run migrations; use `migrate` for operator imports.
Do not adopt an existing development volume: migrate/restore into a new
production database with this role setup. For a restored database, verify
SELECT grants on every restored table before switching traffic. Password
rotation requires an explicit database role update and container recreation;
changing environment variables alone does not rotate existing roles.
For automatic restart after a host reboot, containers retain that configuration
and `restart: unless-stopped` restarts them. Future Compose operations still need
both original passwords exported. Re-enter them from the password manager. No
persistent plaintext credentials file is required. Production uses local private
Docker-network PostgreSQL; for an external DB use verified TLS (`sslmode=verify-full`
with its CA), a dedicated role, and review network access before changing this design.

## Import, persist, then publish

Follow [the EIA guide](../data/eia.md) to download/preview tables and verify the
actual report metadata. For production, replace each `docker compose` in its
import commands with `docker compose -f compose.production.yaml` and use the
`migrate` service instead of `api` for imports (the API database role is read-only). Use an absolute
private directory at the **same path for every release**, such as
`/srv/uranium-private/eia`. Its owner must be UID/GID 10001 for the non-root importer.
Do not mount the raw directory into nginx/Caddy. Example after acquiring and
reviewing one official workbook (replace timestamps and report metadata):

```bash
sudo install -d -m 0700 -o 10001 -g 10001 /srv/uranium-private/eia
# Operator first places the reviewed input in this directory with UID 10001 read access.
docker compose -f compose.production.yaml run --rm --no-deps -T \
  -v /srv/uranium-private/eia:/data/raw/eia \
  migrate python -m app.ingestion.eia_contracting \
  /data/raw/eia/umartable8.xlsx --table 8 --report-year 2025 \
  --retrieved-at '2026-11-16T20:00:00Z' --publication-date 2026-08-13 \
  --raw-dir /data/raw/eia --write
```

The dates above are placeholders, not a claim about your download. Retain
checksum originals, retrieval times and vintage together. Repeat for Tables
7/9/10 using the guide's filenames. A second identical import must add/revise
zero facts. Review values, nulls, source links and report periods against the
official workbooks. Take a backup after acceptance.

```bash
docker compose -f compose.production.yaml up -d edge
curl --fail "https://$APP_DOMAIN/health"
curl --fail "https://$APP_DOMAIN/ready"
curl --fail "https://$APP_DOMAIN/api/v1/contracts/signings?scope=us"
```

Caddy obtains/renews certificates; DNS and public 80/443 must reach this VM.
Its persistent volumes retain TLS state. Do not test with someone else's domain.
Verify HTTP redirects to HTTPS, certificate hostname, security headers, chart
rendering/tooltips at desktop/mobile sizes, loading/error/empty states, accessible
tables, and visible mock notices. Confirm the API/docs and raw files are not
publicly served outside the intended nginx routes. Unknown SPA paths return the
app shell, not private files. Test from outside the VM that database/API ports
are closed. No authentication is provided: all routed reads are public.

## Monitoring and maintenance

Docker logs are bounded to three 10 MB files per service. API access logs are
disabled to avoid recording query strings; errors go to stderr. Do not share
unredacted DB/ingestion tracebacks, which can contain source row values or
connection details. No source credentials are needed. Set an external HTTPS
monitor for `/ready`; separately monitor EIA report dates/import status because
readiness does not check source freshness. Docker health status alone does not
restart an unhealthy-but-running process; alert and investigate it.

Use Lightsail CPU/network/status metrics and configure its supported alarms;
check free disk/memory and backup success on-host. Record an alert recipient
and response procedure before launch. Set log/backup retention and review costs
monthly. Rebuild patched images on a planned cadence, rerun CI and restore
checks, then release with a new tag. Avoid unattended major DB upgrades.

## Backups and restore drill

Daily, before migrations, and after accepted imports, capture a custom-format
PostgreSQL dump plus matching raw artifacts. Do not ingest during this capture.
Store backups with mode 0700/0600 and transfer encrypted copies off the VM to an
approved private backup location. Verify the transfer and retain at least seven
daily copies plus a pre-release copy. A VM snapshot alone is not a tested DB
backup and automatic snapshots disappear when the source instance is deleted.

```bash
umask 077
mkdir -p backups
backup_stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker compose -f compose.production.yaml exec -T db \
  pg_dump -U dashboard -d uranium -Fc > "backups/$backup_stamp.dump"
sudo tar -C /srv/uranium-private -czf "backups/$backup_stamp-raw.tar.gz" eia
docker compose -f compose.production.yaml exec -T db \
  pg_restore --list < "backups/$backup_stamp.dump" > /dev/null
```

A listed dump is not a restore test. Restore into a **new isolated database/VM**:
create `uranium_restore` with `createdb -U dashboard uranium_restore`, then pipe
the saved dump into `pg_restore -U dashboard -d uranium_restore --no-owner --exit-on-error`.
Use an isolated API with `DATABASE_URL` pointing to that database, restore raw
files at the original container mount path, verify migration revision,
observation/run counts, checksums, `/ready`, all four EIA endpoints and chart
samples. Record elapsed restore time. Never trial-restore over production.
Automate the approved backup procedure with a host timer only after deciding
its private destination, retention, credentials and failure alert; that remains
an operator release prerequisite rather than a pretend configured backup job.

## Release and rollback

Before updating, retain the previous source bundle, image IDs/tags, deployment
configuration and tested backup. Build under a **new** tag, run the explicit
migration command, then recreate API **and frontend** together (nginx resolves
the API container on startup):

```bash
docker compose -f compose.production.yaml up -d --force-recreate api frontend
```

Validate through HTTPS. To roll back code, restore the previous reviewed source
bundle/configuration, export its previous `RELEASE_TAG`, and run the same recreate
command without building. First confirm that code supports the current schema.
Do not blindly run `alembic downgrade`. Incompatible schema/data changes require
restoring the pre-release dump and raw artifacts into a new DB/VM, verifying it,
then switching traffic. Writes since that backup may be lost. The initial
migration is unchanged in this preparation.

## Teardown (future operator action)

1. Export/verify final off-host backups and retention; stop ingestion.
2. Stop services using `docker compose -f compose.production.yaml down` (no
   `--volumes`). This preserves on-host volumes, but deleting the VM destroys
   its local state; ensure off-host copies are usable first.
3. In the Lightsail console delete the intended instance after the retention
   decision. Automatic snapshots are removed with it; manually retained snapshots
   continue to incur storage charges.
4. Release unused static IPs, remove obsolete DNS records, and separately delete
   unwanted manual snapshots, disks and optional backup resources after retention.
5. Check billing/resource inventory in the selected region and any other region
   used. Revoking access or stopping containers alone does not stop AWS charges.
