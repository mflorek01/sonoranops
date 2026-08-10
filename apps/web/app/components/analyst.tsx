import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { operationsApi } from "../../lib/api/client";
import type { AnalystResponse, ChatMessage, Incident, OperationsBriefing } from "../../lib/api/types";
import { Empty, Panel, time } from "./shared";

interface TranscriptMessage extends ChatMessage {
  response?: AnalystResponse;
}

const starterQuestions = [
  "What needs attention in this simulated shift?",
  "What should I check next on the primary crusher?",
  "Which readings have data-quality limits?",
];

export function Analyst({
  briefing,
  incidents,
}: {
  briefing: OperationsBriefing;
  incidents: Incident[];
}) {
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string>();
  const [pending, setPending] = useState(false);
  const newestRef = useRef<HTMLDivElement>(null);
  const openIssues = incidents.filter(
    (incident) => incident.state !== "resolved" && incident.state !== "dismissed",
  ).length;

  useEffect(() => {
    newestRef.current?.scrollIntoView({ block: "start", behavior: "smooth" });
  }, [messages, pending]);

  const send = async () => {
    const content = draft.trim();
    if (!content || pending) return;

    const nextUser: TranscriptMessage = { role: "user", content };
    const nextMessages = [...messages, nextUser].slice(-8);
    setMessages(nextMessages);
    setDraft("");
    setError(undefined);
    setPending(true);

    try {
      const response = await operationsApi.chat(
        nextMessages.map(({ role, content: message }) => ({ role, content: message })),
      );
      setMessages((current) => [
        ...current,
        { role: "assistant" as const, content: response.answer, response },
      ].slice(-8));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "The AI analyst is unavailable right now.",
      );
    } finally {
      setPending(false);
    }
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void send();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  };

  return (
    <div className="view-stack analyst-page">
      <section className="analyst-hero">
        <div>
          <h2>Ask about this simulated shift</h2>
          <p>
            Ask in plain English. The analyst can explain the returned records, but it cannot change an issue, control equipment, or replace a field check.
          </p>
        </div>
        <dl className="analyst-context">
          <div><dt>Readings in this shift</dt><dd>{briefing.observationCount.toLocaleString()}</dd></div>
          <div><dt>Open issues</dt><dd>{openIssues}</dd></div>
          <div><dt>Latest reading</dt><dd>{time(briefing.latestObservedAt)}</dd></div>
        </dl>
      </section>
      <Panel
        title="AI analyst"
        detail="It uses the readings shown here. Check source details before acting."
        action={<button className="text-button" onClick={() => { setMessages([]); setDraft(""); setError(undefined); }}>New conversation</button>}
      >
        <div className="chat-transcript" aria-live="polite" aria-label="Analyst conversation">
          {messages.length ? messages.map((message, index) => (
            <div
              className={`chat-bubble chat-${message.role}`}
              key={`${message.role}-${index}-${message.content}`}
              ref={index === messages.length - 1 ? newestRef : undefined}
            >
              <span>{message.role === "user" ? "You" : "AI analyst"}</span>
              <p>{message.content}</p>
              {message.response && (
                <details className="chat-sources">
                  <summary>Sources and limits</summary>
                  {message.response.citations.length ? (
                    <ul>
                      {message.response.citations.map((citation) => (
                        <li key={`${citation.objectType}-${citation.objectId}`}>
                          <strong>{citation.label}</strong> · {citation.objectType}
                          {citation.timestamp ? ` · ${time(citation.timestamp)}` : ""}
                          {citation.note ? ` · ${citation.note}` : ""}
                        </li>
                      ))}
                    </ul>
                  ) : <p>No source citations were returned.</p>}
                  {message.response.uncertaintyNotes.length > 0 && (
                    <ul>{message.response.uncertaintyNotes.map((note) => <li key={note}>{note}</li>)}</ul>
                  )}
                </details>
              )}
            </div>
          )) : (
            <Empty title="Start with a question">
              The analyst uses earlier messages in this conversation to keep the discussion connected.
            </Empty>
          )}
          {pending && <div className="chat-bubble chat-assistant pending"><span>AI analyst</span><p><i /> <i /> <i /></p></div>}
          <div ref={newestRef} />
        </div>
        {error && <div className="error" role="alert"><strong>AI analyst unavailable</strong><span>{error}</span><p>You can still use the record lookup and issue views.</p></div>}
        <div className="starter-questions" aria-label="Suggested questions">
          {starterQuestions.map((question) => <button key={question} type="button" onClick={() => setDraft(question)}>{question}</button>)}
        </div>
        <form className="analyst-form" onSubmit={submit}>
          <label htmlFor="analyst-question">Your question</label>
          <textarea id="analyst-question" value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={onKeyDown} rows={3} placeholder="Ask about a reading, issue, or data-quality limit." />
          <div className="analyst-actions"><span>Enter to send · Shift+Enter for a new line</span><button className="primary" type="submit" disabled={pending || !draft.trim()}>Send</button></div>
        </form>
      </Panel>
    </div>
  );
}
