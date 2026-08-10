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
    path /portfolio/sonoran-ops/api/v1/assistant/tools/* /portfolio/sonoran-ops/api/v1/assistant/chat
}
handle @sonoranAssistantApi {
    # The deterministic tool request is a small structured JSON object.
    request_body {
        max_size 64KB
    }
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
read models, the deterministic read-only assistant-tool POST, and the bounded
`/assistant/chat` POST. It returns `405` for ingestion, incident transitions,
unknown API paths, and all other API methods. Run seeding on the private
Compose network. The assistant request body is capped at 64 KB at the edge;
API-level input limits remain required as a second boundary. The chat route
returns `503` until the API has a server-only `OPENAI_API_KEY`; it must never
fall back to a browser key or another write-capable endpoint.

Stock Caddy has no built-in rate-limiting directive. Do not add an uninstalled
plugin directive to the live configuration. The API currently enforces a fixed
limit of **8 accepted chat requests per hour per client**, **2 concurrent chat
requests per API process**, and a **30 accepted-chat global daily cap per API
process**, returning `429` when any limit is reached. These fixed values are
not environment overrides; the process-local, in-memory windows reset on API
restart. Before broader exposure, add a shared API/gateway limiter with
`Retry-After`, verify trusted proxy/client identity handling, concurrency,
request-body rejection, upstream timeout, and a separate daily spend circuit.
The current deterministic tool route should also receive an API-level request
limit before it is promoted beyond the portfolio audience.

## Environment and validation

Copy `production.env.example` to a root-owned deployment environment file with mode `600`. Replace
the database password with a long URL-safe random value; characters requiring URL encoding must be
percent-encoded consistently in a PostgreSQL URL.

Render the configuration before building:

```bash
docker compose --env-file /secure/path/sonoran-production.env \
  -f compose.production.yaml config --quiet
```

The password expansion is fail-closed, so validation must fail if `POSTGRES_PASSWORD` is absent.
Use `--quiet`: a rendered Compose configuration can contain resolved secret
values and must not be copied into a terminal transcript, ticket, or chat.

### Required production environment names

The protected deployment environment file currently requires the following
values. `NEXT_PUBLIC_*` values are intentionally embedded in the browser build;
never place a secret in one.

| Variable | Required | Purpose |
| --- | --- | --- |
| `POSTGRES_DB` | Yes | Database name. |
| `POSTGRES_USER` | Yes | Database role. |
| `POSTGRES_PASSWORD` | Yes | Database secret; use a long URL-safe value and keep the file mode `600`. |
| `SONORAN_WEB_PORT` | Yes | Loopback-only host port for the web health check. |
| `SONORAN_API_PORT` | Yes | Loopback-only host port for the API health check. |
| `NEXT_PUBLIC_BASE_PATH` | Yes | Public portfolio mount path: `/portfolio/sonoran-ops`. |
| `NEXT_PUBLIC_API_BASE_URL` | Yes | Browser API prefix: `/portfolio/sonoran-ops`. |
| `NEXT_PUBLIC_READ_ONLY_MODE` | Yes | Public lifecycle-control gate; must be `true`. |
| `CORS_ORIGINS` | Yes | Public browser origin: `https://matthewflorek.com`. |
| `DEMO_SEED` | Seed job only | Deterministic synthetic replay seed. |
| `DEMO_MINUTES` | Seed job only | Simulated duration. |
| `DEMO_WALLCLOCK_SPAN_MINUTES` | Seed job only | Wall-clock compression span for the replay. |
| `OPENAI_API_KEY` | Evidence chat only | Server-only key used by the API service for `/assistant/chat`; omit it to keep chat disabled. |
| `OPENAI_MODEL` | Evidence chat only | Model identifier passed only by the API service; set explicitly to make a release reproducible. |
| `CHAT_SAFETY_SALT` | Yes | A unique random, server-only salt for the provider safety identifier. Production Compose fails closed when it is absent. |

The API now consumes `OPENAI_API_KEY` only for the bounded evidence-chat route.
For this deployment, the authorized server operator should reuse the existing
host secret by securely adding the variable name/value to Sonoran's protected,
root-owned deployment environment file without printing, copying into the
repository, or placing it in a build argument. The value must never appear in
`NEXT_PUBLIC_*`, Compose output, logs, screenshots, or a committed file. See
[GOVERNED_AI_ANALYST.md](GOVERNED_AI_ANALYST.md) for the control boundary.

Generate `CHAT_SAFETY_SALT` with a cryptographically secure generator directly
into the root-owned deployment environment file (for example, a 32-byte random
value encoded as text). Do not echo the generated value, paste it into shell
history, include it in a command line, or copy it into the repository. It is a
separate secret from `OPENAI_API_KEY`; rotate either by securely replacing the
protected value and recreating the API service.

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
