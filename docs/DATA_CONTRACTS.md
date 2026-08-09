# Data contracts

## Contract rules

`packages/contracts` is the shared, platform-visible contract boundary. Initial schemas should be authored in a language-neutral form (JSON Schema/OpenAPI) and generated or mirrored for TypeScript and Python. Any producer or consumer change begins with a compatible contract update and fixture update.

All identifiers are strings. All timestamps are ISO-8601 UTC timestamps with a `Z` suffix. All JSON object fields use `snake_case` on the API; the web client may map them at its boundary. Unknown optional fields must be ignored by consumers during the same major version.

### Visibility classification

| Classification | May appear in platform contracts? | Examples |
| --- | --- | --- |
| `observed` | Yes | sensor reading, file row, lab result, source timestamp |
| `platform_derived` | Yes | quality flag, finding rationale, incident state |
| `scenario_private` | No | fault ground truth, seed, scenario schedule, expected answer |
| `evaluation_only` | No | precision/recall labels, scoring annotations |

Any field that could disclose the underlying generated scenario is `scenario_private` unless explicitly demonstrated otherwise. It belongs in simulator-private schema/storage, not `packages/contracts`.

## Envelope: observed inputs

`POST /api/v1/ingestion/observations` accepts a batch of the following envelope. It represents what the platform can know, not why the simulator emitted it.

```json
{
  "contract_version": "1.0",
  "source": {
    "source_id": "telemetry-crusher-01",
    "source_type": "telemetry",
    "received_via": "api"
  },
  "observations": [
    {
      "idempotency_key": "source-event-uuid",
      "observed_at": "2026-08-08T18:42:00Z",
      "asset_ref": {
        "site_id": "sonoran-west",
        "asset_id": "primary-crusher-01"
      },
      "kind": "telemetry",
      "metric": "motor_current_amps",
      "value": 327.4,
      "unit": "A",
      "source_recorded_at": "2026-08-08T18:42:00Z",
      "attributes": {
        "sample_interval_seconds": 60
      }
    }
  ]
}
```

Required observation fields: `idempotency_key`, `observed_at`, `asset_ref.site_id`, `kind`, and `source_recorded_at`. `metric`, `value`, and `unit` are required for `telemetry`; file/API records use a documented `record_type` and typed payload schema instead. `attributes` may hold source context but must not carry hidden truth.

Accepted source types are `telemetry`, `file`, and `external_api`. Accepted kinds begin with `telemetry`, `production_record`, `quality_result`, `maintenance_record`, `dispatch_record`, and `environmental_observation`. Adding a kind requires an explicit typed payload definition—not an unbounded client convention.

### Initial telemetry units

The initial platform and simulator contract uses these canonical metric/unit pairs: `motor_current_amps` → `A`, `throughput_tph` → `t/h`, `vibration_mm_s` → `mm/s`, `bearing_temperature_c` → `C`, and `belt_speed_mps` → `m/s`. Producers must publish `belt_speed_mps` in metres per second as `m/s`; alternative spellings or converted values are flagged rather than silently normalized.

## Normalized platform records

The API assigns `observation_id`, `ingested_at`, and `quality_status`; it preserves `source_recorded_at` and `observed_at` without replacing them. Normalized records may reference an immutable raw payload record using `raw_payload_ref`.

```json
{
  "observation_id": "obs_01J...",
  "idempotency_key": "source-event-uuid",
  "observed_at": "2026-08-08T18:42:00Z",
  "ingested_at": "2026-08-08T18:42:03Z",
  "quality_status": "accepted_with_flags",
  "quality_flags": ["late_arrival"],
  "raw_payload_ref": "raw_01J..."
}
```

Quality flags may include `missing_value`, `invalid_unit`, `out_of_range`, `late_arrival`, `duplicate`, `out_of_order`, `stale_source`, and `schema_mismatch`. Flags are evidence, not an instruction to discard data. The ingestion response returns accepted, duplicate, rejected, and flagged counts, with item-level validation errors where safe.

## Findings and data-quality results

Findings are immutable evaluations. Their current relevance is determined by links to incident state, not by editing the finding.

```json
{
  "finding_id": "fnd_01J...",
  "finding_type": "anomaly",
  "status": "active",
  "asset_ref": {"site_id": "sonoran-west", "asset_id": "primary-crusher-01"},
  "detector": {"name": "motor-current-deviation", "version": "1.0.0"},
  "evaluated_window": {"start_at": "2026-08-08T18:00:00Z", "end_at": "2026-08-08T18:42:00Z"},
  "severity": "warning",
  "rationale": "Motor current exceeded the rolling baseline by 18%.",
  "evidence": [{"observation_id": "obs_01J...", "role": "trigger"}],
  "data_quality_summary": {"status": "degraded", "flags": ["late_arrival"]}
}
```

`finding_type` is `anomaly` or `data_quality`; `severity` is `info`, `warning`, `critical`; and quality summary status is `good`, `degraded`, or `unusable`. A detector must expose enough values in `rationale` or structured evidence for an operator to understand why it fired. Ground-truth labels are forbidden.

## Incidents and transitions

An incident aggregates one or more findings and retains an append-only timeline.

```json
{
  "incident_id": "inc_01J...",
  "status": "open",
  "title": "Elevated motor current on primary crusher",
  "severity": "warning",
  "asset_refs": [{"site_id": "sonoran-west", "asset_id": "primary-crusher-01"}],
  "finding_ids": ["fnd_01J..."],
  "opened_at": "2026-08-08T18:42:03Z",
  "updated_at": "2026-08-08T18:42:03Z"
}
```

Transitions use `{ "to_status", "reason", "actor" }`, where `reason` is required for `dismissed`, `mitigated`, and `resolved`. Valid lifecycle transitions are formalized by the backend and enforced server-side; no client may set `status` directly. Timeline entries include server time, actor, prior/new status, reason, and evidence references.

## Query, errors, and compatibility

List endpoints use `limit` (default 50, maximum 200) and opaque `cursor`; stable response ordering must be documented. Time queries use inclusive `start_at` and exclusive `end_at`. Invalid input returns a standard error envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "One or more observations are invalid.",
    "details": [{"path": "observations[0].unit", "reason": "required"}],
    "request_id": "req_01J..."
  }
}
```

Additive optional fields and new enum values that consumers can safely ignore are minor-version changes. Renames, removals, changed semantics, or new required fields are breaking changes. All fixtures must include a positive, malformed, late/out-of-order, and duplicate case.
