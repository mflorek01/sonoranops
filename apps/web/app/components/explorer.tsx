import { useState } from "react";
import { operationsApi } from "../../lib/api/client";
import type {
  AssistantEvidenceResult,
  AssistantToolName,
  Incident,
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

export function HowItWorks() {
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
