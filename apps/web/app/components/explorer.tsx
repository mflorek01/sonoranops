import { useState } from "react";
import { operationsApi } from "../../lib/api/client";
import type {
  AssistantEvidenceResult,
  AssistantToolName,
  Incident,
  OperationsBriefing,
} from "../../lib/api/types";
import { selectPriorityIncident } from "./incident-priority";
import { assetLabel, Empty, Loading, metricLabel, Panel, pretty, time } from "./shared";

function RecordSummary({ record }: { record: Record<string, unknown> }) {
  const title = typeof record.title === "string" ? record.title : undefined;
  const rationale = typeof record.rationale === "string" ? record.rationale : undefined;
  const assetId = typeof record.asset_id === "string" ? record.asset_id : undefined;
  const metric = typeof record.metric === "string" ? record.metric : undefined;
  const value = typeof record.value === "number" ? record.value : undefined;
  const when = typeof record.observed_at === "string" ? record.observed_at : undefined;
  const findings = Array.isArray(record.linked_findings) ? record.linked_findings.length : undefined;

  return (
    <article>
      <h3>{title ?? (rationale ? "Automated check" : metric ? "Reading" : "Returned record")}</h3>
      {rationale && <p><strong>What happened:</strong> {rationale}</p>}
      {assetId && <p><strong>Equipment:</strong> {assetLabel(assetId)}</p>}
      {metric && <p><strong>Reading:</strong> {metricLabel(metric)}{value === undefined ? " was not returned." : ` was ${value}.`}</p>}
      {when && <p><strong>Recorded at:</strong> {time(when)}</p>}
      {findings !== undefined && <p><strong>Why it was flagged:</strong> {findings ? `${findings} linked automated check${findings === 1 ? "" : "s"}.` : "No linked automated check was returned."}</p>}
      {!title && !rationale && !metric && <p>What this record is about was not returned.</p>}
      <details className="technical-details">
        <summary>Technical details</summary>
        <pre>{JSON.stringify(record, null, 2)}</pre>
      </details>
    </article>
  );
}

function Citation({
  citation,
}: {
  citation: AssistantEvidenceResult["citations"][number];
}) {
  const when = citation.timestamp
    ? time(citation.timestamp)
    : citation.startAt || citation.endAt
      ? `${time(citation.startAt)} to ${time(citation.endAt)}`
      : undefined;
  const details = [
    citation.objectType,
    citation.assetId,
    citation.metric,
    citation.sourceId,
    when,
    citation.note,
  ].filter(Boolean);

  return (
    <li>
      <strong>{citation.objectId}</strong>
      <span>{details.join(" · ")}</span>
    </li>
  );
}

export function EvidenceExplorer({ incidents }: { incidents: Incident[] }) {
  const [result, setResult] = useState<AssistantEvidenceResult>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  const priorityIncident = selectPriorityIncident(incidents);

  const run = async (
    tool: AssistantToolName,
    arguments_: Record<string, unknown> = {},
  ) => {
    setLoading(true);
    setError(undefined);

    try {
      setResult(await operationsApi.runAssistantTool(tool, arguments_));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Evidence query failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="view-stack">
      <section className="explorer-hero">
        <h2>Look up the records behind the screen</h2>
        <p>
          These lookups return source-backed readings. They do not diagnose a
          root cause, make a recommendation, or change equipment.
        </p>
        <div className="query-actions">
          <button
            className="primary"
            onClick={() => void run("list_recent_incidents", { limit: 10 })}
          >
            Open issues
          </button>
          <button
            onClick={() => void run("list_recent_findings", { limit: 10 })}
          >
            Recent automated checks
          </button>
          {priorityIncident && (
            <button
              onClick={() =>
                void run("get_incident_evidence", {
                  incident_id: priorityIncident.id,
                })
              }
            >
              Evidence for {priorityIncident.id}
            </button>
          )}
        </div>
      </section>
      {loading && <Loading label="Retrieving source records" />}
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {result && (
        <Panel
          title="Query result"
          detail={`${pretty(result.toolName)} · ${result.records.length} records returned from ${
            result.siteId
          }.`}
        >
          <div className="result-list">
            {result.records.length ? (
              result.records.map((record, index) => {
                return (
                  <RecordSummary key={index} record={record} />
                );
              })
            ) : (
              <Empty title="No records matched this query">
                Try another limited record lookup.
              </Empty>
            )}
          </div>
          <h3 className="citations-title">Citations</h3>
          {result.citations.length ? (
            <ul className="citation-list">
              {result.citations.map((citation) => (
                <Citation
                  key={`${citation.objectType}-${citation.objectId}`}
                  citation={citation}
                />
              ))}
            </ul>
          ) : (
            <p className="quiet">
              No citations were returned with this result.
            </p>
          )}
          {result.uncertaintyNotes.map((note) => (
            <p className="uncertainty" key={note}>
              Uncertainty: {note}
            </p>
          ))}
          {result.truncated && (
            <p className="uncertainty">
              The server truncated this result. Narrow the query for complete
              evidence.
            </p>
          )}
        </Panel>
      )}
    </div>
  );
}

export function HowItWorks({
  briefing,
  incidents,
}: {
  briefing: OperationsBriefing;
  incidents: Incident[];
}) {
  const linkedFindingCount = incidents.reduce(
    (total, incident) => total + incident.evidenceCount,
    0,
  );
  const activeIncidentCount = incidents.filter(
    (incident) => incident.state !== "resolved" && incident.state !== "dismissed",
  ).length;
  return (
    <div className="view-stack">
      <section className="how-hero">
        <h2>Evidence stays separate from a scenario&apos;s hidden answer.</h2>
        <p>
          A simulated aggregate-plant shift enters through the validated
          ingestion API. The platform receives readings, source timestamps,
          and data warnings—not the simulator’s private answer key.
        </p>
      </section>
      <section className="static-answer" aria-labelledby="static-answer-title">
        <div>
          <h2 id="static-answer-title">Are these static charts?</h2>
          <p>
            No. The browser fetches stored records through the deployed API and renders each count,
            sequence, and visual from that response. The simulated shift is intentionally frozen so
            the same evidence can be reviewed reproducibly.
          </p>
        </div>
        <ol className="boundary-pipeline" aria-label="Current record pipeline">
          <li><strong>{briefing.observationCount.toLocaleString()}</strong><span>stored readings</span></li>
          <li><strong>{linkedFindingCount.toLocaleString()}</strong><span>linked automated checks</span></li>
          <li><strong>{activeIncidentCount.toLocaleString()}</strong><span>open issues</span></li>
        </ol>
      </section>
      <section className="truth-table" aria-labelledby="truth-table-title">
        <h2 id="truth-table-title">What this demonstration claims</h2>
        <div>
          <article>
            <h3>Simulated</h3>
            <p>Aggregate-plant measurements, assets, site context, and simulated-shift timing are synthetic.</p>
          </article>
          <article>
            <h3>Real software</h3>
            <p>The app receives, stores, checks, and displays the records through a deployed database and service.</p>
          </article>
          <article>
            <h3>Not claimed</h3>
            <p>Live customer data, validated failure prediction, production control, or safety authority.</p>
          </article>
        </div>
      </section>
      <section className="boundary-summary" aria-labelledby="boundary-summary-title">
        <div>
          <h2 id="boundary-summary-title">What this public simulated shift contains</h2>
          <p>
            The interface is connected to a deployed application. The readings are simulated so
            the portfolio can demonstrate ingestion, auditability, and review without representing
            a live plant.
          </p>
        </div>
        <dl>
          <div>
            <dt>Stored readings</dt>
            <dd>{briefing.observationCount.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Readings with data warnings</dt>
            <dd>{briefing.flaggedCount.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Observation time field</dt>
            <dd>{briefing.replay.observationTimeField}</dd>
          </div>
        </dl>
      </section>
      <div className="architecture">
        <article>
          <b>1</b>
          <h3>Simulated shift data</h3>
          <p>
            Messy, time-stamped readings enter through the working data service.
          </p>
        </article>
        <article>
          <b>2</b>
          <h3>Automated checks and issues</h3>
          <p>
            Automated checks preserve their reason, check period, and linked
            source readings.
          </p>
        </article>
        <article>
          <b>3</b>
          <h3>Human review</h3>
          <p>
            The interface shows the facts, flags, uncertainty, and next human
            checks without manufacturing certainty.
          </p>
        </article>
      </div>
      <div className="two-column">
        <Panel
          title="Data boundary"
          detail="The public site is intentionally constrained."
        >
          <ul className="check-list">
            <li>The simulated shift supplies readings, timestamps, data warnings, and automated-check outputs.</li>
            <li>It does not provide a hidden scenario answer, control commands, or a root-cause label.</li>
            <li>Human review and field verification remain outside this portfolio deployment.</li>
          </ul>
        </Panel>
        <Panel title="Working glossary" detail="Terms used consistently throughout the application.">
          <dl className="glossary">
            <div>
              <dt>Observation</dt>
              <dd>A time-stamped source record retained as received.</dd>
            </div>
            <div>
              <dt>Finding</dt>
              <dd>An automated check with a reason and a check period.</dd>
            </div>
            <div>
              <dt>Incident</dt>
              <dd>A review record that links automated checks and its history.</dd>
            </div>
          </dl>
        </Panel>
      </div>
      <details className="technical-details">
        <summary>Technical details</summary>
        <p>The deployed application uses HTTP ingestion, a Postgres database, and APIs to receive, store, check, and return records.</p>
      </details>
      <Panel
        title="Scope of this public deployment"
        detail="A portfolio review environment, not a production control system."
      >
        <ul className="check-list">
          <li>
            Read-only access prevents public changes to incident lifecycle
            records.
          </li>
          <li>Record lookups are limited and show their sources.</li>
          <li>
            Live operational decisions still require site procedures and field
            verification.
          </li>
        </ul>
      </Panel>
    </div>
  );
}
