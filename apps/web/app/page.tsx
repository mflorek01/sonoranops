"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiMode, operationsApi } from "../lib/api/client";
import type {
  Incident,
  IncidentDetail,
  OperationsBriefing,
} from "../lib/api/types";
import { EvidenceExplorer, HowItWorks } from "./components/explorer";
import { Analyst } from "./components/analyst";
import { selectPriorityIncident } from "./components/incident-priority";
import { Overview } from "./components/overview";
import { IncidentRecord, Incidents, Quality } from "./components/records";
import { Empty, Loading, time } from "./components/shared";

type View =
  | "overview"
  | "incidents"
  | "incident"
  | "quality"
  | "explorer"
  | "analyst"
  | "how";

type NavigationView = Exclude<View, "incident">;

interface Route {
  view: View;
  incidentId?: string;
  guideStep?: number;
}

const nav: Array<{ id: NavigationView; label: string }> = [
  { id: "overview", label: "Operations" },
  { id: "incidents", label: "Issues" },
  { id: "quality", label: "Data quality" },
  { id: "explorer", label: "Record lookup" },
  { id: "analyst", label: "AI analyst" },
  { id: "how", label: "How it works" },
];

const guide: Array<{ view: View; title: string; text: string }> = [
  {
    view: "overview",
    title: "Start with the operating story",
    text: "See this simulated shift, the production trend, and the first issue to review.",
  },
  {
    view: "incident",
    title: "Review an issue",
    text: "Open the automated check, check period, and source readings behind the issue.",
  },
  {
    view: "quality",
    title: "Check data quality in context",
    text: "Flags remain visible; the interface does not turn them into an opaque score.",
  },
  {
    view: "explorer",
    title: "Look up a record",
    text: "Look up returned readings and see the sources behind them.",
  },
  {
    view: "how",
    title: "Understand the system boundary",
    text: "The app receives simulated readings, not a hidden scenario answer.",
  },
];

const githubUrl = "https://github.com/mflorek01/sonoranops";

function isView(value: string | null): value is View {
  return (
    value !== null &&
    (value === "incident" || nav.some((item) => item.id === value))
  );
}

function parseRoute(): Route {
  const params = new URLSearchParams(window.location.search);
  const requestedView = params.get("view");
  const view = isView(requestedView) ? requestedView : "overview";
  const requestedStep = Number(params.get("step"));
  const guideStep =
    params.get("walkthrough") === "1" &&
    Number.isInteger(requestedStep) &&
    requestedStep >= 1 &&
    requestedStep <= guide.length
      ? requestedStep
      : undefined;

  return {
    view,
    incidentId: params.get("incident") || undefined,
    guideStep,
  };
}

function writeRoute(route: Route, replace = false) {
  const url = new URL(window.location.href);
  url.searchParams.set("view", route.view);

  if (route.incidentId) {
    url.searchParams.set("incident", route.incidentId);
  } else {
    url.searchParams.delete("incident");
  }

  if (route.guideStep) {
    url.searchParams.set("walkthrough", "1");
    url.searchParams.set("step", String(route.guideStep));
  } else {
    url.searchParams.delete("walkthrough");
    url.searchParams.delete("step");
  }

  window.history[replace ? "replaceState" : "pushState"]({}, "", url);
}

function ErrorNotice({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action: React.ReactNode;
}) {
  return (
    <div className="error" role="alert">
      <strong>{title}</strong>
      <span>{detail}</span>
      {action}
    </div>
  );
}

export default function Workspace() {
  const [view, setViewState] = useState<View>("overview");
  const [briefing, setBriefing] = useState<OperationsBriefing>();
  const [incidents, setIncidents] = useState<Incident[]>();
  const [selected, setSelected] = useState<IncidentDetail>();
  const [activeIncidentId, setActiveIncidentId] = useState<string>();
  const [dataError, setDataError] = useState<string>();
  const [incidentError, setIncidentError] = useState<string>();
  const [guideStep, setGuideStep] = useState<number>();
  const incidentRequest = useRef(0);

  const refresh = useCallback(async () => {
    setDataError(undefined);

    try {
      const [nextBriefing, nextIncidents] = await Promise.all([
        operationsApi.getBriefing(),
        operationsApi.listIncidents(),
      ]);
      setBriefing(nextBriefing);
      setIncidents(nextIncidents);
    } catch (caught) {
      setDataError(
        caught instanceof Error
          ? caught.message
          : "The deployed app did not return the current shift.",
      );
    }
  }, []);

  const cancelIncidentLoad = useCallback(() => {
    incidentRequest.current += 1;
    setActiveIncidentId(undefined);
    setSelected(undefined);
    setIncidentError(undefined);
  }, []);

  const loadIncident = useCallback(async (id: string) => {
    const requestId = incidentRequest.current + 1;
    incidentRequest.current = requestId;
    setActiveIncidentId(id);
    setSelected(undefined);
    setIncidentError(undefined);

    try {
      const nextIncident = await operationsApi.getIncident(id);
      if (incidentRequest.current === requestId) {
        setSelected(nextIncident);
      }
    } catch (caught) {
      if (incidentRequest.current === requestId) {
        setIncidentError(
          caught instanceof Error
            ? caught.message
            : "The requested issue is unavailable.",
        );
      }
    }
  }, []);

  const restoreRoute = useCallback(
    (route: Route) => {
      setViewState(route.view);
      setGuideStep(route.guideStep);

      if (route.incidentId) {
        void loadIncident(route.incidentId);
      } else {
        cancelIncidentLoad();
      }
    },
    [cancelIncidentLoad, loadIncident],
  );

  const navigateToRoute = useCallback(
    (route: Route, replace = false) => {
      writeRoute(route, replace);
      restoreRoute(route);
    },
    [restoreRoute],
  );

  useEffect(() => {
    const restoreFromAddress = () => restoreRoute(parseRoute());
    restoreFromAddress();
    window.addEventListener("popstate", restoreFromAddress);
    void refresh();

    return () => window.removeEventListener("popstate", restoreFromAddress);
  }, [refresh, restoreRoute]);

  const navigate = (next: NavigationView) => {
    navigateToRoute({ view: next });
  };

  const chooseIncident = (id: string, step = guideStep) => {
    navigateToRoute({ view: "incident", incidentId: id, guideStep: step });
  };

  const startGuide = () => {
    navigateToRoute({ view: "overview", guideStep: 1 });
  };

  const moveGuide = (direction: 1 | -1) => {
    const nextStep = (guideStep ?? 1) + direction;

    if (nextStep < 1) {
      return;
    }

    if (nextStep > guide.length) {
      navigateToRoute({ view, incidentId: activeIncidentId });
      return;
    }

    const target = guide[nextStep - 1];
    if (target.view === "incident") {
      const priority = incidents
        ? selectPriorityIncident(incidents)
        : undefined;
      navigateToRoute({
        view: "incident",
        incidentId: priority?.id,
        guideStep: nextStep,
      });
      return;
    }

    navigateToRoute({ view: target.view, guideStep: nextStep });
  };

  const exitGuide = () => {
    navigateToRoute({ view, incidentId: activeIncidentId });
  };

  const retryIncident = () => {
    if (activeIncidentId) {
      void loadIncident(activeIncidentId);
    }
  };

  const displayTitle =
    nav.find((item) => item.id === view)?.label ?? "Issue";
  const noData = !briefing || !incidents;

  return (
    <main className="app-shell">
      <a className="skip" href="#content">
        Skip to content
      </a>
      <aside className="site-rail">
        <a className="brand" href="?view=overview">
          <span>SO</span>
          <strong>
            Sonoran Ops
            <small>Operations intelligence</small>
          </strong>
        </a>
        <nav aria-label="Primary navigation">
          {nav.map((item) => (
            <button
              key={item.id}
              aria-current={view === item.id ? "page" : undefined}
              className={view === item.id ? "active" : ""}
              onClick={() => navigate(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="rail-footer">
          <a href={githubUrl} target="_blank" rel="noreferrer">
            View the repository
          </a>
          <span>{apiMode === "demo" ? "Local sample" : "Deployed application"}</span>
        </div>
      </aside>
      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="topbar-status">Simulated aggregate-plant shift</p>
            <h1>{displayTitle}</h1>
          </div>
          <button className="refresh" onClick={() => void refresh()}>
            Refresh records
          </button>
        </header>
        <div className="portfolio-banner" role="status">
          <strong>Portfolio demonstration</strong>
          <span>
            Simulated aggregate-plant data is feeding a real deployed
            application. The platform never receives a hidden scenario answer.
          </span>
          <button className="text-button" onClick={() => navigate("how")}>
            How this works
          </button>
        </div>
        <section className="walkthrough-intro">
          <div>
            <strong>3-minute walkthrough</strong>
            <span>
              Follow the top issue from the plant view to its readings, data
              checks, and next step.
            </span>
          </div>
          <div>
            <button className="primary" onClick={startGuide}>
              Start walkthrough
            </button>
            <button onClick={exitGuide}>Explore freely</button>
            <a href={githubUrl} target="_blank" rel="noreferrer">
              GitHub
            </a>
          </div>
        </section>
        {guideStep && (
          <aside className="guide" aria-label="3-minute walkthrough">
            <p>
              Step {guideStep} of {guide.length}
            </p>
            <div>
              <strong>{guide[guideStep - 1].title}</strong>
              <span>{guide[guideStep - 1].text}</span>
            </div>
            <div className="guide-actions">
              <button onClick={() => moveGuide(-1)} disabled={guideStep === 1}>
                Back
              </button>
              <button className="primary" onClick={() => moveGuide(1)}>
                {guideStep === guide.length ? "Finish" : "Next"}
              </button>
              <button className="text-button" onClick={exitGuide}>
                Exit
              </button>
            </div>
          </aside>
        )}
        <div id="content" className="content">
          {dataError && (
            <ErrorNotice
              title="Unable to refresh the simulated shift."
              detail={dataError}
              action={<button onClick={() => void refresh()}>Try again</button>}
            />
          )}
          {noData ? (
            dataError ? null : (
              <Loading />
            )
          ) : (
            <>
              {view === "overview" && (
                <Overview
                  briefing={briefing}
                  incidents={incidents}
                  onIncident={chooseIncident}
                  onView={navigate}
                />
              )}
              {view === "incidents" && (
                <Incidents incidents={incidents} onIncident={chooseIncident} />
              )}
              {view === "incident" &&
                (selected ? (
                  <IncidentRecord
                    incident={selected}
                    onBack={() => navigate("incidents")}
                  />
                ) : incidentError ? (
                  <ErrorNotice
                    title="Unable to load this issue."
                    detail={incidentError}
                    action={<button onClick={retryIncident}>Try again</button>}
                  />
                ) : activeIncidentId ? (
                  <Loading label="Loading the issue" />
                ) : (
                  <Empty title="No issue was selected">
                    Select an open issue from the operations overview or
                    issues list.
                  </Empty>
                ))}
              {view === "quality" && <Quality briefing={briefing} />}
              {view === "explorer" && (
                <EvidenceExplorer incidents={incidents} />
              )}
              {view === "analyst" && (
                <Analyst briefing={briefing} incidents={incidents} />
              )}
              {view === "how" && <HowItWorks briefing={briefing} incidents={incidents} />}
            </>
          )}
        </div>
        <footer>
          Simulated shift: {briefing?.replay.mode ?? "Loading"} · latest
          reading {time(briefing?.latestObservedAt)}
        </footer>
      </section>
    </main>
  );
}
