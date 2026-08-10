import type { OperationsBriefing } from "../../lib/api/types";
import { metricLabel, number, Panel, pretty, time } from "./shared";

type AnalyticsView = "incidents" | "quality" | "explorer";

function Sparkline({
  points,
  label,
}: {
  points: Array<{ value: number; qualityFlags: string[] }>;
  label: string;
}) {
  if (!points.length) return null;

  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const coordinate = (point: { value: number }, index: number) => ({
    x: (index / Math.max(points.length - 1, 1)) * 100,
    y: 100 - ((point.value - min) / range) * 100,
  });
  const line = points.map((point, index) => {
    const { x, y } = coordinate(point, index);
    return `${x},${y}`;
  });

  return (
    <svg
      className="sparkline"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      role="img"
      aria-label={label}
    >
      <line x1="0" y1="50" x2="100" y2="50" />
      <polyline points={line.join(" ")} />
      {points.map((point, index) => {
        if (!point.qualityFlags.length) return null;
        const { x, y } = coordinate(point, index);
        return <circle key={index} cx={x} cy={y} r="2.5" />;
      })}
    </svg>
  );
}

function SeriesTable({
  series,
}: {
  series: NonNullable<OperationsBriefing["visualAnalytics"]>["metricSeries"][number];
}) {
  return (
    <details className="visual-table">
      <summary>Show returned points</summary>
      <table>
        <thead>
          <tr>
            <th>Observed</th>
            <th>Value</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {series.points.map((point) => (
            <tr key={`${point.observedAt}-${point.value}`}>
              <td>{time(point.observedAt)}</td>
              <td>{number(point.value, 2)}</td>
              <td>{point.qualityFlags.length ? point.qualityFlags.join(", ") : "None"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

export function VisualAnalytics({
  briefing,
  onView,
}: {
  briefing: OperationsBriefing;
  onView: (view: AnalyticsView) => void;
}) {
  const analytics = briefing.visualAnalytics;
  if (!analytics) return null;

  const kindTotal = analytics.observationKindCounts.reduce((total, item) => total + item.count, 0);
  const incidentTotal = analytics.incidentCounts.reduce((total, item) => total + item.count, 0);

  return (
    <section className="analytics-stack" aria-label="Returned visual analytics">
      <Panel
        title="Returned signal series"
        detail="Each small multiple is a bounded sequence returned by the API. Dots mark points with quality flags."
        action={<button className="text-button" onClick={() => onView("explorer")}>Inspect source evidence</button>}
      >
        {analytics.metricSeries.length ? (
          <div className="small-multiples">
            {analytics.metricSeries.slice(0, 6).map((series) => {
              const first = series.points[0];
              const last = series.points.at(-1);
              const flagged = series.points.filter((point) => point.qualityFlags.length).length;
              const label = `${metricLabel(series.metric)} for ${series.assetId}: ${series.points.length} returned observations from ${number(first?.value, 2)} to ${number(last?.value, 2)} ${series.unit ?? ""}. ${flagged} points carry quality flags.`;

              return (
                <article className="small-multiple" key={`${series.assetId}-${series.metric}`}>
                  <header>
                    <strong>{metricLabel(series.metric)}</strong>
                    <span>{series.unit ?? "Unit not returned"}</span>
                  </header>
                  <p>{series.assetId}</p>
                  <Sparkline points={series.points} label={label} />
                  <footer>
                    <span>{number(first?.value, 2)}</span>
                    <span>{number(last?.value, 2)}</span>
                    <span>{flagged} flagged</span>
                  </footer>
                  <SeriesTable series={series} />
                </article>
              );
            })}
          </div>
        ) : (
          <p className="quiet">No metric series were returned for this replay.</p>
        )}
      </Panel>
      <div className="two-column analytics-summary">
        <Panel
          title="Observation composition"
          detail="The horizontal bars are shares of the returned observation kinds."
        >
          {kindTotal ? (
            <div className="composition-list">
              {analytics.observationKindCounts.map((item) => (
                <div key={item.key}>
                  <div>
                    <span>{pretty(item.key)}</span>
                    <strong>{item.count.toLocaleString()}</strong>
                  </div>
                  <div
                    className="composition-bar"
                    role="img"
                    aria-label={`${pretty(item.key)}: ${item.count.toLocaleString()} of ${kindTotal.toLocaleString()} returned observations`}
                  >
                    <span style={{ width: `${(item.count / kindTotal) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="quiet">No observation-kind counts were returned.</p>
          )}
        </Panel>
        <Panel
          title="Incident distribution"
          detail="Grouped by returned asset, severity, and lifecycle status."
          action={<button className="text-button" onClick={() => onView("incidents")}>Open records</button>}
        >
          {incidentTotal ? (
            <div className="incident-distribution">
              {analytics.incidentCounts.map((item) => (
                <div key={`${item.assetId}-${item.severity}-${item.status}`}>
                  <strong>{item.count}</strong>
                  <span>{item.assetId}</span>
                  <small>{pretty(item.severity)} · {pretty(item.status)}</small>
                </div>
              ))}
            </div>
          ) : (
            <p className="quiet">No incident counts were returned.</p>
          )}
        </Panel>
      </div>
      <Panel
        title="Asset review sequence"
        detail="Nodes follow the API’s returned order. This is a review sequence, not a geographic plant map."
        action={<button className="text-button" onClick={() => onView("quality")}>Review quality detail</button>}
      >
        {analytics.processNodes.length ? (
          <ol className="process-strip">
            {analytics.processNodes.map((node, index) => {
              const assetFlags = analytics.qualityFlagCountsByAsset.filter(
                (item) => item.assetId === node.assetId,
              );
              const flagCount = assetFlags.reduce((total, item) => total + item.count, 0);
              return (
                <li key={node.assetId}>
                  <article>
                    <header>
                      <span>Step {index + 1}</span>
                      {node.activeIncidentCount > 0 && <strong>{node.activeIncidentCount} incident{node.activeIncidentCount === 1 ? "" : "s"}</strong>}
                    </header>
                    <h3>{node.assetId}</h3>
                    <dl>
                      <div><dt>Observations</dt><dd>{node.observationCount.toLocaleString()}</dd></div>
                      <div><dt>Flagged</dt><dd>{node.flaggedObservationCount.toLocaleString()}</dd></div>
                      <div><dt>Flag categories</dt><dd>{flagCount.toLocaleString()}</dd></div>
                    </dl>
                    <small>Latest {time(node.latestObservedAt)}</small>
                  </article>
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="quiet">No process nodes were returned.</p>
        )}
      </Panel>
    </section>
  );
}
