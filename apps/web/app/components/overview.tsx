import type { Incident, OperationsBriefing } from "../../lib/api/types";
import { VisualAnalytics } from "./analytics";
import { selectPriorityIncident } from "./incident-priority";
import { Empty, number, Panel, Pill, time } from "./shared";

function ThroughputChart({ briefing }: { briefing: OperationsBriefing }) {
  const { points, baselineValue, unit } = briefing.production;

  if (!points.length) {
    return (
      <Empty title="No production record series was returned">
        The replay returned run facts, but no chartable observations for this
        window.
      </Empty>
    );
  }

  const values = points.map((point) => point.value);
  const min = Math.min(...values, baselineValue ?? values[0]) * 0.97;
  const max = Math.max(...values, baselineValue ?? values[0]) * 1.03;
  const range = max - min || 1;
  const coordinates = points
    .map(
      (point, index) =>
        `${(index / Math.max(points.length - 1, 1)) * 100},${
          100 - ((point.value - min) / range) * 100
        }`,
    )
    .join(" ");
  const baselineY =
    baselineValue === null || baselineValue === undefined
      ? undefined
      : 100 - ((baselineValue - min) / range) * 100;
  const label = `Recorded throughput from ${number(values[0])} to ${number(
    values.at(-1),
  )} ${unit}. ${
    baselineValue !== null && baselineValue !== undefined
      ? `Baseline ${number(baselineValue)} ${unit}: median of ${
          briefing.production.baselineSampleCount
        } clean production records.`
      : "No baseline was returned."
  }`;

  return (
    <figure className="throughput">
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        role="img"
        aria-label={label}
      >
        <line x1="0" y1="25" x2="100" y2="25" />
        <line x1="0" y1="50" x2="100" y2="50" />
        <line x1="0" y1="75" x2="100" y2="75" />
        {baselineY !== undefined && (
          <line
            className="baseline"
            x1="0"
            y1={baselineY}
            x2="100"
            y2={baselineY}
          />
        )}
        <polyline points={coordinates} />
      </svg>
      <figcaption>
        <span>{time(points[0]?.observedAt)}</span>
        <span>{time(points.at(-1)?.observedAt)}</span>
      </figcaption>
    </figure>
  );
}

export function Overview({
  briefing,
  incidents,
  onIncident,
  onView,
}: {
  briefing: OperationsBriefing;
  incidents: Incident[];
  onIncident: (id: string) => void;
  onView: (view: "incidents" | "quality" | "explorer") => void;
}) {
  const priority = selectPriorityIncident(incidents);
  const active = incidents.filter(
    (incident) =>
      incident !== undefined &&
      incident.state !== "resolved" &&
      incident.state !== "dismissed",
  );
  const production = briefing.production;
  const qualityRate = briefing.observationCount
    ? (briefing.flaggedCount / briefing.observationCount) * 100
    : 0;
  const recordSeriesDescription =
    briefing.replay.productionSeriesDefinition.replace(
      /feed-rate/gi,
      "recorded throughput",
    );

  return (
    <div className="view-stack">
      <section
        className="operating-story"
        aria-labelledby="operating-story-title"
      >
        <div>
          <h2 id="operating-story-title">
            {priority?.title ?? "No open incidents in this replay"}
          </h2>
          <p>
            {priority?.summary ??
              "The platform has no open incident record to review in the current data window."}
          </p>
          {priority && (
            <button className="primary" onClick={() => onIncident(priority.id)}>
              Review the evidence
            </button>
          )}
        </div>
        <dl>
          <div>
            <dt>Latest recorded throughput</dt>
            <dd>
              {number(production.currentValue)} <small>{production.unit}</small>
            </dd>
          </div>
          <div>
            <dt>Replay window</dt>
            <dd>
              {number(briefing.observationCount)} <small>records</small>
            </dd>
          </div>
          <div>
            <dt>Flagged records</dt>
            <dd>
              {number(briefing.flaggedCount)} <small>need context</small>
            </dd>
          </div>
        </dl>
      </section>
      <section className="demo-orientation" aria-labelledby="demo-orientation-title">
        <div>
          <h2 id="demo-orientation-title">What this screen demonstrates</h2>
          <p>
            A synthetic aggregate replay is processed by deployed ingestion, finding, incident, and
            evidence-review services. The interface only visualizes records returned by those
            services.
          </p>
        </div>
        <ol>
          <li>
            <strong>Source</strong>
            <span>Synthetic, time-stamped aggregate observations</span>
          </li>
          <li>
            <strong>Working software</strong>
            <span>Validated API, persisted records, detectors, and read-only workflows</span>
          </li>
          <li>
            <strong>Evidence, not decoration</strong>
            <span>Every count and chart is calculated from the returned replay</span>
          </li>
          <li>
            <strong>Decision to investigate</strong>
            <span>{priority ? priority.title : "No open incident was returned"}</span>
          </li>
        </ol>
      </section>
      <div className="two-column evidence-overview">
        <Panel
          title="Asset evidence map"
          detail="Issue markers use active incident counts. Asset placement is a review aid, not a surveyed plant layout."
        >
          <div className="asset-map" role="list" aria-label="Asset evidence map">
            {briefing.assets.map((asset) => (
              <article key={asset.assetId} role="listitem">
                <div className="asset-map-symbol">Asset</div>
                <div>
                  <strong>{asset.assetId}</strong>
                  <span>
                    {asset.activeIncidentCount
                      ? `${asset.activeIncidentCount} active incident${asset.activeIncidentCount === 1 ? "" : "s"}`
                      : "No active incident"}
                  </span>
                  <small>
                    {asset.observationCount.toLocaleString()} observations · {asset.flaggedCount.toLocaleString()} flagged
                  </small>
                </div>
              </article>
            ))}
          </div>
          <p className="chart-note">
            Table equivalent: each asset lists its returned observation, flagged-record, and active-incident counts.
          </p>
        </Panel>
        <Panel
          title="Evidence flow"
          detail="Counts move from received observations toward records that need human attention."
        >
          <ol className="evidence-flow">
            <li>
              <strong>{briefing.observationCount.toLocaleString()}</strong>
              <span>observations received</span>
            </li>
            <li>
              <strong>{briefing.flaggedCount.toLocaleString()}</strong>
              <span>quality-flagged records</span>
            </li>
            <li>
              <strong>{active.length}</strong>
              <span>open incident records</span>
            </li>
          </ol>
          <div className="flag-distribution" aria-label="Quality flag distribution">
            {briefing.quality.flagCounts.map((item) => (
              <div key={item.flag}>
                <span>{item.flag.replace(/[-_]/g, " ")}</span>
                <strong>{item.count.toLocaleString()}</strong>
              </div>
            ))}
          </div>
          <p className="chart-note">
            {qualityRate.toFixed(1)}% of returned observations carry at least one quality flag. Flags stay visible rather than being converted into a health score.
          </p>
        </Panel>
      </div>
      <VisualAnalytics briefing={briefing} onView={onView} />
      <div className="two-column">
        <Panel title="Recorded throughput" detail={recordSeriesDescription}>
          <div className="chart-summary">
            <strong>
              {number(production.currentValue)} <small>{production.unit}</small>
            </strong>
            {production.deltaVsBaseline !== null &&
              production.deltaVsBaseline !== undefined && (
                <span>
                  {production.deltaVsBaseline >= 0 ? "+" : ""}
                  {number(production.deltaVsBaseline, 1)} {production.unit} from
                  baseline
                </span>
              )}
          </div>
          <ThroughputChart briefing={briefing} />
          <p className="chart-note">
            This chart uses the returned replay points. Dashed line:{" "}
            {production.baselineValue === null ||
            production.baselineValue === undefined
              ? "baseline not returned"
              : `${number(production.baselineValue)} ${
                  production.unit
                } median of ${production.baselineSampleCount} clean records`}
            .
          </p>
        </Panel>
        <Panel
          title="What to review"
          detail="Work from the record, not a score."
        >
          <ol className="review-list">
            <li>
              <b>1</b>
              <span>
                <strong>Operating context</strong>
                <small>
                  The production series is an observed replay window, not a
                  forecast.
                </small>
              </span>
            </li>
            <li>
              <b>2</b>
              <span>
                <strong>Linked incident</strong>
                <small>
                  Open the priority record to see detector logic and source
                  observations.
                </small>
              </span>
            </li>
            <li>
              <b>3</b>
              <span>
                <strong>Data quality</strong>
                <small>
                  Check which records were flagged and why before interpreting
                  trends.
                </small>
              </span>
            </li>
          </ol>
        </Panel>
      </div>
      <Panel
        title="Replay coverage by asset"
        detail="Observation and quality counts are calculated from the returned replay—not estimated health scores."
      >
        <div className="asset-coverage">
          {briefing.assets.map((asset) => {
            const flaggedShare = asset.observationCount
              ? (asset.flaggedCount / asset.observationCount) * 100
              : 0;
            return (
              <article key={asset.assetId}>
                <header>
                  <strong>{asset.assetId}</strong>
                  <span>{asset.observationCount.toLocaleString()} records</span>
                </header>
                <div
                  className="quality-bar"
                  role="img"
                  aria-label={`${asset.flaggedCount.toLocaleString()} of ${asset.observationCount.toLocaleString()} records have a quality flag`}
                >
                  <span style={{ width: `${Math.min(flaggedShare, 100)}%` }} />
                </div>
                <footer>
                  <span>{asset.flaggedCount.toLocaleString()} flagged</span>
                  <span>{asset.activeIncidentCount} active incidents</span>
                  <span>Latest {time(asset.latestObservedAt)}</span>
                </footer>
              </article>
            );
          })}
        </div>
      </Panel>
      <Panel
        title="Open incident records"
        detail={`${active.length} records have not been resolved or dismissed.`}
        action={
          <button className="text-button" onClick={() => onView("incidents")}>
            All incident records
          </button>
        }
      >
        <div className="record-list">
          {active.length ? (
            active.slice(0, 4).map((incident) => (
              <button
                className="record-row"
                key={incident.id}
                onClick={() => onIncident(incident.id)}
              >
                <span>
                  <Pill value={incident.severity} />
                  <strong>{incident.title}</strong>
                  <small>
                    {incident.assetIds.join(", ")} · updated{" "}
                    {time(incident.updatedAt)}
                  </small>
                </span>
                <span aria-hidden="true">View</span>
              </button>
            ))
          ) : (
            <Empty title="No open incidents">
              There are no open records in the current replay.
            </Empty>
          )}
        </div>
      </Panel>
    </div>
  );
}
