import type {
  Incident,
  IncidentDetail,
  OperationsBriefing,
} from "../../lib/api/types";
import { assetLabel, Empty, metricLabel, number, Panel, Pill, pretty, time } from "./shared";

export function Incidents({
  incidents,
  onIncident,
}: {
  incidents: Incident[];
  onIncident: (id: string) => void;
}) {
  return (
    <Panel
      title="Issues"
      detail="Each issue connects an automated check to the readings that support it."
    >
      <div className="record-list">
        {incidents.map((incident) => (
          <button
            className="record-row"
            key={incident.id}
            onClick={() => onIncident(incident.id)}
          >
            <span>
              <Pill value={incident.severity} />
              <strong>{incident.title}</strong>
              <small>
                {assetLabel(incident.assetIds[0] ?? "unmapped")} · {incident.evidenceCount} automated checks
              </small>
            </span>
            <span>
              <Pill value={incident.state} />
            </span>
          </button>
        ))}
      </div>
    </Panel>
  );
}

export function IncidentRecord({
  incident,
  onBack,
}: {
  incident: IncidentDetail;
  onBack: () => void;
}) {
  return (
    <div className="view-stack">
      <button className="back" onClick={onBack}>
        Back to issues
      </button>
      <section className="record-hero">
        <p className="record-id">Issue record · {assetLabel(incident.assetIds[0] ?? "unmapped")}</p>
        <h2>{incident.title}</h2>
        <p>{incident.summary}</p>
        <div className="tag-row">
          <Pill value={incident.severity} />
          <Pill value={incident.state} />
          <span>Opened {time(incident.openedAt)}</span>
        </div>
        <details className="technical-details">
          <summary>Technical details</summary>
          <p>Issue ID: {incident.id}.</p>
        </details>
      </section>
      <div className="two-column">
        <Panel
          title="Why this issue was opened"
          detail="An automated check raised this issue. It is not a root-cause conclusion."
        >
          {incident.findings.length ? (
            <div className="finding-list">
              {incident.findings.map((finding) => (
                <article key={finding.id}>
                  <h3>{finding.rationale}</h3>
                  <p className="quiet">
                    Check period: {time(finding.windowStartAt)} to{" "}
                    {time(finding.windowEndAt)}
                  </p>
                  <details className="technical-details">
                    <summary>Technical details</summary>
                    <p>
                      Automated-check key: {finding.detector}
                      {finding.detectorVersion
                        ? `, version ${finding.detectorVersion}`
                        : ""}
                      . Check ID: {finding.id}.
                    </p>
                  </details>
                </article>
              ))}
            </div>
          ) : (
            <Empty title="No automated-check detail was returned">
              This issue remains useful for review history, but it cannot
              support a reading review until linked automated-check detail is
              available.
            </Empty>
          )}
        </Panel>
        <Panel title="Before acting" detail="Keep uncertainty visible.">
          <ul className="check-list">
            <li>Confirm the field condition and operating state.</li>
            <li>Review data warnings before comparing readings.</li>
            <li>
              Use the issue history as a record of decisions, not a
              substitute for a field check.
            </li>
          </ul>
          <p className="read-only-note">
            Public portfolio mode is read-only. The deployed application
            preserves the lifecycle contract, but this site does not permit
            changes.
          </p>
        </Panel>
      </div>
      <Panel
        title="Readings behind this issue"
        detail="Returned source readings. The app does not fill in missing evidence."
      >
        {incident.findings.some((finding) => finding.evidence.length) ? (
          <div className="evidence-table">
            <div className="evidence-head">
              <span>Reading time</span>
              <span>Signal</span>
              <span>Quality</span>
            </div>
            {incident.findings
              .flatMap((finding) => finding.evidence)
              .map((item) => (
                <div className="evidence-row" key={item.id}>
                  <span>
                    <strong>{time(item.observedAt)}</strong>
                    <small>
                      {item.source} · {item.id}
                    </small>
                  </span>
                  <span>
                    {item.metric
                      ? `${metricLabel(item.metric)}: ${number(item.value, 2)}${
                          item.unit ? ` ${item.unit}` : ""
                        }`
                      : "Metric not returned"}
                  </span>
                  <span>
                    {item.qualityFlags.length ? (
                      item.qualityFlags.map((flag) => (
                        <Pill key={flag} value={flag} />
                      ))
                    ) : (
                      <span className="plain-status">No data warnings</span>
                    )}
                  </span>
                </div>
              ))}
          </div>
        ) : (
          <Empty title="No linked readings were returned">
            The application does not infer missing evidence.
          </Empty>
        )}
      </Panel>
      <Panel
        title="Issue activity"
        detail="Append-only history returned by the API."
      >
        {incident.timeline.length ? (
          <ol className="activity-list">
            {incident.timeline.map((item) => (
              <li key={item.id}>
                <strong>{item.text}</strong>
                <span>
                  {item.actor} · {time(item.occurredAt)}
                </span>
                {item.reason && <p>{item.reason}</p>}
              </li>
            ))}
          </ol>
        ) : (
          <Empty title="No timeline entries were returned">
            Future lifecycle activity will be appended here.
          </Empty>
        )}
      </Panel>
    </div>
  );
}

export function Quality({ briefing }: { briefing: OperationsBriefing }) {
  const quality = briefing.quality;
  const clean = Math.max(0, briefing.observationCount - quality.flaggedCount);

  return (
    <div className="view-stack">
      <section className="quality-hero">
        <h2>
          {number(briefing.observationCount)} readings reviewed in this
          simulated shift
        </h2>
        <p>
          {number(clean)} arrived without a data warning.{" "}
          {number(quality.flaggedCount)} are retained with their warnings rather
          than hidden or corrected in the interface.
        </p>
      </section>
      <div className="two-column">
        <Panel
          title="Data warnings returned"
          detail="Counts describe this simulated shift, not a quality score."
        >
          {quality.flagCounts.length ? (
            <dl className="flag-list">
              {quality.flagCounts.map((item) => (
                <div key={item.flag}>
                  <dt>{pretty(item.flag)}</dt>
                  <dd>{number(item.count)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <Empty title="No data-warning categories were returned">
              No data-warning categories were supplied for this simulated shift.
            </Empty>
          )}
        </Panel>
        <Panel
          title="How the application treats them"
          detail="Data warnings are context, not a verdict."
        >
          <ul className="check-list">
            <li>Keep the original reading and source timestamp.</li>
            <li>Show the warning alongside the supporting reading.</li>
            <li>Leave the human decision and next check explicit.</li>
          </ul>
        </Panel>
      </div>
      <Panel
        title="Asset-level simulated-shift facts"
        detail="No inferred availability or health percentage."
      >
        <div className="asset-facts">
          {briefing.assets.map((asset) => (
            <article key={asset.assetId}>
              <h3>{assetLabel(asset.assetId)}</h3>
              <dl>
                <div>
                  <dt>Readings</dt>
                  <dd>{number(asset.observationCount)}</dd>
                </div>
                <div>
                  <dt>Flagged</dt>
                  <dd>{number(asset.flaggedCount)}</dd>
                </div>
                <div>
                  <dt>Open issues</dt>
                  <dd>{number(asset.activeIncidentCount)}</dd>
                </div>
              </dl>
              <small>Latest signal: {time(asset.latestObservedAt)}</small>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
