# Sonoran Operations Intelligence

## Technical Implementation Plan — Portfolio MVP and Production Path

**Status:** active repository implementation plan. Foundation, first platform slice, and local runtime are complete; remaining sections guide active delivery.
**Primary demonstration:** a general, evidence-led operations intelligence app for a fictional Arizona aggregate/materials production facility.
**Core operator question:** *Production is below plan. Is the likely contributor equipment degradation, bad instrumentation, a process restriction, planned activity, or a data-system failure—and what should the operator investigate next?*

## 1. Executive intent and hiring story

Sonoran Operations Intelligence helps plant operations teams turn noisy equipment telemetry, process events, production records, dispatch/order signals, and operator evidence into a defensible operational picture. It makes the next investigation clear without pretending to know more than the data supports.

The first implementation is deliberately a portfolio MVP: it demonstrates real product engineering, not a static dashboard or a scripted AI demo. A fictional Arizona aggregate/materials plant supplies a concrete domain—primary and secondary crushers, screens, feeders, conveyors, stackers, motors, stockpiles, and dispatch—while the platform stays scenario-driven and applicable to other asset-intensive operations.

The hiring story is that a small team can deliver an unusually credible vertical slice:

- A usable application with ingestion, canonical data, transparent analytics, incidents, evidence, and a bounded assistant.
- A flagship incident that comes from ordinary seeded records and common product logic—not from special UI or code paths.
- Explicit uncertainty, source/data quality, and auditability at every decision point.
- Reproducible demonstrations, tests, and written tradeoffs that show the system can become a real deployment rather than being discarded after a presentation.

### Product claim

For connected production operations with defined data inputs, Sonoran can normalize telemetry and business/process events, identify unusual or missing conditions, organize related facts into an incident, estimate production/order exposure, and help an authorized person investigate through source-cited answers.

### Claims we will not make

- No autonomous plant control, PLC/SCADA commands, safety certification, regulatory certification, or guaranteed outage prevention.
- No asserted root cause from telemetry alone. The product distinguishes observation, hypothesis, and unknown.
- No medical-style certainty that a bearing, crusher, or process component is failing.
- No claim that a portfolio-scale synthetic dataset proves production anomaly accuracy.
- No unrestricted LLM database access, network access, or mutation capability.
- No hardcoded flagship result, scenario-specific detector setting, scenario-specific prose, or UI branch. The app must work from data and configuration for every scenario.

## 2. Scope, non-goals, and MVP boundary

### Portfolio MVP: build now

1. Next.js/TypeScript operator app with overview, incident, asset, data-health, and investigation views.
2. FastAPI/Python backend with a single demo organization and simple local roles.
3. PostgreSQL with partition-ready, time-series-compatible tables; Docker Compose local runtime.
4. Ingestion from MQTT simulation plus file and HTTP batch/single-event inputs.
5. A seeded Arizona aggregate plant model; deterministic scenario generator with randomized public seeds.
6. Transparent rolling statistics, threshold/rate-of-change rules, source-health detection, and deterministic correlation.
7. Incident/evidence lifecycle with human acknowledgement, finding, ownership, and closure note.
8. A read-only tool-calling assistant with server-enforced scope and citations.
9. Synthetic production plans, orders/dispatch, stockpiles, and haul-distance context for commercial impact.

### Later production-hardening: design for it, do not block MVP on it

- OIDC integration, multi-tenant deployment isolation, full RBAC/SSO administration, and enterprise audit retention.
- Managed broker/queue, object storage for raw payloads and files, durable worker orchestration, HA/DR, backup/restore rehearsal, and production on-call.
- Full connector framework, data catalog, ticketing/CMMS integration, notification delivery, and export governance.
- 1M+ point load suite, formal SLOs, penetration test, model governance, and change-management approval workflows.
- Optional Isolation Forest after baseline methods have been evaluated; no ML work delays the core MVP.

### Explicit MVP non-goals

- No physical-actuation or write-back workflow.
- No full MES, SCADA, historian, ERP, CMMS, or dispatch-system replacement.
- No generic AI copilot that can take action or answer without retrieved evidence.
- No native mobile/offline field application.
- No assertion that synthetic commercial impact equals financial loss in a live business.

### MVP assumptions to validate

- Inputs can identify a source, time, asset or external key, metric/event kind, value/payload, and unit where relevant.
- A 1–5 minute data-to-screen latency is sufficient for the portfolio MVP; it is not a control-room real-time promise.
- Demo data is wholly synthetic and contains no customer, employee, dispatch, or site-sensitive information.
- The MVP uses one fictional organization; identity is local/demo-only. Every model/query still carries `organization_id` so a tenant boundary can be added without redesign.

## 3. Product principles

1. **Evidence before eloquence.** Every alert and answer exposes source facts, time windows, detector/version, and quality caveats.
2. **Humans decide.** The product prioritizes and explains; authorized operators acknowledge, investigate, and close.
3. **General logic, seeded scenarios.** The scenario generator changes data—not application behavior.
4. **Uncertainty is useful output.** “Evidence is insufficient” and “data system is degraded” are valid, visible results.
5. **Traceability is a feature.** Any card, chart annotation, or assistant citation links to evidence and provenance.
6. **Statistics first.** Robust, inspectable rules are the default. ML is optional, versioned, and cannot be the sole basis for an important MVP conclusion.
7. **Commercial context without false precision.** Production-plan, stockpile, dispatch, and order exposure are labeled estimates based on synthetic assumptions.

## 4. Users and critical workflows

| Persona | Goal | Critical workflow | MVP success signal |
|---|---|---|---|
| Shift supervisor | Keep production on plan and focus the crew | Review below-plan queue → compare impact/evidence → assign or acknowledge | Can explain the top issue and next check in under two minutes |
| Control-room/field operator | Investigate a developing production problem | Open incident → inspect timeline/charts/source health → add finding → hand off | Can create an evidence-backed shift handoff without guessing |
| Reliability/process engineer | Separate equipment, instrumentation, and process explanations | Compare equipment trends/baselines → inspect related signals → record hypothesis | Can see why a signal was flagged and what contradicts it |
| Production/dispatch planner | Understand order risk and mitigation options | Inspect plan vs actual, stockpile buffer, dispatch schedule, orders at risk | Can distinguish a plant concern from a customer/service exposure |
| Integration/data owner | Keep operational data trustworthy | Check source freshness/rejects → inspect quarantined payload → correct/replay | Can find invalid, duplicate, late, or mismapped data safely |
| Portfolio evaluator | Verify the system is real and repeatable | Start stack → select/reset a randomized seed → follow incident/evidence path | Can prove the flagship is a general-app outcome |

### Core workflow: below-plan investigation

1. A plan/actual calculation indicates the plant or product stream is below its shift target, or a relevant product output trend falls outside the expected band.
2. The overview shows the impact and any active incident, including data-quality state.
3. The supervisor opens the incident and compares secondary-crusher vibration, bearing temperature, power-per-ton, throughput, screen/product output, equipment events, planned work, and source freshness.
4. The system surfaces possible contributors—not a root cause—and marks competing explanations: degradation signal, instrument issue, process restriction, planned activity, or data-system failure.
5. The operator uses cited assistant questions or direct drill-down to decide the next human check, records a finding, assigns ownership, and hands off or resolves with a reason.

## 5. Flagship demo and scenario catalog

### Flagship: Secondary crusher degradation investigation

The fictional facility is **Sonoran Ridge Aggregates**, an Arizona materials production site producing specified aggregate products from a primary crusher through secondary crushing, screens, conveyors, stackers, and stockpiles.

During a shift, production is below plan. On the secondary crusher train, vibration, bearing temperature, and power-per-ton progressively rise while throughput and a relevant finished-product output fall. An order/dispatch horizon exposes a small set of synthetic orders at risk if the trend persists, moderated by available stockpile buffer and haul-distance assumptions. At the same time, one relevant telemetry feed has intermittent delay/quality degradation, leaving a credible data-system or instrumentation alternative.

Expected product behavior:

1. Show below-plan production and a priority incident; do **not** assert “crusher failure.”
2. Correlate transparent evidence: rising vibration/temperature/power-per-ton, falling throughput/product output, and any relevant event/quality facts.
3. Show data-quality ambiguity explicitly. A caveat must be visible before or beside the conclusion—not buried in raw data.
4. Present a structured set of plausible investigative categories: equipment degradation, bad instrumentation, process restriction, planned activity, data-system failure, and insufficient evidence.
5. Let the assistant answer “What changed?”, “What evidence supports it?”, “What might contradict it?”, and “What should we inspect next?” with citations and uncertainty.
6. Allow a human to acknowledge, assign, add “inspect secondary crusher bearing/vibration instrumentation and check screen restriction,” and hand off. Resolution requires a human-provided reason.

### Demo invariants

- The flagship uses normal `Asset`, `MetricDefinition`, `TelemetryObservation`, `OperationalEvent`, `ProductionPlan`, `Order`, `Alert`, `Incident`, and `EvidenceItem` records.
- A scenario seed controls timing offsets, trend slopes, noise, product/order numbers, source delay, and fictional naming. It writes a **public** scenario manifest plus a **private CI evaluator** manifest.
- Runtime code must never branch on a scenario name or seed to choose detector thresholds, result wording, priority, assistant content, or UI behavior.
- Acceptance tests assert invariant relationships and tolerance windows rather than exact timestamps or LLM wording.
- A local/demo scenario selector/reset is clearly labeled and disabled outside demo configuration.

### Randomized scenario catalog

| ID | Scenario | Public data pattern | Required behavior |
|---|---|---|---|
| S01 | Secondary crusher degradation (flagship) | Vibration/temp/power-per-ton rise; throughput/product output fall; intermittent quality ambiguity; plan/order impact | Correlated priority incident, evidence and caveat; no root-cause assertion |
| S02 | Normal production variation | Expected shifts/noise within process bands | No misleading incident; overview remains explainable |
| S03 | Gradual degradation | Multi-window vibration/temp trend on a motor/crusher | Trend alert with baseline rationale and investigation prompt |
| S04 | Isolated spike | One high vibration/power point with immediate recovery | Record anomaly candidate; avoid escalation without corroboration |
| S05 | Sensor drift or freeze | Slowly offset value or unchanged value while peers vary | Instrumentation/data-quality hypothesis, not equipment conclusion |
| S06 | Site connectivity outage | Several sources stop or arrive late together | Data-system incident/health banner, separate from asset failure |
| S07 | Screen/process restriction | Screen load/recirculating load rise, downstream output falls while crusher signals remain normal | Process-restriction candidate with linked evidence |
| S08 | Planned maintenance | Scheduled crusher/screen maintenance and expected discontinuity | Suppress/downgrade matching candidates with retained reason |
| S09 | Duplicate/replayed input | Same source event ID/payload hash repeated | Idempotent receipt and no duplicate observation/alert |
| S10 | Late arrival/correction | Valid process data arrives out of order | Preserve provenance, recompute affected window, annotate late data |
| S11 | Unit or asset mismatch | kW/hp or external asset key maps incorrectly/ambiguously | Reject/quarantine; never silently convert/guess an asset |
| S12 | Schema drift | Source changes required field/type/version | Quarantine and source-health issue with mapping/schema reason |
| S13 | Demand/order risk | Output/stockpile/haul-distance combination threatens scheduled loads | Surface estimated orders at risk and assumptions, not financial certainty |

## 6. Functional requirements

### FR-1 — Local identity and future authorization boundary

- MVP supports local demo users (`viewer`, `operator`, `engineer`, `admin`) via a simple development identity configuration.
- API authorization is centralized; UI visibility is never the authorization mechanism.
- Store `organization_id` on all business records and require it in repository/service signatures, even though MVP exposes one organization.
- Audit MVP user state changes, detector/config edits, file uploads, and assistant tool invocations. Full OIDC/multi-tenant RBAC is a hardening milestone.

### FR-2 — Asset, process, and commercial registry

- Model assets: primary crusher, secondary crusher, screens, feeders, conveyors, stackers, motors, stockpiles, and product streams.
- Support tags, external identifiers, zone/train, asset class/status, and typed relationships such as `feeds`, `conveys_to`, `screens_for`, `powers`, and `stocks`.
- Model product specification, shift production plan, actual production aggregate, stockpile balance, dispatch/load, order, scheduled date, customer-region placeholder, and assumed haul distance.
- Link commercial exposure to sourced plant/output/stockpile facts and label any calculation as an estimate.

### FR-3 — Ingestion and source contracts

- MQTT adapter subscribes to configured simulated/device topics. File adapter accepts CSV/JSON batch upload; HTTP adapter supports batch and single-event JSON.
- Validate source identity, schema version, event timestamp, metric/event type, asset mapping, unit, numeric range, duplicate identity, organization scope, and payload size.
- Record immutable receipt/disposition: `accepted`, `duplicate`, `quarantined`, or `rejected`, with mapping/schema version and reason code.
- Use `(organization_id, source_id, source_event_id)` idempotency when supplied; otherwise use canonical payload fingerprint rules documented per adapter.
- Provide source health: last seen, freshness lag, valid/rejected/duplicate/quarantined counts, reason summaries, and mapping/schema version.

### FR-4 — Operational time series and events

- Persist numeric telemetry using both `observed_at` and `received_at`; query by asset/metric/range with bounded downsampling and baseline overlays.
- Persist events: maintenance windows, setpoint/process state, inspection notes, equipment status, production/dispatch updates, and source-health events.
- Preserve raw/source provenance references and quality flags. Never alter an accepted fact; corrections supersede it.

### FR-5 — Plan, production, stockpile, and order exposure

- Calculate plan versus actual by shift/product/production area using explicit time windows and source status.
- Calculate simple estimated at-risk orders using expected shortfall, available stockpile by product, dispatch cutoff, and configured/seeded haul-distance/service-time assumptions.
- Render the facts and formula inputs; state “estimated exposure” and missing assumptions. Do not invent revenue loss or customer impact.

### FR-6 — Detection, hypothesis cues, and correlation

- Run scheduled and on-demand evaluation on eligible telemetry windows.
- Implement rolling median/MAD robust z-score, threshold, rate-of-change, trend, freeze/staleness, and source-freshness rules. Version detector policy/configuration.
- Optionally compare an Isolation Forest score for multivariate groups after MVP; retain feature/model/training/version metadata and never use it as the sole high-priority rationale.
- Emit alert candidates with score, observed/expected values, baseline snapshot, detector/config version, quality state, and plain-language rule explanation.
- Correlate compatible alert candidates with asset/process topology, time overlap, product/plan impact, events, and quality state into incidents. Preserve every individual alert and correlation reason.
- Maintain **hypothesis cues**, not root causes. Policy may label evidence as consistent with equipment degradation, instrumentation/data issue, process restriction, planned activity, data-system failure, or insufficient evidence; it must also show evidence that limits the cue.

### FR-7 — Incident, evidence, and human decision lifecycle

- Incident states: `open`, `acknowledged`, `investigating`, `monitoring`, `resolved`, `closed`.
- Severity: `critical`, `high`, `medium`, `low`, `informational`; calculated suggestions can be overridden with a rationale.
- Support assignment, tags, findings, status transition, and closure/resolution category/note. Automated jobs may open/update evidence but cannot resolve/close.
- Evidence timeline includes observations/aggregates, anomaly evaluations, alerts, correlation facts, production/order calculations, events, source health, user findings, and assistant answers.
- Evidence captures are immutable snapshots/references with content/provenance/version metadata; corrections create a superseding link.

### FR-8 — Grounded assistant

- Provide an optional incident/asset/time-scoped chat panel to authorized local users.
- The assistant invokes only server-defined read-only tools. It cannot write incidents, send instructions to plant systems, browse external networks, or access raw SQL.
- Factual claims require a returned tool citation. If evidence is unavailable or degraded, say so plainly and give a next investigative step.
- Render citation label, source/object ID, time/range, quality state, and deep link. Store turn/prompt/tool/citation/safety metadata for MVP review.

### FR-9 — Operator information architecture

- **Overview:** production vs plan, relevant output/product stream, stockpile/order-risk summary, prioritized incidents, and source-health banner.
- **Incident detail:** status/owner, deterministic “what changed” summary, hypothesis cues/limits, timeline, charts, detector rationale, production/order exposure, activity log, and assistant panel.
- **Asset detail:** current trend, baseline, connected assets, related events/incidents, source health, and raw facts.
- **Data health:** sources, mapping/schema versions, freshness, rejection/quarantine samples, and authorized local replay controls.
- **Production/dispatch:** plan vs actual, stockpiles, scheduled dispatches/orders, haul-distance assumptions, and at-risk estimates.
- From any incident evidence item, reach its source/raw details within two interactions. All severity and quality colors carry textual labels.

## 7. Architecture and service responsibilities

```text
MQTT simulator / CSV-JSON upload / HTTP producer
                  │
                  ▼
      FastAPI ingestion adapters + validation/mapping
                  │                    │
                  ▼                    ▼
    PostgreSQL (partition-ready operational/time-series schema)  quarantine receipts
                  │
                  ├── evaluation/correlation worker
                  ├── source-health and plan-vs-actual calculator
                  └── FastAPI product API + assistant tool facade
                                      │
                                      ▼
                         Next.js TypeScript operator app
                                      │
                                      ▼
                         configured LLM provider (tools only)
```

### MVP technology decisions

- **Web:** Next.js App Router, TypeScript, accessible components, React Query/equivalent cache, time-series charts with zoom and annotations.
- **API/workers:** FastAPI, Pydantic, SQLAlchemy/Alembic, Python evaluation module, Compose worker process. Keep a job interface so a managed queue can replace it later.
- **Data:** PostgreSQL 16; monthly time partition design and indexes on `(organization_id, asset_id, metric_id, observed_at)`. Use native PostgreSQL in MVP; retain Timescale-compatible query/schema patterns rather than requiring an extension.
- **Transport:** Mosquitto in Docker Compose plus HTTP/file adapters.
- **Analytics:** NumPy/Pandas/scikit-learn; transparent rules first; optional Isolation Forest only as a later comparison.
- **Runtime:** Docker Compose for UI, API, worker, database, MQTT, and generator. `.env.example` contains non-secret defaults/placeholders.
- **Assistant:** tool-calling model behind a narrow server facade. The provider is configuration-driven and may be mocked for deterministic tests.

### Responsibility boundaries

| Component | Owns | Does not own |
|---|---|---|
| Web app | Presentation, navigation, client validation, user workflow | Authorization truth, direct DB access, detector policy |
| Product API | Commands, read models, local-role enforcement, audit events | Broker protocol, free-form LLM data access |
| Ingestion adapters | Protocol, mapping, validation, durable disposition | Incident severity/closure decisions |
| Data layer | Constraints, migrations, time partitions, immutable facts | Hidden business policy in DB triggers |
| Evaluation worker | Features, scores, alerts, source-health calculations | Human state transition or LLM conclusions |
| Correlation worker | Deterministic links and incident candidates | Deleting/silently merging evidence |
| Assistant facade | Tool schemas, policy, citations, transcript ledger | SQL generated by model, operational actions |

## 8. Canonical data model and source contract

All entities have UUID `id`, `organization_id`, and appropriate creation/provenance fields. Time is stored as UTC `timestamptz`; any source timezone is preserved in provenance.

| Entity | MVP fields and constraints |
|---|---|
| `Organization` | fictional organization; retained boundary for later tenant isolation |
| `Asset` | name, asset type, status, process area/train, external keys, tags |
| `AssetRelationship` | from/to asset, typed relationship, validity range |
| `MetricDefinition` | key, canonical unit, plausible bounds, sampling expectation, detector policy |
| `Source` | kind, schema/mapping version, freshness SLA, enabled/status |
| `TelemetryObservation` | source/event IDs, asset, metric, observed/received time, canonical numeric value/unit, quality flags, raw fingerprint |
| `OperationalEvent` | type, asset/process/product scope, occurrence time, structured attributes, source provenance |
| `IngestionReceipt` | raw reference/hash, disposition, reason, mapping/schema version |
| `ProductionPlan` / `ProductionActual` | shift/window, product/area, planned/actual tons or rate, source/version |
| `StockpileBalance` | product/stockpile, measured/estimated tons, timestamp, quality/source |
| `Order` / `Dispatch` | product, requested/scheduled time, quantity, dispatch state, modeled haul distance/service assumption |
| `EvaluationRun` / `AnomalyScore` | watermark/interval, detector/config/code/model versions, score/threshold/features/verdict |
| `Alert` | type, severity suggestion, dedupe key, time window, score reference, explanation/quality state |
| `Incident` / links | lifecycle, severity, owner, calculated impact, alert/evidence links with correlation rationale |
| `EvidenceItem` | immutable typed snapshot/reference, capture/source/version/hash, quality state, supersedes link |
| `Finding` / `AuditEvent` | human hypothesis/finding revisions; actor/action/object/before-after/correlation ID |
| `AssistantTurn` | scope, prompt/model version, tool ledger, citations, safety disposition, feedback |

### Canonical ingestion envelope

```json
{
  "schema_version": "1.0",
  "source_event_id": "sec-crusher-01:2026-08-08T12:00:00Z:vibration",
  "occurred_at": "2026-08-08T12:00:00Z",
  "asset_external_key": "SRC-SEC-01",
  "metric_key": "bearing_vibration_rms",
  "value": 7.2,
  "unit": "mm/s",
  "quality": "good",
  "attributes": {"sensor_channel": "drive_end"}
}
```

Adapters map native messages to this envelope through versioned mappings. Mapping changes require fixtures and recorded approval. An observation resolves to exactly one active asset/metric or is quarantined; it is never guessed.

## 9. Data quality and trust model

### Quality dimensions

- **Validity:** schema/type/unit/plausible-range checks pass.
- **Completeness:** expected metrics/sources exist in the evaluation window.
- **Freshness:** arrival age and last-seen age meet the source’s documented MVP expectation.
- **Uniqueness:** source ID/payload fingerprint is not replayed.
- **Consistency:** asset mapping, metric mapping, product/plan association, and unit conversion are unambiguous.
- **Integrity:** raw reference/hash plus mapping/transformation version are available.

### Trust states and product behavior

| State | Meaning | Behavior |
|---|---|---|
| `trusted` | Required quality checks/freshness pass | Eligible for normal scoring/correlation |
| `degraded` | Usable but late, incomplete, or flagged | May be used with visible caveat/reduced confidence |
| `untrusted` | Invalid, ambiguous, materially incomplete | Quarantine/context only; never sole basis for alert |
| `unknown` | Insufficient history/source state | Do not infer normality; state the gap |

Incident confidence is a policy cue based on evidence diversity, quality, baseline adequacy, and correlation strength. It is never presented as probability of equipment failure.

## 10. Incident lifecycle and evidence model

```text
alert candidate → open → acknowledged → investigating ↔ monitoring → resolved → closed
```

- Correlation opens an incident when documented criteria are met; otherwise alerts remain triageable.
- State changes require a permitted local role and meaningful rationale where applicable. `resolved` needs a category/note; `closed` needs owner confirmation or a documented MVP policy.
- Reopening preserves prior closure evidence. Automated jobs add facts/cues; they never close an incident.
- An incident retains calculated production/order impact with formula inputs and a “synthetic estimate” label.

An `EvidenceItem` captures type, source object/version, observation interval, capture time, detector/mapping version, machine-readable payload/reference, content hash, quality state, and rendering hint. Evidence types: telemetry point/range aggregate, anomaly evaluation, production/plan calculation, stockpile/order exposure, operational event, source-health fact, user finding, lifecycle record, and assistant answer/tool result.

## 11. Anomaly design, evaluation, and hidden ground truth

### Detection pipeline

1. Watermark observations by source with configured allowed lateness.
2. Build features: median, MAD, robust z-score, slope, rate of change, power-per-ton, freeze/staleness, rolling completeness, neighbor comparison, and source freshness.
3. Run transparent rule policies first and store the exact values/baseline/threshold/version.
4. After MVP, run optional Isolation Forest on configured multivariate groups; store feature schema, training interval, contamination, artifact/version, and comparison results.
5. Dedupe candidates into alerts and correlate via topology, signal family, timing, plan/product impact, maintenance events, and quality state.

### Hidden-ground-truth boundary

- Scenario generation emits public operational data and public seed manifest; the running app, API, assistant, fixtures, screenshots, and demo script receive no expected labels.
- A private evaluator manifest is available only to CI/evaluation jobs. It defines required detect/no-detect windows, correlation links, quality caveats, and timing tolerances.
- Fixed holdout random seeds are never used for threshold tuning. Publish aggregate evaluation results/limitations, never hidden labels.
- Measure alert/incident precision-recall against scenario invariants, time-to-detect, duplicate rate, correlation purity, citation coverage, and false-alert counts by scenario.

## 12. Grounded assistant tool design

The assistant is an evidence orchestrator. It receives a server-derived organization/user/scope and can call only read-only typed tools:

| Tool | Inputs | Returned bounded evidence |
|---|---|---|
| `search_incidents` | filters, time range, cursor | incident summaries and calculated-impact labels |
| `get_incident` | incident ID | lifecycle, assets, alerts, evidence IDs, current cues/limits |
| `get_incident_timeline` | incident/range/cursor | chronological typed evidence |
| `get_asset_context` | asset/range | metadata, topology, events, recent incidents |
| `query_metric_series` | asset/metric/range/resolution | bounded aggregates, quality, baseline overlay |
| `get_alert_rationale` | alert ID | detector/config version, score/threshold/features |
| `get_production_context` | product/area/shift | plan/actual, stockpile, dispatch/order-risk inputs |
| `get_source_health` | source/asset/range | freshness, rejects, mapping/schema condition |
| `search_findings` | incident/asset/query | human findings and revisions |

Controls:

- Server injects the organization/scope; the model cannot select another organization or widen time/result bounds.
- Tools apply allowlisted fields, pagination, row/time limits, and source-note redaction.
- Factual answer clauses must cite a returned tool object. Otherwise the assistant says evidence is unavailable or offers general, clearly non-factual investigation guidance.
- The response distinguishes observed facts, possible interpretations, limitations/contradictions, and next investigative checks.
- Source text is untrusted; embedded instructions are never executed. The assistant cannot operate equipment, mutate data, call arbitrary APIs, or make root-cause certainty claims.

## 13. Security, responsible AI, and safety

### MVP controls

- Development/demo identity, role check at API routes, centralized organization-scoped repositories, and audit records for material user actions.
- Input limits/schema validation, safe file handling, dependency/secret scanning, redacted structured logging, environment-secret placeholders, and synthetic-data-only repository policy.
- Assistant tool allowlist, citation gate, scope limits, prompt-injection fixtures, redaction before context, and no operational actions.
- Clear product copy: decision support only; source quality and uncertainty are visible.

### Production-hardening controls

- OIDC/SSO, full RBAC/ABAC, multi-tenant database/deployment controls, encryption/key management, data retention/export policy, security monitoring, penetration testing, and incident response process.
- Managed secrets, backups/restore drills, HTTPS/TLS, raw payload object storage governance, sensitive-read audit policy, and formal threat modeling.

## 14. Testing strategy and acceptance criteria

| Layer | Required MVP tests |
|---|---|
| Unit | Envelope validation, conversion, mapping, quality flags, robust statistics, plan/order formula, hypothesis cue policy, local-role guard, citation renderer |
| Property/fuzz | Random time order/replays/units/schema fields; duplicate invariant; never map ambiguous asset |
| Integration | PostgreSQL migration/constraints, MQTT/file/API ingestion, quarantine, worker evaluation, correlation, plan/order calculation |
| API contract | OpenAPI snapshots, local roles, organization scope boundary, pagination/time limits, idempotency |
| End-to-end | Seed → ingest → evaluate → below-plan incident → evidence/chart → cited assistant answer → human finding/state transition |
| Assistant | Tool allowlist/scope, citation rule, unsupported-claim refusal, injection/redaction fixtures |
| Accessibility | Keyboard/focus/error/color-independent status checks on overview/incident/assets |
| Demo regression | Full catalog with randomized seeds; no scenario-specific app branch; flagship screenshot/smoke path |

MVP merge gate: format/lint/type checks, migrations, unit/integration tests, flagship invariant test, source-data safety scan, and build. Nightly/optional pipeline runs expanded randomized scenarios, accessibility, and performance baseline.

## 15. Observability and developer operations

- Structured logs carry correlation ID, pseudonymous organization/source/asset/incident IDs, code version, and redaction state.
- Metrics: receipt disposition, source lag, watermark/evaluation duration, candidate/alert/correlation counts, plan-vs-actual calculation, API latency/error, database query duration, assistant tool/citation/refusal counts.
- Health endpoints report liveness/readiness/database migration/worker heartbeat/MQTT connection without exposing sensitive diagnostics.
- Local runbooks cover reset/seed, replay batch, source outage, stuck evaluation, detector configuration rollback, and incident evidence inspection.
- MVP targets are development acceptance targets: valid MQTT/API data visible within 60 seconds in a normal local run; chart/incident requests p95 under 1.5 seconds at seed scale; no duplicate business record from replay. Formal availability/RPO/RTO/SLO/load targets belong to production hardening.

## 16. Delivery plan: three workstreams plus root integration/QA

This plan assumes a small agent team working in parallel. Workstreams may be staffed by one contributor each; the root integrator owns the integrated vertical slice, contract alignment, scenario QA, and release readiness.

| Workstream | Primary scope | Immediate deliverables |
|---|---|---|
| A — Product UX and web | Next.js, information architecture, charts, incident/asset/production/data-health UX | Clickable screens backed by stable API contracts; accessibility smoke path |
| B — Data, backend, and detection | FastAPI, PostgreSQL, ingestion, generator, quality, statistics, correlation | End-to-end seeded evidence path; detectors/evaluation harness |
| C — Trust, assistant, and delivery | Tool facade, citations, test fixtures, Docker, CI, docs/runbooks | Bounded assistant, security baseline, reproducible demo/release artifacts |
| Root integration/QA | API/schema decisions, cross-workstream test, scenario invariants, visual demo polish | Integrated Compose stack, milestone gates, final demo rehearsal |

### Milestone 0 — foundation gate (immediate)

**Tasks:** repository shape; Compose services; FastAPI/Next.js health shell; PostgreSQL/Alembic; shared canonical types/OpenAPI; source-safe synthetic policy; scenario-generator skeleton; CI build/lint/test.

**Dependencies:** none.

**Gate:** one documented command starts UI/API/worker/DB/MQTT; empty UI truthfully shows service state; migration succeeds from empty DB; CI passes; an ADR records schema, worker, assistant, and scenario-boundary decisions.

### Milestone 1 — credible data path

**Tasks:** plant asset/topology registry; canonical envelope; MQTT/API/file ingestion; receipts/quarantine; source health; asset/data-health views; generator emits S02, S09, S10, S11, S12.

**Dependencies:** Milestone 0 contracts.

**Gate:** accepted/rejected/duplicate/late/mismapped/schema-drift data is traceable to source/mapping/version; no ambiguous asset is silently assigned; S09–S12 integration invariants pass; operator can trace a chart point to its receipt.

**Demo:** ingest a normal randomized plant feed and show source health plus raw provenance.

### Milestone 2 — production intelligence gate

**Tasks:** plan/actual, product output, stockpiles, synthetic dispatch/orders/haul-distance assumptions; transparent baseline/rules; source-freshness/freeze policies; alert rationale; S01–S08 generator/evaluator coverage.

**Dependencies:** Milestone 1 canonical facts and data-quality state.

**Gate:** S01 gradual crusher condition produces evidence-backed alert candidates; S02 normal variation and S04 isolated spike do not create misleading high incidents; S05/S06 distinguish instrumentation/connectivity evidence; S07 exposes process restriction; S08 retains maintenance suppression reason. All show detector/baseline/configuration/quality facts.

**Demo:** overview explains production below plan and shows estimated order exposure with formula inputs.

### Milestone 3 — incident investigation gate

**Tasks:** deterministic correlation; incident lifecycle/assignment/findings/audit; immutable evidence; incident/asset/production views; hypothesis cue/limits UI; flagship seeded flow.

**Dependencies:** Milestone 2 alerts/calculations.

**Gate:** flagship produces a data-driven priority incident with degradation plus ambiguity evidence; user reaches raw source facts within two interactions; human can acknowledge, add finding, assign, and hand off; no automated closure; no hardcoded flagship UI/result code.

**Demo:** conduct the full “below plan—what next?” investigation without developer tools.

### Milestone 4 — grounded assistant and release gate

**Tasks:** tool facade, citations/deep links, transcript/safety audit, adversarial fixtures, Compose reset/runbooks, complete scenario CI, visual/accessibility review, README/demo capture.

**Dependencies:** Milestone 3 stable read models/evidence contracts.

**Gate:** assistant gives cited/qualified answers to flagship questions, refuses unsupported root cause, cannot escape scope/tool list, and identifies relevant data gaps. Randomized catalog gate passes; a clean evaluator starts/resets/runs the demo from README alone.

**Demo:** “What changed? What supports it? What could contradict it? What should we check next?” answered through evidence deep links.

### Production-hardening milestones (later)

1. OIDC/full RBAC/multi-tenancy and managed deployment baseline.
2. Queue/object storage/backup/restore, managed observability, SLOs and load testing.
3. Shadow integration with one real source and one asset/process slice; no decision-making dependence.
4. Shadow detection and human-triage pilot alongside incumbent tools.
5. Controlled one-way CMMS/ticket linkage only after security, audit, retention, and rollback requirements are accepted.

## 17. Risk register

| Risk | Mitigation and trigger |
|---|---|
| Demo becomes scripted | Data-only randomized seeds, private evaluator, code-review prohibition on scenario branches; trigger: scenario name/seed referenced by app logic |
| Data quality makes conclusions unsafe | Quarantine, visible trust state, never alert solely on untrusted input; trigger: lag/reject/ambiguity condition |
| False positives erode trust | Statistics first, normal/spike/maintenance scenarios, holdout seeds, human findings; trigger: scenario regression or operator feedback |
| Assistant hallucinates/leaks | Read-only tools, server scope, citations/redaction, injection suite; trigger: unsupported claim/citation gap |
| Commercial metric overstates value | Formula-visible synthetic estimates, no revenue claim; trigger: missing inventory/order/haul assumption |
| Scope expands into MES/control system | Explicit non-goals and product review; trigger: direct write-back/control request |
| Small team loses integration quality | Root-owned contracts/gates and Compose smoke path every milestone; trigger: independently passing components without vertical demo |
| Schema traps future deployment | Minimal canonical model, versioned mappings, ADR/migration discipline; trigger: second source/asset type forces one-off fields |

## 18. Definition of done for portfolio MVP

The MVP is done only when:

- A new evaluator can start, reset, and run a randomized scenario from the README without hidden developer intervention.
- MQTT, HTTP, and file input paths produce traceable canonical facts and visible duplicate/late/invalid/ambiguous/schema-drift behavior.
- Production below plan, product output, stockpile buffer, dispatch/order exposure, and haul-distance assumptions are visible and correctly labeled synthetic estimates.
- The flagship incident arises from general rules/correlation and shows rising secondary-crusher signals, falling throughput/output, source-quality ambiguity, evidence links, and no asserted root cause.
- An operator can acknowledge, investigate, record a finding, assign/handoff, resolve with a human reason, and inspect the audit trail.
- Every detector conclusion exposes baseline/threshold/version/quality; assistant facts are cited or explicitly unavailable/uncertain.
- The assistant is tool-scoped/read-only, passes injection/scope/refusal tests, and cannot perform plant or incident mutations.
- The Compose stack, tests, scenario manifests, runbooks, ADRs, README, limitations, and demo capture are current.

## 19. Public portfolio and README expectations

The repository should be evaluable in fifteen minutes:

1. Lead README with the below-plan question, product claim/limitations, architecture, stack, local startup, and synthetic-data policy.
2. Include a “Run the flagship” path with a seed/reset command, expected observable states, and a short screenshot/video. Describe milestones, not a fake click script.
3. Publish source contract, plant model, scenario catalog, detector method, hidden-evaluator boundary, assistant tools, and threat/safety summary.
4. Include both what works and what does not: decision support only, synthetic data, no root-cause certainty, no autonomous control, and no production accuracy claim.
5. Include evidence screenshots showing data quality/citations and a code/test note demonstrating the flagship is generated by ordinary product logic.

## 20. Real-system replacement path

Sonoran moves from portfolio to real system through controlled augmentation:

1. **Discovery:** select one process slice and 1–2 sources; establish data ownership, sensitivity, SLA, retention, source contract, and operator success measure.
2. **Shadow ingest:** read-only ingest and map real signals; compare freshness/quality against incumbent views. No operational reliance.
3. **Shadow intelligence:** run transparent detection and plan/output context with domain review; quantify nuisance/coverage and refine policy.
4. **Human-triage pilot:** a narrow plant/shift team uses Sonoran beside incumbent tools; gather handoff/false-positive/decision-quality feedback.
5. **Controlled system integration:** add links to CMMS/ticketing/dispatch only after identity, audit, retention, security, and rollback acceptance; start one-way and human-confirmed.
6. **Operationalization:** introduce OIDC/multi-tenant controls, managed services, backups/restore, on-call, SLOs, governance, and change management.
7. **Replacement decision:** replace a specific incumbent workflow only after agreed operational benefit, security approval, supportability, recoverability, and rollback are demonstrated.

No phase authorizes plant control without a separately scoped safety, regulatory, security, and customer-approval program.

## 21. Immediate next actions

- [ ] Ratify MVP boundary, core question, and flagship evidence sequence.
- [ ] Record ADRs for monorepo, schema/partition approach, job interface, local identity boundary, assistant provider facade, and hidden evaluator.
- [ ] Deliver Milestone 0 Compose health shell and canonical types before feature screens.
- [ ] Implement scenario generator/public manifest/private CI manifest before detector tuning.
- [ ] Build the vertical path in milestone order; do not start optional ML or enterprise hardening before the flagship gate.
