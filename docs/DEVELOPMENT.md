# Development workflow

## Prerequisites

- Node.js 20+ and pnpm 9+
- Python 3.12+
- Docker Desktop (or compatible Compose runtime)

Copy `.env.example` to `.env`; `.env` is local-only. For a complete local runtime, use `npm run demo:up`; it starts PostgreSQL, MQTT, the API, and the web app. The API entrypoint applies Alembic migrations before it starts.

For host-side work, create and activate `.venv`, then run `npm run install`. This installs the API from `services/api/pyproject.toml` and web dependencies from `apps/web/package-lock.json`. Do not install project dependencies globally.

## Commands

| Command | Purpose |
| --- | --- |
| `npm run demo:up` / `npm run demo:down` | Start or stop the complete containerized local stack |
| `npm run compose:config` | Render and validate Compose configuration without starting services |
| `npm run test` | API/contract tests and web tests |
| `npm run lint` | Ruff API checks and web linting |
| `npm run typecheck` | Web TypeScript validation |
| `npm run build` | API bytecode compilation and production web build |
| `npm run migrate` | Apply Alembic migrations to `DATABASE_URL` |

The GitHub Actions workflow runs contract/API checks, web lint/typecheck/test/build, and `docker compose config` on pushes and pull requests.

## Working agreements

1. Read the architecture and data contracts before adding a feature.
2. Keep a change within one owned area whenever possible. Cross-boundary changes begin in `packages/contracts` and require a coordinated review.
3. Do not import `simulator` from platform code or make platform code aware of scenario truth.
4. Keep migrations portable to PostgreSQL 16 unless an optional Timescale optimization and fallback are documented.
5. Add tests and contract fixtures alongside behavior, including poor-data behavior—not just happy paths.
6. Never commit `.env`, database volumes/dumps, evaluator runs, or generated secrets.

## Area ownership and handoffs

| Area | Primary owner | Contract with other areas |
| --- | --- | --- |
| `apps/web` | Frontend | Consumes only published API/client types; proposes UI-driven API needs through contracts |
| `services/api` | Backend | Implements API/OpenAPI, persistence, detection, quality, and incidents; does not consume private simulator state |
| `packages/contracts` | Backend + frontend reviewers | Source of public schema truth; changes are additive by default and versioned |
| `simulator` | Simulator/evaluation | Emits only public observations via API/files; owns private truth separately |
| `evaluation` | Simulator/evaluation | Reads private truth and public platform outputs only for scoring |
| `infra` | Platform/infrastructure | Owns Compose, container, and database runtime assets |

To avoid collisions, do not place implementation code in another area's directory. If a change needs both a schema and implementation, land the schema/fixture first or coordinate a single small cross-area change. Do not reformat or reorganize unrelated files.

## Suggested implementation order

1. Define concrete schemas and fixtures in `packages/contracts`.
2. Add API validation, idempotent ingestion, and migrations in `services/api`.
3. Add simulator adapters that publish only those schemas.
4. Add normalized query/detection/incident behavior plus API tests.
5. Build the web read and transition workflows against the documented API.
6. Add evaluation scoring isolated from platform runtime.

## Quality gates

- Web: formatting, linting, type checking, component/integration tests.
- API: formatting/linting, typing, unit/integration tests against PostgreSQL, OpenAPI/schema validation.
- Contracts: schema compatibility checks and fixture validation in both TypeScript and Python.
- Simulator/evaluation: deterministic seed support, contract conformance, and proof that private truth is not present in published payloads.

Run the root commands above before handing work across an area boundary. API tests use SQLite only as a unit-test fallback; migrations and the local runtime target PostgreSQL.
