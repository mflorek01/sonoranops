import type {
  Incident,
  IncidentDetail,
  OperationsBriefing,
} from "../../lib/api/types";
import { Empty, number, Panel, Pill, pretty, time } from "./shared";

export function Incidents({
  incidents,
  onIncident,
}: {
  incidents: Incident[];
  onIncident: (id: string) => void;
}) {
  return (
    <Panel
      title="Incident records"
      detail="Each record is an auditable link between findings and the source data."
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
                {incident.id} · {incident.assetIds.join(", ")} ·{" "}
                {incident.evidenceCount} linked findings
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
        Back to incident records
      </button>
      <section className="record-hero">
        <p className="eyebrow">Incident {incident.id}</p>
        <h2>{incident.title}</h2>
        <p>{incident.summary}</p>
        <div className="tag-row">
          <Pill value={incident.severity} />
          <Pill value={incident.state} />
          <span>Opened {time(incident.openedAt)}</span>
        </div>
      </section>
      <div className="two-column">
        <Panel
          title="Why this record exists"
          detail="Detector output, not a root-cause conclusion."
        >
          {incident.findings.length ? (
            <div className="finding-list">
              {incident.findings.map((finding) => (
                <article key={finding.id}>
                  <p className="eyebrow">
                    {finding.detector}
                    {finding.detectorVersion
                      ? ` · version ${finding.detectorVersion}`
                      : ""}
                  </p>
                  <h3>{finding.rationale}</h3>
                  <p className="quiet">
                    Evaluation window: {time(finding.windowStartAt)} to{" "}
                    {time(finding.windowEndAt)}
                  </p>
                </article>
              ))}
            </div>
          ) : (
            <Empty title="No finding detail was returned">
              This record remains useful for lifecycle history, but it cannot
              support an evidence review until linked finding detail is
              available.
            </Empty>
          )}
        </Panel>
        <Panel title="Before acting" detail="Keep uncertainty visible.">
          <ul className="check-list">
            <li>Confirm the field condition and operating state.</li>
            <li>Review quality flags before comparing observations.</li>
            <li>
              Use the incident timeline as a record of decisions, not a
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
        title="Linked source observations"
        detail="Facts returned with the incident record."
      >
        {incident.findings.some((finding) => finding.evidence.length) ? (
          <div className="evidence-table">
            <div className="evidence-head">
              <span>Observation</span>
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
                      ? `${pretty(item.metric)}: ${number(item.value, 2)}${
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
                      <span className="plain-status">No quality flags</span>
                    )}
                  </span>
                </div>
              ))}
          </div>
        ) : (
          <Empty title="No linked observations were returned">
            The application does not infer missing evidence.
          </Empty>
        )}
      </Panel>
      <Panel
        title="Record activity"
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
        <p className="eyebrow">Data quality record</p>
        <h2>
          {number(briefing.observationCount)} observations evaluated in this
          replay
        </h2>
        <p>
          {number(clean)} arrived without a quality flag.{" "}
          {number(quality.flaggedCount)} are retained with their flags rather
          than hidden or corrected in the interface.
        </p>
      </section>
      <div className="two-column">
        <Panel
          title="Flags returned"
          detail="Counts describe the observed replay, not a quality score."
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
            <Empty title="No flag categories were returned">
              No quality categories were supplied for this replay.
            </Empty>
          )}
        </Panel>
        <Panel
          title="How the application treats them"
          detail="Quality flags are context, not a verdict."
        >
          <ul className="check-list">
            <li>Keep the original observation and source timestamp.</li>
            <li>Expose the flag alongside the evidence.</li>
            <li>Leave the human decision and next check explicit.</li>
          </ul>
        </Panel>
      </div>
      <Panel
        title="Asset-level replay facts"
        detail="No inferred availability or health percentage."
      >
        <div className="asset-facts">
          {briefing.assets.map((asset) => (
            <article key={asset.assetId}>
              <h3>{pretty(asset.assetId)}</h3>
              <dl>
                <div>
                  <dt>Observations</dt>
                  <dd>{number(asset.observationCount)}</dd>
                </div>
                <div>
                  <dt>Flagged</dt>
                  <dd>{number(asset.flaggedCount)}</dd>
                </div>
                <div>
                  <dt>Active incidents</dt>
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
