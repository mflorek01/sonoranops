# Sonoran Operations Intelligence

Sonoran Operations Intelligence is a public, portfolio-grade operations-data
application for a **synthetic** aggregate and materials operation. It turns
published simulation observations into traceable data-quality findings,
incidents, evidence, and a bounded investigation experience.

**Live demo:** [matthewflorek.com/portfolio/sonoran-ops](https://matthewflorek.com/portfolio/sonoran-ops)

**Repository:** [github.com/mflorek01/sonoranops](https://github.com/mflorek01/sonoranops)

The demo is read-only, uses no customer or Granite data, and makes no claim of
plant control, safety certification, autonomous action, or mechanical root
cause. It is intended to show the application and data-product decisions that
would be needed for an asset-intensive operations use case.

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
| `docs` | Architecture, data contracts, recruiter journey, deployment, and developer workflow |
| `evaluation` | Evaluation harnesses and non-production run outputs |

## Run locally

Prerequisites: Docker Desktop with Compose, Node.js 20+ with npm, and Python 3.12+ for host-side development.

1. Read the [implementation plan](docs/IMPLEMENTATION_PLAN.md), [recruiter journey and authenticity standard](docs/RECRUITER_JOURNEY.md), [visual analytics definitions](docs/VISUAL_ANALYTICS.md), [architecture](docs/ARCHITECTURE.md), [data contracts](docs/DATA_CONTRACTS.md), and [development guide](docs/DEVELOPMENT.md). The isolated public-server workflow is in the [production deployment runbook](docs/DEPLOYMENT.md).
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

See [Integration notes](docs/INTEGRATION.md) for the live web/API adapter and
its deliberately limited derived UI fields. The public demonstration journey
and its evidence-first UX acceptance criteria live in
[docs/RECRUITER_JOURNEY.md](docs/RECRUITER_JOURNEY.md).

## Current status

The working demo includes contract validation, idempotent ingestion,
data-quality findings, incident lifecycle APIs, a typed web adapter, database
migrations, containerized local and public runtimes, a seeded synthetic replay,
a database-derived operations briefing, and deterministic, cited, read-only
evidence tools. The simulator publishes only public observations to the
platform; private scenario truth is retained for evaluation and is not
available to application code.

The evidence-first recruiter walkthrough is implemented and current. It guides
free exploration from the operating story to incident evidence and data-quality
context, while replacing decorative or invented presentation values with
traceable public data. Its product decisions and acceptance criteria are in
[RECRUITER_JOURNEY.md](docs/RECRUITER_JOURNEY.md).

The dashboard's observed/derived/unknown boundaries are defined in
[VISUAL_ANALYTICS.md](docs/VISUAL_ANALYTICS.md). The public evidence explorer
is deterministic. An optional server-side, read-only evidence-chat route uses
the same bounded tools when configured with a protected `OPENAI_API_KEY`; the
remaining production-hardening controls are documented in
[GOVERNED_AI_ANALYST.md](docs/GOVERNED_AI_ANALYST.md).

Still out of scope for this portfolio release: real customer connectors and
data, authentication/SSO and enterprise RBAC, production availability
calculations, managed operational infrastructure, and production assistant
governance such as audit retention, identity binding, budget control, and rate
limiting.
