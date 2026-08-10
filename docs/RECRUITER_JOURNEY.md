# Recruiter Journey and Authenticity Standard

This document defines the public demonstration journey for Sonoran Operations
Intelligence. It is deliberately designed for a recruiter or hiring manager to
understand the product and its engineering decisions without industrial domain
knowledge, a prepared presenter, or trust in unexplained dashboard numbers.

It complements the technical delivery plan in
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md): that plan defines the system
and its production path; this document defines how the public product proves
those decisions in a short, self-directed review.

## Demonstration context and audience

Sonoran is a portfolio demonstration for a fictional aggregate operation. It
shows how an operations-data application can turn messy, time-stamped signals
into an evidence-led investigation. It is not a Granite product, does not use
Granite branding, and does not claim access to Granite data or workflows.

The primary visitor is a Granite recruiter or a hiring manager assessing an
industrial AI, analytics, applications, or data-product candidate. They are
likely to ask:

- Is this a real application, or a polished collection of invented dashboard
  numbers?
- Can the candidate distinguish an equipment issue from bad or late data?
- Does the interface explain the next decision in plain language?
- Can I follow a fact back to its source and understand the uncertainty?
- Does the work show product judgment as well as engineering ability?
- What parts would require real site integration and operational validation?

The product must answer those questions through the interaction itself. A
visitor should not need to read source code, already understand crushing
operations, or infer the intended story from a chart.

## The optional four-minute guided review

The default landing state offers two equal choices: **Start the guided review**
and **Explore freely**. The guided review is a persistent, dismissible rail or
compact briefing panel, never a blocking modal or a scripted product tour. It
shows progress, explains why the current view matters, and provides one clear
next action. Visitors can leave it at any point without losing access to the
application.

| Step | Visitor question | Objective and on-screen copy | Evidence to expose | Action |
| --- | --- | --- | --- | --- |
| 1. Orient (0:00–0:30) | What am I looking at? | **“A working operations-data demo, built around a synthetic aggregate site.”** Explain that the demo replays synthetic public observations through the same ingestion, data-quality, finding, incident, and investigation paths shown on screen. | Observation count, source count, last refresh, public/read-only status, and a short system map: inputs → quality checks → findings → incident → human investigation. | Continue to the current operating story. |
| 2. See the operating story (0:30–1:15) | Why does this require attention? | **“Start with the question, not the widgets.”** Present one priority investigation in context: an observed change on the crusher train, the related production signal, and the current data-quality caveat. State the platform has identified an investigation priority, not a mechanical diagnosis. | A time series made from real API observations, annotated with the observation window and a link to the incident. Supporting counts must be computed from returned records, not placeholders. | Open the priority incident. |
| 3. Inspect the incident (1:15–2:15) | Why does the system think this matters? | **“Evidence supports a next check; it does not prove root cause.”** Show the concrete signal changes, detector rationale, source/time provenance, and competing explanations. Make missing or weak evidence visually explicit. | Expanded finding evidence, linked observations, detector/version, quality flags, observed and received timestamps, and the human next-check suggestion. | Review the data-quality caveat. |
| 4. Test data trust (2:15–3:00) | Could this be a data problem instead? | **“The platform separates an operating signal from the trustworthiness of that signal.”** State whether records are late, malformed, duplicated, stale, or clean—and what that means for the investigation. | Source freshness, affected records, reason codes, and a plain-language interpretation. An empty state explains why nothing is present and what normal operation means. | Ask an evidence question. |
| 5. Explore evidence (3:00–4:00) | Can I verify the story without taking anyone’s word for it? | **“Use bounded evidence tools to inspect the same public records.”** Describe the deterministic retrieval boundary in normal language: no generative model, no raw database access, no mutation, and citations for every result. | A readable result table or timeline, concise citations, uncertainty notes, and a link back to the source incident/observation. Avoid raw JSON as the primary experience. | Explore freely, view architecture, or open the repository. |

The guidance should use concrete, calm language. Good examples: “3 source
feeds were observed in this replay,” “12 records arrived late,” and “Inspect
the vibration sensor and crusher bearing before assigning cause.” Avoid
unearned claims such as “AI detected a failure,” “real-time intelligence,” or
“actionable insights.”

### The synthetic-to-real explanation

The first step includes a short “How to read this demo” disclosure. It must
make a useful distinction rather than merely displaying a synthetic-data
warning:

> The records are synthetic, but the application path is real: contract-shaped
> observations are ingested, quality-checked, stored, grouped into findings and
> incidents, and returned as cited evidence. The generator's hidden scenario
> labels are kept out of the app and used only to evaluate it.

The corresponding “what changes at a real site” link explains that connectors,
metric ownership, access control, retention, thresholds, and operational
validation are site-specific work still to be completed. It does not imply that
the public replay has those integrations. See
[VISUAL_ANALYTICS.md](VISUAL_ANALYTICS.md#synthetic-replay-versus-a-real-deployment)
for the precise boundary.

## Trust moments

The path contains deliberate moments where the product earns—not requests—
trust:

1. **Boundary disclosed before the first metric.** The opening label makes the
   synthetic, read-only portfolio context clear while still describing the
   working data path.
2. **A single operating question before a dashboard.** The overview leads with
   a priority investigation and its implications instead of a grid of equally
   weighted KPIs.
3. **Every important number has provenance.** A visitor can see the source,
   time window, definition, and calculation behind a chart, count, or score.
4. **Data quality is a competing explanation.** Late, missing, duplicated, or
   malformed records are presented as operationally relevant evidence—not
   hidden behind a high “trust score.”
5. **Uncertainty survives drill-down.** The incident cannot become more
   certain in the copy than the evidence permits. “Insufficient evidence” is a
   valid result.
6. **The assistant is bounded rather than theatrical.** It retrieves cited
   records through fixed, read-only tools. It does not imply autonomy, live
   plant control, or hidden reasoning.
7. **The public app remains safe.** Read-only controls are visibly labeled;
   lifecycle actions demonstrate the model but do not allow a public visitor to
   change records.

## Free exploration and failure-safe behavior

Guidance must assist, not constrain. On every step, the navigation stays
available and “Explore freely” dismisses the rail. Returning to a guided view
restores the appropriate step based on the current route; it does not reset or
trap the visitor.

When the expected public record is unavailable, the product must not silently
substitute an attractive scenario result. Instead it should say what happened,
show the actual empty or degraded state, and offer a useful next action (for
example, review another active incident or reload the seeded demo). Empty
states explain both cause and consequence: “No linked evidence was returned
for this incident. The investigation remains open; do not infer a cause from
this screen.”

## Explicit boundaries: what Sonoran does and does not claim

Sonoran **does** demonstrate:

- Contract-validated ingestion of synthetic, public observation records.
- Traceable data-quality findings and deterministic incident/evidence
  workflows.
- A user experience that separates observation, hypothesis, and unknown.
- Bounded, cited evidence retrieval against the application’s public data.

Sonoran **does not** claim:

- A live connection to Granite, a customer, or any plant system.
- PLC/SCADA control, safety certification, outage prevention, or autonomous
  operational action.
- Mechanical root-cause determination from telemetry alone.
- That synthetic data establishes production accuracy, financial impact, or
  field performance.
- That a generative AI model is making the public demo’s decisions.

This boundary is product content, not a legal footnote. It appears in the
orientation panel, evidence explorer disclosure, README, and architecture
documentation.

## Role alignment without borrowing Granite’s identity

The demo should speak to the work relevant to a construction-materials and
aggregate operator: safety-minded investigation, production continuity,
equipment/process ambiguity, data stewardship, and respectful collaboration
between operations and engineering. It should use general phrases such as
“aggregate operations use case” and “asset-intensive production environment.”

It must not use Granite logos, internal terminology, colors, customer stories,
or language implying endorsement. The recruiter should be able to recognize
the role fit from the quality of the product decisions, not from simulated
co-branding.

## Design principles: authenticity before aesthetics

The visual system follows the evidence-first direction in the Metamorphysis
brand guidance: plain English, concrete verbs, visible boundaries, restrained
color, and real product evidence rather than decorative imagery. Sonoran may
retain a measured industrial amber for attention states, but uses a warm light
canvas, legible dark ink, quiet white surfaces, and restrained blue/lavender
supporting tints. IBM Plex Sans is the primary UI face; a monospace face is
reserved for IDs and timestamps.

The following are common template or AI-generated-interface tells and are
prohibited unless they carry clear operational meaning:

- A page made of evenly sized metric cards with equal visual weight.
- Decorative trend lines, gauges, or “live” labels not tied to returned data.
- Gradients, glow effects, sparkles, pseudo-scientific glyphs, or generic
  avatar chips used as decoration.
- Vague labels such as “Needs review,” “Data trust,” or “Insights” without a
  definition, affected scope, and next human decision.
- Impossible precision, arbitrary percentages, or convenient zero/100 values
  standing in for unavailable calculations.
- Raw object/JSON dumps presented as an assistant answer or evidence citation.
- A confident conclusion alongside no evidence, an empty timeline, or a
  contradictory source-health claim.

Prefer editorial hierarchy over card density: one clearly stated operating
story, supporting facts, annotated data, and an obvious path to evidence.
Whitespace, plain tables, timestamps, labels, and compact definitions are
useful when they clarify what is known. Any chart must use actual public API
data, name its metric/unit/time window, and provide its values or an equivalent
text/table alternative.

## Cognitive-load and plain-English implementation brief

This is the implementation brief for the main/frontend owner. It is based on a
first-time recruiter/operator reading of the current public screens. The
application already has credible evidence and boundaries; the remaining risk is
that specialist terms make a visitor work too hard before they understand the
point of the demo.

### P0: orient a first-time visitor in 20 seconds

Place this compact statement directly below the page title on the default
Operations screen, ahead of charts, tiles, or a plant diagram:

> **Demo data. Working software.** This is a simulated aggregate-plant replay
> running through a deployed application. It flags records that need a human
> check; it does not diagnose equipment or control a plant.

Follow it with one primary action and one quiet link:

- Primary: **Review the top issue**
- Secondary: **See how the demo works**

Replace “Start walkthrough” with **Take the 3-minute tour**. Replace “Explore
freely” with **Browse on my own**. The secondary option should not look like a
failure path.

The top navigation should use these visitor-facing labels, in this order:

| Current label | Replace with | Why |
| --- | --- | --- |
| Operations | **Start here** | Gives an unfamiliar visitor an obvious entry point. |
| Incident records | **Issues to review** | Explains the decision purpose before the data model. |
| Data quality | **Check the data** | States the action, not an abstract category. |
| Evidence explorer | **Inspect evidence** | Uses a common verb and matches the next task. |
| AI analyst | **Ask about the evidence** | Centers the bounded task, not the technology. Keep “AI-assisted” in the disclosure only. |
| How it works | **About this demo** | Answers the recruiter’s immediate credibility question. |

The product name may remain Sonoran Ops, but replace the small “Operations
intelligence” subtitle with **An evidence-led operations demo**. “Intelligence”
is broad and does not tell a recruiter what they can do here.

### P0: terms that require translation

Do not remove precise terms from a technical detail view. Introduce them once
in plain language, then use the shorter term consistently. Tooltips or a
“What this means” line should carry the precise definition.

| Current term/copy | Plain-English replacement | Keep the technical meaning in |
| --- | --- | --- |
| Synthetic aggregate-plant replay | **Simulated plant data, replayed for this demo** | About this demo: fixed, repeatable data window. |
| Operating record | **The data reviewed on this screen** | Evidence metadata. |
| Observation | **A time-stamped source reading** | Glossary: preserved as received. |
| Finding | **A rule noticed an unusual pattern** | Detail: detector name/version and rule rationale. |
| Incident | **An issue that needs human review** | Detail: durable review record linking findings/evidence. |
| Detector output | **What the rule noticed** | Detail: detector/version. |
| Evaluation window | **Time period the rule checked** | Detail: start/end times. |
| Linked source observations | **Source readings behind this issue** | Table title/metadata. |
| Quality flags | **Data warnings** | Detail: exact flag names/reason codes. |
| Bounded query | **A limited evidence search** | Disclosure: only approved record types/time ranges. |
| Scenario ground truth / hidden answer | **The simulator’s private answer key** | About-this-demo boundary. |
| Replay coverage by asset | **Data received for each piece of equipment** | Detail: record count and latest timestamp. |
| Asset review sequence | **Equipment review order** | Legend: it is not a plant map. |
| Returned signal series | **Recorded signals over this demo window** | Chart: metric, unit, points, time window. |
| Incident distribution | **Issues by equipment and status** | Detail: severity/state grouping. |

Avoid phrases such as “returned,” “deployed record,” “platform-visible,”
“evidence boundary,” and “workflow” in primary copy. They are useful in
technical documentation but force a recruiter to infer the real-world meaning.

### P0: every record must answer four questions

Each record surface needs a fixed scan pattern. Use sentence-case question
headings; do not rely on a reader to decode an ID, pill, or raw detector name.

| Record type | What happened? | Where? | Why it matters | What to check next |
| --- | --- | --- | --- | --- |
| Source reading | “This reading was recorded.” State metric, value, unit, and time. | Equipment/source name. | State data warning if present; otherwise “No data warning on this reading.” | “Compare it with nearby readings and the equipment state.” |
| Finding | “A rule saw [metric] [rise/fall/deviation] during [time range].” | Equipment and metric. | “This is a cue to investigate, not a failure diagnosis.” | “Review the cited readings and their data warnings.” |
| Issue / incident | “This issue groups [n] unusual-pattern findings for review.” | Affected equipment/process area. | State severity as priority for review, not probability; name any contradictory data warning. | “Check the source readings, field condition, and current operating state.” |
| Data warning | “These [n] records arrived late / had [flag].” | Affected source/equipment/time range. | Explain whether comparison is less reliable or whether the record was retained but excluded. | “Confirm source timing/mapping before using this as operational evidence.” |
| AI-assisted answer | “Here is a summary of the cited records.” | Name the selected site and evidence range. | “It does not establish root cause or authorize action.” | “Open the cited issue/readings; verify in the field.” |

For an empty state, preserve the same scan pattern. Example: **“No source
readings are linked to this issue yet. Do not infer a cause from this screen.
Next: inspect another open issue or the data-warning view.”**

### P1: plant-diagram and state language

The asset/equipment diagram must never be mistaken for a live SCADA display,
a geographic map, or a health dashboard. Put this legend above the diagram:

> **Equipment review order — not a plant map or live status display.** Each
> card shows stored demo records, data warnings, and issues that need review.

Use a consistent three-line label per asset:

1. **Equipment:** “Primary crusher” (friendly name first; technical ID only in
   secondary text).
2. **What the demo has:** “126 stored readings · latest at 10:42 AM MST.”
3. **Review state:** “1 issue to review” / “Data warnings on 4 readings” /
   “No open issue in this demo window.”

Do not use “healthy,” “normal,” “online,” a green dot, “no concern,” or “no
active incident” as a proxy for condition. “No open issue in this demo window”
is an accurate absence statement. Use arrows only if they mean an actual
returned process relationship; otherwise use numbered placement and call it a
review order. A diagram click should open a short equipment summary with the
four record questions above, not a generic details panel.

### Guided three-minute sequence

The current five concepts should be presented as four short decisions, with
the visitor free to leave at every step:

| Time | Screen | Guide copy | One action |
| --- | --- | --- | --- |
| 0:00–0:20 | Start here | **“Demo data. Working software.”** Explain the simulated-input/working-app boundary and the one issue to review. | **Review the top issue** |
| 0:20–1:05 | Issue detail | **“What changed, and why should someone look?”** Show the rule’s plain-language finding, affected equipment, cited readings, and uncertainty. | **See the source readings** |
| 1:05–1:45 | Check the data | **“Could the data itself explain this?”** Show affected records, warning meaning, and whether comparisons are limited. | **Inspect the evidence** |
| 1:45–3:00 | Inspect evidence / About this demo | **“Verify the story, then see the boundary.”** Run one cited evidence search; show simulated inputs versus real ingestion/storage/rules/UI and what is not claimed. | **Browse on my own** or **View the repository** |

The AI-assisted answer is optional after step 4, not part of the default proof
path. A recruiter should first see the evidence without having to trust a
model-generated summary.

### Acceptance criteria for the frontend implementation

- In a 20-second unmoderated test, a first-time visitor can accurately say:
  “The data is simulated; the software is real; it is showing an issue for a
  human to check; I should open the top issue.”
- In a three-minute test, the visitor can distinguish a source reading, rule
  finding, issue/incident, and data warning without opening external docs.
- Every primary screen presents one task-oriented heading, one-sentence plain
  language summary, one primary next action, and no more than three equally
  prominent metrics before the task is clear.
- Every chart and diagram has a title that names its decision purpose, a
  legend/state statement, source/time/unit context, and a text/table
  alternative.
- An issue detail states why it exists, where it applies, the data limitation,
  and a human next check before detector IDs or timeline metadata.
- “No issue,” “no data warning,” and “not returned” are described as scope or
  availability statements—not good health, normal operation, or live status.
- The AI-assisted screen visibly states its evidence-only/read-only limit,
  shows citations and uncertainty, and offers a direct path to source records.
- A visitor can leave the tour, use back/forward, and resume exploration
  without losing context. All guide actions and diagram interactions are
  keyboard reachable with visible focus.

## Prioritized acceptance criteria

### P0 — required before sharing the public demo

- A first-time visitor can start or dismiss the five-step guided review from
  the overview; it is keyboard reachable, non-blocking, and route-aware.
- The overview names the current operating question and makes its synthetic,
  read-only boundary clear before showing derived metrics.
- Every visible KPI, chart, confidence statement, and source-health statement
  is backed by a defined public API field or visibly marked unavailable. No
  decorative series, fabricated availability, fixed production delta, or
  default 0%/100% claim remains.
- A priority incident has visible linked evidence or an explicit, honest empty
  state; it never claims linked evidence while rendering none.
- The data-quality view explains affected data, reason, scope, and
  investigation consequence. It cannot call a feed degraded while declaring
  the whole system fit for decisions without a visible qualification.
- Evidence explorer results are readable records/citations with uncertainty,
  not raw debug output. Its deterministic, read-only boundary is clear.
- Public deployment remains read-only and all essential paths work at
  `/portfolio/sonoran-ops`.

### P1 — strengthens the evaluation

- A source-to-screen provenance affordance exists for significant values and
  chart annotations.
- The guide includes compact links to architecture, data contracts, and the
  source repository for technical reviewers.
- Empty, loading, degraded, and API-error states preserve the same calm,
  concrete language and next action.
- Visual regression checks cover the overview, incident, data trust, and
  evidence explorer at desktop and narrow widths.

### P2 — later extension

- Guided paths vary by visitor role (recruiter, shift supervisor, data owner)
  without changing product truth.
- A saved shareable incident view, real authentication, source connectors, and
  production-grade audit/retention controls are added only with the hardening
  work described in the implementation plan.

## Evaluation and analytics plan

The public site must collect no unnecessary personal data. If lightweight
portfolio analytics are enabled, disclose them in the site privacy context and
measure anonymous, aggregate behavior only.

| Question | Measure | Success signal | Safeguard |
| --- | --- | --- | --- |
| Can a visitor orient quickly? | Guided review start rate; completion of step 1 | Most guided visitors reach the operating story | No session replay or sensitive form capture |
| Does the story hold attention? | Step-to-step completion; incident opened from guide | Meaningful progression from overview to evidence | Treat low traffic as qualitative, not statistically decisive |
| Do visitors verify evidence? | Incident evidence and data-quality drill-down rate; evidence-tool use | Visitors reach at least one provenance surface | Record aggregate event names only, not tool arguments or record contents |
| Does the UI create confusion? | Guide dismissal, backtracking, error/empty-state exposure, optional short feedback | Identify the step/copy needing revision | Never frame dismissal as failure; free exploration is intentional |
| Does the product support the hiring story? | Recruiter/hiring-manager qualitative feedback: “I can explain what it does, why the incident matters, and its limits.” | Clear repeatable explanation without a live presenter | Ask permission before associating feedback with a person or company |

Run an internal task test before each major release with five prompts: “What is
this?”, “What changed?”, “Why should I trust it?”, “What could contradict the
equipment explanation?”, and “What would you inspect next?” A reviewer should
be able to answer all five from the interface in four minutes. Record defects
as product gaps—not as reasons to add more dashboard decoration.

## Release-review script

Before sharing the demo, a reviewer who did not build it should complete the
four-minute path without coaching. Ask them to state: the data boundary, the
current operating question, the evidence supporting it, the data-quality
caveat, and the next human check. If any answer depends on a presenter's
explanation rather than the interface, revise the current step's copy,
evidence, or navigation. The relevant visual definitions are in
[VISUAL_ANALYTICS.md](VISUAL_ANALYTICS.md); a future generative analyst must
meet the governance gates in [GOVERNED_AI_ANALYST.md](GOVERNED_AI_ANALYST.md).
