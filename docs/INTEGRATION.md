# Integration notes

## Local runtime

`compose.yaml` is provider-neutral local orchestration. It starts PostgreSQL, MQTT, FastAPI, and Next.js with service health dependencies and conservative memory limits. The API migrates its database at container start; use a one-off migration job in a multi-replica deployment rather than relying on that local convenience.

The browser uses `NEXT_PUBLIC_API_BASE_URL` at build time. For Docker Compose it defaults to `http://localhost:8000`; for host-side web development, set the same value in `apps/web/.env.local` or the shell. The API permits the configured `CORS_ORIGINS` only, with no credentialed cross-origin requests.

## Web/API adapter

The web API client now consumes the platform's public endpoints:

| Web need | Platform endpoint | Adapter behavior |
| --- | --- | --- |
| Operations briefing | `GET /operations/briefing?site_id=sonoran-west` | Returns a transparent, stored-observation read model: replay boundary, count/window, production-record throughput series, clean-record median baseline, quality-flag counts, and per-asset observation/incident facts. It explicitly omits availability, plan, confidence, and causal diagnosis. |
| Incidents and lifecycle | `GET /incidents`, `GET /incidents/{id}`, `POST /incidents/{id}/transitions` | Converts snake_case/list envelopes, maps `to_status`, and receives expanded linked findings plus their source observations for incident detail. The public deployment renders lifecycle actions read-only. |
| Asset context | `GET /operations/briefing` | Renders per-asset observation counts, flagged-record counts, latest observation time, and active-incident counts from briefing facts. The public UI does not present derived health or availability. |
| Overview/data trust | `GET /operations/briefing`, `GET /incidents` | Uses database-derived counts, a defined production series/baseline, and explicit quality-flag totals. It must render unavailable values as unavailable rather than invent a score or fallback number. |

The briefing endpoint and expanded incident detail resolve the previous presentation gaps: production is a returned `production_record.attributes.throughput_tph` series with a documented clean-record median baseline; asset context comes from stored observation and incident facts; and incident detail returns linked findings and linked observations. The API deliberately still does **not** provide operational availability, planned production, model confidence, financial exposure, or a causal diagnosis. The web client must omit or mark those values unavailable—not convert absence into `0`, `100%`, or a confident conclusion.

`/operations/summary` and `/data-trust` remain UI routes, not backend endpoints. Their visible claims are supported by `/operations/briefing` and the normal read APIs. The briefing is calculated only from stored public observation/incident rows and cannot access simulator-private state. The public interface and its guided evidence path are specified in [RECRUITER_JOURNEY.md](RECRUITER_JOURNEY.md).

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
