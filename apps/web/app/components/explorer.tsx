import { useState } from "react";
import { operationsApi } from "../../lib/api/client";
import type {
  AssistantEvidenceResult,
  AssistantToolName,
  Incident,
  OperationsBriefing,
} from "../../lib/api/types";
import { selectPriorityIncident } from "./incident-priority";
import { Empty, Loading, Panel, pretty, time } from "./shared";

function recordSummary(record: Record<string, unknown>) {
  if (Array.isArray(record.linked_findings) || Array.isArray(record.timeline)) {
    const findings = Array.isArray(record.linked_findings)
      ? record.linked_findings.length
      : 0;
    const timeline = Array.isArray(record.timeline)
      ? record.timeline.length
      : 0;

    return [
      record.title ? String(record.title) : "Incident evidence record",
      `${findings} linked finding${findings === 1 ? "" : "s"}`,
      `${timeline} timeline entr${timeline === 1 ? "y" : "ies"}`,
    ];
  }

  const keys = [
    "title",
    "rationale",
    "metric",
    "value",
    "asset_id",
    "incident_id",
    "id",
  ];
  return keys
    .filter((key) => record[key] !== undefined && record[key] !== null)
    .map((key) => `${pretty(key)}: ${String(record[key])}`);
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
        <h2>Bounded queries over the deployed record</h2>
        <p>
          These tools retrieve source-backed records. They do not diagnose a
          root cause, make a recommendation, or use a generative model.
        </p>
        <div className="query-actions">
          <button
            className="primary"
            onClick={() => void run("list_recent_incidents", { limit: 10 })}
          >
            Open incidents
          </button>
          <button
            onClick={() => void run("list_recent_findings", { limit: 10 })}
          >
            Recent findings
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
                const summary = recordSummary(record);
                return (
                  <article key={index}>
                    {summary.length ? (
                      summary.map((line) => <p key={line}>{line}</p>)
                    ) : (
                      <p>Record returned without a displayable summary.</p>
                    )}
                  </article>
                );
              })
            ) : (
              <Empty title="No records matched this query">
                Try an alternative bounded query.
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
          A synthetic aggregate-plant replay enters through the validated
          ingestion API. The platform receives observations, source timestamps,
          and quality flags—not scenario ground truth.
        </p>
      </section>
      <section className="static-answer" aria-labelledby="static-answer-title">
        <div>
          <h2 id="static-answer-title">Are these static charts?</h2>
          <p>
            No. The browser fetches stored records through the deployed API and renders each count,
            sequence, and visual from that response. The synthetic replay is intentionally frozen so
            the same evidence can be reviewed reproducibly.
          </p>
        </div>
        <ol className="boundary-pipeline" aria-label="Current record pipeline">
          <li><strong>{briefing.observationCount.toLocaleString()}</strong><span>stored observations</span></li>
          <li><strong>{linkedFindingCount.toLocaleString()}</strong><span>linked findings</span></li>
          <li><strong>{activeIncidentCount.toLocaleString()}</strong><span>open incidents</span></li>
        </ol>
      </section>
      <section className="truth-table" aria-labelledby="truth-table-title">
        <h2 id="truth-table-title">What this demonstration claims</h2>
        <div>
          <article>
            <h3>Simulated</h3>
            <p>Aggregate-plant measurements, assets, site context, and replay timing are synthetic.</p>
          </article>
          <article>
            <h3>Real software</h3>
            <p>HTTP ingestion, Postgres persistence, quality rules and detectors, APIs, UI workflows, and bounded AI tools.</p>
          </article>
          <article>
            <h3>Not claimed</h3>
            <p>Live Granite data, validated failure prediction, production control, or safety authority.</p>
          </article>
        </div>
      </section>
      <section className="boundary-summary" aria-labelledby="boundary-summary-title">
        <div>
          <h2 id="boundary-summary-title">What this public replay contains</h2>
          <p>
            The interface is connected to a deployed application. The observations are synthetic so
            the portfolio can demonstrate ingestion, auditability, and review without representing
            a live plant.
          </p>
        </div>
        <dl>
          <div>
            <dt>Stored observations</dt>
            <dd>{briefing.observationCount.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Quality-flagged records</dt>
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
          <h3>Replay data</h3>
          <p>
            Messy, time-stamped observations enter through the validated
            ingestion API.
          </p>
        </article>
        <article>
          <b>2</b>
          <h3>Findings and incidents</h3>
          <p>
            Detectors preserve their rationale, evaluation window, and linked
            source observations.
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
            <li>The replay supplies observations, timestamps, quality flags, and detector outputs.</li>
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
              <dd>A detector output with rationale and an evaluation window.</dd>
            </div>
            <div>
              <dt>Incident</dt>
              <dd>An auditable review record that links findings and lifecycle history.</dd>
            </div>
          </dl>
        </Panel>
      </div>
      <Panel
        title="Scope of this public deployment"
        detail="A portfolio review environment, not a production control system."
      >
        <ul className="check-list">
          <li>
            Read-only access prevents public changes to incident lifecycle
            records.
          </li>
          <li>Evidence explorer queries are bounded and cited.</li>
          <li>
            Live operational decisions still require site procedures and field
            verification.
          </li>
        </ul>
      </Panel>
    </div>
  );
}
