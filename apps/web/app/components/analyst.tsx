import { FormEvent, useState } from "react";
import { operationsApi } from "../../lib/api/client";
import type { AnalystResponse, Incident, OperationsBriefing } from "../../lib/api/types";
import { Empty, Loading, Panel, time } from "./shared";

const starterQuestions = [
  "What should an operations manager review first in this replay?",
  "Summarize the open incident records and their evidence limits.",
  "What data-quality issues should affect interpretation of recorded throughput?",
];

export function Analyst({
  briefing,
  incidents,
}: {
  briefing: OperationsBriefing;
  incidents: Incident[];
}) {
  const [question, setQuestion] = useState(starterQuestions[0]);
  const [result, setResult] = useState<AnalystResponse>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);

  const ask = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(undefined);

    try {
      setResult(await operationsApi.chat(trimmed));
    } catch (caught) {
      setResult(undefined);
      setError(
        caught instanceof Error
          ? caught.message
          : "The analyst service is unavailable right now.",
      );
    } finally {
      setLoading(false);
    }
  };

  const openCount = incidents.filter(
    (incident) => incident.state !== "resolved" && incident.state !== "dismissed",
  ).length;

  return (
    <div className="view-stack">
      <section className="analyst-hero">
        <div>
          <h2>Ask about the operating record</h2>
          <p>
            The analyst receives the public replay context and should distinguish evidence from
            inference. It cannot change records or make field decisions.
          </p>
        </div>
        <dl className="analyst-context">
          <div>
            <dt>Replay records</dt>
            <dd>{briefing.observationCount.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Open incidents</dt>
            <dd>{openCount}</dd>
          </div>
          <div>
            <dt>Latest signal</dt>
            <dd>{time(briefing.latestObservedAt)}</dd>
          </div>
        </dl>
      </section>
      <Panel
        title="AI analyst"
        detail="Responses should cite returned records and identify uncertainty."
      >
        <form className="analyst-form" onSubmit={ask}>
          <label htmlFor="analyst-question">Your question</label>
          <textarea
            id="analyst-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={4}
            placeholder="Ask about this replay, its incidents, or its data-quality context."
          />
          <div className="analyst-actions">
            <button className="primary" type="submit" disabled={loading || !question.trim()}>
              {loading ? "Reviewing records…" : "Ask analyst"}
            </button>
          </div>
        </form>
        <div className="starter-questions" aria-label="Suggested questions">
          {starterQuestions.map((starter) => (
            <button key={starter} type="button" onClick={() => setQuestion(starter)}>
              {starter}
            </button>
          ))}
        </div>
      </Panel>
      {loading && <Loading label="The analyst is reviewing the available record" />}
      {error && (
        <div className="error" role="alert">
          <strong>AI analyst unavailable</strong>
          <span>{error}</span>
          <p>
            You can still use the evidence explorer and incident records while the service is
            unavailable.
          </p>
        </div>
      )}
      {result && (
        <Panel
          title="Analyst response"
          detail={result.mode ? `Response mode: ${result.mode}` : "Response from the configured analyst service."}
        >
          <div className="analyst-answer">{result.answer}</div>
          {result.citations.length ? (
            <section className="analyst-citations" aria-labelledby="analyst-citations-title">
              <h3 id="analyst-citations-title">Returned citations</h3>
              <ul>
                {result.citations.map((citation) => (
                  <li key={`${citation.objectType}-${citation.objectId}`}>
                    <strong>{citation.label}</strong>
                    <span>
                      {citation.objectType} · {citation.objectId}
                      {citation.timestamp ? ` · ${time(citation.timestamp)}` : ""}
                      {citation.note ? ` · ${citation.note}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            <Empty title="No citations were returned">
              Treat this response as an orientation aid and inspect source records before acting.
            </Empty>
          )}
          {result.uncertaintyNotes.length > 0 && (
            <section className="analyst-uncertainty" aria-labelledby="analyst-uncertainty-title">
              <h3 id="analyst-uncertainty-title">Limits and uncertainty</h3>
              <ul>
                {result.uncertaintyNotes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </section>
          )}
          {result.toolsUsed.length > 0 && (
            <p className="quiet">Tools used: {result.toolsUsed.join(", ")}</p>
          )}
        </Panel>
      )}
    </div>
  );
}
