# Visual analytics and evidence definitions

This reference defines the meaning of every public visual analytic in the
Sonoran demo. It exists to prevent a presentation layer from turning incomplete
data into a persuasive-looking claim. It supports the recruiter journey in
[RECRUITER_JOURNEY.md](RECRUITER_JOURNEY.md) and the API mapping in
[INTEGRATION.md](INTEGRATION.md).

## Evidence hierarchy

The interface presents information in this order:

1. **Observed fact** — a stored, time-stamped observation, finding, or incident
   record.
2. **Derived fact** — a documented calculation from stored records, such as a
   count, median baseline, or difference from that baseline.
3. **Investigation cue** — an explainable detector result or a human next
   check. It is not root cause.
4. **Unknown or unavailable** — a value the platform does not store or cannot
   calculate. It must remain unavailable rather than becoming a zero, score,
   or placeholder.

No visual may skip levels. A chart annotation may point to an observation or
finding; it may not label an unobserved mechanical condition as fact.

## Operations briefing definitions

`GET /api/v1/operations/briefing?site_id=sonoran-west` is the source for the
overview's public evidence summary. Its `replay_boundary` tells the visitor
which rows and timestamp field underpin the screen. The response does not read
simulator-private truth.

| Visual element | Definition | Source and calculation | Interpretation boundary |
| --- | --- | --- | --- |
| Observation count | Number of stored observation rows for the selected site | `observation_count` | It is a replay volume, not a data-completeness percentage. |
| Time window | Earliest to latest `observed_at` in the selected site | `oldest_observed_at`, `latest_observed_at` | Shows the scope of the replay; it is not a live-status indicator. |
| Throughput series | Stored production-record `attributes.throughput_tph` values ordered by `observed_at` | `production.series` | Every point is a public stored record. Missing points are not interpolated. |
| Current throughput | Latest point in the returned throughput series | `production.current` | “Current” means latest in the seeded replay, not a live plant reading. |
| Baseline | Median of unflagged returned production-record values | `production.baseline.method`, `.value`, `.sample_count` | A robust reference for this replay only; not plan, capacity, target, or forecast. |
| Difference from baseline | Current throughput minus clean-record median | `production.delta_vs_baseline` | Describes a difference, not revenue, lost tons, availability, or cause. |
| Flagged records | Observation rows with a non-accepted quality state or quality flags | `flagged_observation_count`, `data_quality_flag_counts` | Explains data condition; it does not certify or invalidate the entire site. |
| Per-asset context | Counts and latest stored time by asset, plus active incident count | `assets[]` | Not health, runtime, availability, remaining useful life, or a maintenance recommendation. |

## Chart and annotation rules

- Name the metric, unit, site, time window, and baseline method beside or in a
  keyboard-reachable details region for every chart.
- Use a line only when time ordering is meaningful. Do not smooth, project,
  interpolate, or decorate a sparse series.
- Render a table or text alternative with the plotted values and annotation
  references. Screen-reader users must be able to reach the same facts.
- Annotate a finding with its detector name/version, observed time window, and
  rationale. Link to the incident or evidence detail; do not replace the
  evidence with an icon or a colour.
- Use amber/red only to communicate an explicit severity or quality condition
  already returned by the API. Pair it with text. Blue is reserved for action
  or emphasis; a “live” green dot is not used because the demo is a replay.
- If no series, baseline, or eligible clean records exist, show the absence and
  its consequence. For example: “No clean production records are available to
  calculate a baseline.”

## Incident and data-quality definitions

An incident groups one or more explainable findings. Its evidence area must
show linked findings and linked observations, including observed timestamps,
quality flags, and detector rationale. A finding can say that a recorded value
deviated from an ordinary recent pattern or that source freshness is degraded.
It cannot say a bearing is failing, a restriction exists, or a causal chain is
proven without a separate validated input and explicit product rule.

Data quality is a parallel explanation, not a decorative health score. The
interface should state the flag/reason, affected record count, scope, and the
decision consequence. For example, a late-arriving record can support an
investigation with a timing caveat; an invalid-unit record should not be used
as detector evidence. See [DATA_CONTRACTS.md](DATA_CONTRACTS.md) for the
contract boundary and [INTEGRATION.md](INTEGRATION.md) for the implemented
detector rules.

## Equipment diagram legend and state language

Treat an equipment diagram as an evidence index, not a live plant image. Its
visible legend must say: **“Equipment review order — not a plant map or live
status display.”** A visitor should be able to see what each marker means
without reading hover text.

For every equipment marker/card, render: a friendly equipment name; the number
of stored readings and latest recorded time; the number of data warnings; and
the number of issues to review. Use accurate absence language: **“No open issue
in this demo window”** rather than “healthy,” “normal,” “online,” or a green
status dot. State explicitly that an issue count is a review priority, not a
fault probability or equipment-condition score.

Use arrows only for a documented returned relationship. If positions are only
there to organize review, show numbered placement and call the display an
equipment review order. Selecting an asset should lead to its observed facts,
data warnings, and related issues—not an inferred health percentage.

## Synthetic replay versus a real deployment

The data path is real application behavior using synthetic inputs: the
generator emits contract-shaped observations, the platform validates and
stores them, then read models and detectors operate only on those stored rows.
The scenario's hidden labels, seed, intended failure pattern, and expected
answer remain evaluation-only. The web app and API have no runtime path to
them.

In a real deployment, the same visual definitions would need a site-approved
metric catalog, source ownership, clock synchronization policy, historian/MES
or dispatch connector agreements, data-retention controls, authentication,
and validated operational thresholds. The demo does **not** demonstrate those
site integrations, real-time freshness, process safety, financial impact,
maintenance diagnosis, or production accuracy.
