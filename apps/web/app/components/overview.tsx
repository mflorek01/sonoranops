import type { Incident, OperationsBriefing } from "../../lib/api/types";
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
  onView: (view: "incidents" | "quality") => void;
}) {
  const priority = selectPriorityIncident(incidents);
  const active = incidents.filter(
    (incident) =>
      incident !== undefined &&
      incident.state !== "resolved" &&
      incident.state !== "dismissed",
  );
  const production = briefing.production;
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
          <p className="eyebrow">Current operating story</p>
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
