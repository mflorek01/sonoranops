import type { Incident, OperationsBriefing } from "../../lib/api/types";
import { VisualAnalytics } from "./analytics";
import { PlantDiagram } from "./plant-diagram";
import { selectPriorityIncident } from "./incident-priority";
import { assetLabel, Empty, number, Panel, Pill, time } from "./shared";

function ThroughputChart({ briefing }: { briefing: OperationsBriefing }) {
  const { points, baselineValue, unit } = briefing.production;

  if (!points.length) {
    return (
      <Empty title="No production record series was returned">
        The simulated shift returned run facts, but no chartable readings for this
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
            {priority?.title ?? "No open issues in this simulated shift"}
          </h2>
          <p>
            {priority?.summary ??
              "No issue needs review in this simulated shift."}
          </p>
          {priority && (
            <button className="primary" onClick={() => onIncident(priority.id)}>
              Review this issue
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
            <dt>Simulated shift</dt>
            <dd>
              {number(briefing.observationCount)} <small>records</small>
            </dd>
          </div>
          <div>
            <dt>Readings with data warnings</dt>
            <dd>
              {number(briefing.flaggedCount)} <small>need review</small>
            </dd>
          </div>
        </dl>
      </section>
      <PlantDiagram briefing={briefing} onView={onView} />
      <section className="demo-orientation" aria-labelledby="demo-orientation-title">
        <div>
          <h2 id="demo-orientation-title">What this screen demonstrates</h2>
          <p>
            A simulated shift runs through the same working software shown here. The app receives,
            stores, checks, and displays the readings.
          </p>
        </div>
        <ol>
          <li>
            <strong>Source</strong>
            <span>Simulated, time-stamped aggregate readings</span>
          </li>
          <li>
            <strong>Working software</strong>
            <span>Data service, stored readings, automated checks, and read-only review</span>
          </li>
          <li>
            <strong>Evidence, not decoration</strong>
            <span>Every count and chart is calculated from the returned shift</span>
          </li>
          <li>
            <strong>Decision to investigate</strong>
            <span>{priority ? priority.title : "No open issue was returned"}</span>
          </li>
        </ol>
      </section>
      <div className="two-column evidence-overview">
        <Panel
          title="Equipment summary"
          detail="Issue markers use open-issue counts. This is a review aid, not a surveyed plant layout."
        >
          <div className="asset-map" role="list" aria-label="Equipment summary">
            {briefing.assets.map((asset) => (
              <article key={asset.assetId} role="listitem">
                <div className="asset-map-symbol">Asset</div>
                <div>
                  <strong>{assetLabel(asset.assetId)}</strong>
                  <span>
                    {asset.activeIncidentCount
                      ? `${asset.activeIncidentCount} open issue${asset.activeIncidentCount === 1 ? "" : "s"}`
                      : "No open issue"}
                  </span>
                  <small>
                    {asset.observationCount.toLocaleString()} readings; {asset.flaggedCount.toLocaleString()} data warnings
                  </small>
                </div>
              </article>
            ))}
          </div>
          <p className="chart-note">
            Table equivalent: each asset lists its returned readings, data warnings, and open-issue counts.
          </p>
        </Panel>
        <Panel
          title="What the app checked"
          detail="The app narrows readings with data warnings into open issues for review."
        >
          <ol className="evidence-flow">
            <li>
              <strong>{briefing.observationCount.toLocaleString()}</strong>
              <span>readings received</span>
            </li>
            <li>
              <strong>{briefing.flaggedCount.toLocaleString()}</strong>
              <span>readings with data warnings</span>
            </li>
            <li>
              <strong>{active.length}</strong>
              <span>open issues</span>
            </li>
          </ol>
          <div className="flag-distribution" aria-label="Data warning distribution">
            {briefing.quality.flagCounts.map((item) => (
              <div key={item.flag}>
                <span>{item.flag.replace(/[-_]/g, " ")}</span>
                <strong>{item.count.toLocaleString()}</strong>
              </div>
            ))}
          </div>
          <p className="chart-note">
            {qualityRate.toFixed(1)}% of returned readings carry at least one data warning. Warnings stay visible rather than being converted into a health score.
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
            This chart uses returned shift readings. Dashed line:{" "}
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
                  The production series is a simulated shift record, not a
                  forecast.
                </small>
              </span>
            </li>
            <li>
              <b>2</b>
              <span>
                <strong>Linked issue</strong>
                <small>
                  Open the priority issue to see the automated-check reason
                  and source readings.
                </small>
              </span>
            </li>
            <li>
              <b>3</b>
              <span>
                <strong>Data quality</strong>
                <small>
                  Check which readings have data warnings and why before
                  interpreting trends.
                </small>
              </span>
            </li>
          </ol>
        </Panel>
      </div>
      <Panel
        title="Simulated-shift coverage by asset"
        detail="Reading and data-warning counts come from the returned simulated shift—not estimated health scores."
      >
        <div className="asset-coverage">
          {briefing.assets.map((asset) => {
            const flaggedShare = asset.observationCount
              ? (asset.flaggedCount / asset.observationCount) * 100
              : 0;
            return (
              <article key={asset.assetId}>
                <header>
                  <strong>{assetLabel(asset.assetId)}</strong>
                  <span>{asset.observationCount.toLocaleString()} readings</span>
                </header>
                <div
                  className="quality-bar"
                  role="img"
                  aria-label={`${asset.flaggedCount.toLocaleString()} of ${asset.observationCount.toLocaleString()} readings have data warnings`}
                >
                  <span style={{ width: `${Math.min(flaggedShare, 100)}%` }} />
                </div>
                <footer>
                  <span>{asset.flaggedCount.toLocaleString()} data warnings</span>
                  <span>{asset.activeIncidentCount} open issues</span>
                  <span>Latest {time(asset.latestObservedAt)}</span>
                </footer>
              </article>
            );
          })}
        </div>
      </Panel>
      <Panel
        title="Open issues"
        detail={`${active.length} issues still need a documented review.`}
        action={
          <button className="text-button" onClick={() => onView("incidents")}>
            All issues
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
                    {assetLabel(incident.assetIds[0] ?? "unmapped")}; updated{" "}
                    {time(incident.updatedAt)}
                  </small>
                </span>
                <span aria-hidden="true">View</span>
              </button>
            ))
          ) : (
            <Empty title="No open issues">
              There are no open issues in this simulated shift.
            </Empty>
          )}
        </div>
      </Panel>
    </div>
  );
}
