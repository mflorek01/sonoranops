# Sonoran Operations Intelligence

Sonoran Operations Intelligence is a portfolio-grade industrial intelligence platform for a **synthetic** aggregate and materials operation. It turns simulated operating signals into traceable production, equipment-health, quality, and incident workflows.

The application is intentionally split into two systems:

- **Synthetic plant / scenario generator** creates inputs and holds hidden scenario truth used only for evaluation.
- **Operations platform** ingests only published observations and makes decisions from those observations, exactly as a real industrial platform would.

The platform must never read generator state, scenario schedules, fault labels, or expected answers.

## Repository map

| Path | Responsibility |
| --- | --- |
| `apps/web` | Next.js/TypeScript operator-facing UI |
| `services/api` | FastAPI ingestion, query, incidents, and assistant-facing APIs |
| `packages/contracts` | Versioned, platform-safe shared API/event schemas and generated clients |
| `simulator` | Synthetic plant generator, fixtures, and evaluation-only truth |
| `infra` | Docker, database, and deployment assets |
| `docs` | Architecture, data contracts, and developer workflow |
| `evaluation` | Evaluation harnesses and non-production run outputs |

## Run locally

Prerequisites: Docker Desktop with Compose, Node.js 20+ with npm, and Python 3.12+ for host-side development.

1. Read the [implementation plan](docs/IMPLEMENTATION_PLAN.md), [architecture](docs/ARCHITECTURE.md), [data contracts](docs/DATA_CONTRACTS.md), and [development guide](docs/DEVELOPMENT.md).
2. Copy `.env.example` to `.env` and replace the development database password if desired.
3. Start the complete local stack with `npm run demo:up`.
4. Open `http://localhost:3000`. The API health check is at `http://localhost:8000/api/v1/health`.
5. Stop it with `npm run demo:down`.

Compose starts PostgreSQL 16, an MQTT broker, the FastAPI service, and the Next.js UI. The API container applies Alembic migrations before accepting traffic. MQTT is provisioned as a local transport endpoint; no platform service currently consumes hidden simulator data from it.

The database migration path is PostgreSQL-compatible. Timescale features remain optional optimizations and must retain a PostgreSQL fallback.

## Common commands

Create and activate a repository-local Python virtual environment before host-side API commands. On PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
npm run install
npm run test
npm run lint
npm run build
npm run migrate
```

`npm run install` installs web dependencies from its committed lockfile and API dependencies from `services/api/pyproject.toml`. `npm run migrate` uses `DATABASE_URL` from `.env` (or the active shell).

See [Integration notes](docs/INTEGRATION.md) for the live web/API adapter and its deliberately limited derived UI fields.

## Current status

The first platform slice is available: public contract validation, idempotent ingestion, data-quality findings, incident lifecycle APIs, a typed web adapter, database migrations, and a containerized local runtime. The synthetic simulator/evaluation system, authentication, external source adapters, production availability calculations, and the read-only assistant remain future work.
