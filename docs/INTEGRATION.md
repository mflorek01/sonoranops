# Integration notes

## Local runtime

`compose.yaml` is provider-neutral local orchestration. It starts PostgreSQL, MQTT, FastAPI, and Next.js with service health dependencies and conservative memory limits. The API migrates its database at container start; use a one-off migration job in a multi-replica deployment rather than relying on that local convenience.

The browser uses `NEXT_PUBLIC_API_BASE_URL` at build time. For Docker Compose it defaults to `http://localhost:8000`; for host-side web development, set the same value in `apps/web/.env.local` or the shell. The API permits the configured `CORS_ORIGINS` only, with no credentialed cross-origin requests.

## Web/API adapter

The web API client now consumes the platform's public endpoints:

| Web need | Platform endpoint | Adapter behavior |
| --- | --- | --- |
| Incidents and lifecycle | `GET /incidents`, `GET /incidents/{id}`, `POST /incidents/{id}/transitions` | Converts snake_case/list envelopes, maps `to_status`, adds an idempotency key and `operator:web` actor |
| Assets | `GET /assets`, `GET /observations` | Derives display name, last observed time, and data-quality health from observed records |
| Overview/data trust | `GET /observations`, `GET /incidents` | Derives visible counts and quality score only from platform-visible observations |

The adapter intentionally does **not** invent plant truth. Several presentation fields have no platform equivalent yet: asset availability is observation presence (100 or 0), production delta is `0`, incident confidence is `0`, and incident evidence cards are empty because the incident detail API currently returns finding IDs/timeline, not expanded finding evidence. The UI also exposes lifecycle choices that may be rejected by the API's valid-transition rules. These are known product/API expansion items, not simulator fallbacks.

`/operations/summary` and `/data-trust` are not backend endpoints; the browser derives their displayed values through public read APIs. Any later server-side aggregate must preserve those provenance rules and must not access simulator-private state.

## Current detector boundary

The platform currently creates two bounded, explainable finding classes from public observations: a telemetry-deviation rule (a reading differs by at least 25% from the mean of three to five preceding readings for the same asset/metric) and a multi-source freshness rule (two or more source clocks are stale while another source remains current). These findings state a deviation or data-system classification only; they do not assert mechanical root cause, screen restriction, or simulator scenario truth.

## Deterministic evidence-tool mode (synthetic demo)

`POST /api/v1/assistant/tools/{tool_name}` exposes a narrowly allowlisted, provider-neutral retrieval surface for the demo. It calls no LLM, executes no raw SQL, and performs no state mutation. The request body is:

```json
{
  "site_id": "sonoran-west",
  "arguments": { "asset_id": "primary-crusher-01", "limit": 20 }
}
```

`site_id` is required and is enforced inside each retrieval query. Results and citations for incidents, findings, and observations outside that site are not returned. The current allowlist is `list_recent_incidents`, `get_incident_evidence`, `query_observations`, `list_recent_findings`, and `compare_observation_periods`; each retains its existing input validation, bounded windows, result limits, citations, uncertainty notes, and `truncated` flag. Arguments must be a JSON object for the selected tool—there is no raw query or registry-inspection mode. The response is:

```json
{
  "mode": "deterministic_evidence_tool",
  "tool_name": "query_observations",
  "site_id": "sonoran-west",
  "records": [],
  "citations": [],
  "uncertainty_notes": [],
  "truncated": false
}
```

This is demo-safe evidence retrieval, not a production assistant integration. Authentication, authorization, tenant binding, audit logging, rate limiting, and production retention controls remain future hardening work.
