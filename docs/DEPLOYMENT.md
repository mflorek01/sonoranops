# Production deployment

This runbook deploys the synthetic Sonoran Operations Intelligence demo at
`https://matthewflorek.com/portfolio/sonoran-ops`. It uses the standalone
`compose.production.yaml`; the existing `compose.yaml` remains local-development orchestration.

## Prerequisites

The production build sets `NEXT_PUBLIC_BASE_PATH=/portfolio/sonoran-ops`, embeds the matching API
base, and enables `NEXT_PUBLIC_READ_ONLY_MODE=true`. The public portfolio therefore renders
lifecycle controls as read-only and does not depend on public mutation access.

The host must also have enough Docker disk headroom for build layers, the database, backups, and a
known-good rollback image. Do not build on a nearly full root filesystem.

## One-time edge setup

Create the external network and connect the existing shared Caddy container:

```bash
docker network create sonoran_edge
docker network connect sonoran_edge metamorphysis-caddy
```

The Compose services join that network with stable aliases `sonoran-api` and `sonoran-web`.
Loopback ports `3212` and `3211` remain available for operator checks; they are not public
listeners.

Add the exact API allowlist before the web route in the existing Caddy site. Preserve the prefix for
Next and strip it only for allowed FastAPI requests:

```caddyfile
@sonoranReadApi {
    method GET
    path /portfolio/sonoran-ops/api/v1/health /portfolio/sonoran-ops/api/v1/operations* /portfolio/sonoran-ops/api/v1/assets* /portfolio/sonoran-ops/api/v1/observations* /portfolio/sonoran-ops/api/v1/findings* /portfolio/sonoran-ops/api/v1/incidents*
}
handle @sonoranReadApi {
    uri strip_prefix /portfolio/sonoran-ops
    reverse_proxy sonoran-api:8000
}

@sonoranAssistantApi {
    method POST
    path /portfolio/sonoran-ops/api/v1/assistant/tools/*
}
handle @sonoranAssistantApi {
    uri strip_prefix /portfolio/sonoran-ops
    reverse_proxy sonoran-api:8000
}

@sonoranDeniedApi path /portfolio/sonoran-ops/api/*
handle @sonoranDeniedApi {
    respond "Method Not Allowed" 405
}

@sonoranWeb path /portfolio/sonoran-ops /portfolio/sonoran-ops/*
handle @sonoranWeb {
    reverse_proxy sonoran-web:3000
}
```

Validate the complete Caddy configuration before reload. This policy exposes only the listed GET
read models and the deterministic read-only assistant tool POST. It returns `405` for ingestion,
incident transitions, unknown API paths, and all other API methods. Run seeding on the private
Compose network. The assistant path still needs request-size and rate limits.

## Environment and validation

Copy `production.env.example` to a root-owned deployment environment file with mode `600`. Replace
the database password with a long URL-safe random value; characters requiring URL encoding must be
percent-encoded consistently in a PostgreSQL URL.

Render the configuration before building:

```bash
docker compose --env-file /secure/path/sonoran-production.env \
  -f compose.production.yaml config
```

The password expansion is fail-closed, so validation must fail if `POSTGRES_PASSWORD` is absent.

## Build, migrate, and start

```bash
docker compose --env-file /secure/path/sonoran-production.env \
  -f compose.production.yaml build

docker compose --env-file /secure/path/sonoran-production.env \
  -f compose.production.yaml up -d db api web
```

`api` depends on the one-off `migrate` service completing successfully. The API command itself runs
only Uvicorn, so replicas cannot race an embedded migration command. `AUTO_CREATE_SCHEMA` remains
disabled. Record the migration output and deployed image identities before cutover.

## Opt-in demo seed

Seeding is never part of normal startup. After API health is green, run:

```bash
docker compose --env-file /secure/path/sonoran-production.env \
  -f compose.production.yaml --profile seed run --rm seed
```

The job compresses deterministic simulation steps into a recent four-minute wall-clock span and
posts only public contract batches to `http://api:8000`. Its stable per-batch idempotency headers
make transport retries safe. Evaluator-private truth is written under `/tmp` inside the disposable
job and is neither mounted nor published. Re-running the same seed intentionally exercises
duplicate handling; do not treat it as a database reset.

## Verification

```bash
curl --fail http://127.0.0.1:3212/api/v1/health
curl --fail http://127.0.0.1:3211/portfolio/sonoran-ops
curl --fail https://matthewflorek.com/portfolio/sonoran-ops/api/v1/health
curl --fail https://matthewflorek.com/portfolio/sonoran-ops
docker compose --env-file /secure/path/sonoran-production.env \
  -f compose.production.yaml ps
```

Verify that PostgreSQL, MQTT, port 8000, and port 3000 are not public host listeners. Only Caddy
should publish ports 80/443. Review capped container logs for migration errors, health restarts, or
private-field leakage.

## Backup and rollback

Create and verify a PostgreSQL custom-format backup before every schema or application change.
Keep the previous immutable API/web images until the observation window completes. Application
rollback and database restore are separate decisions: Alembic migrations are forward operations,
and `docker compose down` must never be run with `--volumes` against production.
