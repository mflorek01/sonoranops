import type {
  Asset,
  AssistantEvidenceResult,
  AssistantToolName,
  DataTrust,
  Incident,
  IncidentDetail,
  OperationsApi,
  OperationsSummary,
  Severity,
  TimelineEntry,
  TransitionInput,
} from "./types";
import { demoApi } from "./demo";

const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
const demoEnabled = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

type ListResponse<T> = { items: T[]; next_cursor?: string | null };
type ApiAsset = { site_id: string; asset_id: string };
type ApiObservation = {
  observation_id: string;
  observed_at: string;
  source_recorded_at: string;
  asset_ref: ApiAsset;
  metric: string | null;
  value: number | null;
  quality_flags: string[];
};
type ApiIncident = {
  incident_id: string;
  status: Incident["state"];
  title: string;
  severity: "info" | "warning" | "critical";
  asset_refs: ApiAsset[];
  finding_ids: string[];
  opened_at: string;
  updated_at: string;
};
type ApiTimelineEntry = {
  timeline_entry_id: string;
  occurred_at: string;
  actor: string;
  prior_status: Incident["state"] | null;
  new_status: Incident["state"];
  reason: string | null;
};
type ApiIncidentDetail = ApiIncident & { timeline: ApiTimelineEntry[] };

const severityFor = (severity: ApiIncident["severity"]): Severity => {
  if (severity === "critical") return "critical";
  if (severity === "warning") return "medium";
  return "low";
};

const titleFor = (value: string) => value.replace(/[-_]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

const toIncident = (incident: ApiIncident): Incident => ({
  id: incident.incident_id,
  title: incident.title,
  state: incident.status,
  severity: severityFor(incident.severity),
  assetIds: incident.asset_refs.map((asset) => asset.asset_id),
  openedAt: incident.opened_at,
  updatedAt: incident.updated_at,
  summary: `${incident.finding_ids.length} linked platform finding${incident.finding_ids.length === 1 ? "" : "s"}.`,
  confidence: 0,
  evidenceCount: incident.finding_ids.length,
});

const toTimeline = (entry: ApiTimelineEntry): TimelineEntry => ({
  id: entry.timeline_entry_id,
  occurredAt: entry.occurred_at,
  kind: entry.prior_status ? "transition" : "created",
  actor: entry.actor,
  text: entry.prior_status
    ? `State changed from ${entry.prior_status} to ${entry.new_status}`
    : "Incident opened from platform findings.",
  reason: entry.reason ?? undefined,
});

const toIncidentDetail = (incident: ApiIncidentDetail): IncidentDetail => ({
  ...toIncident(incident),
  evidence: [],
  timeline: incident.timeline.map(toTimeline),
});

class HttpOperationsApi implements OperationsApi {
  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl}/api/v1${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { error?: { message?: string } } | null;
      throw new Error(body?.error?.message ?? `API request failed (${response.status})`);
    }
    return response.json() as Promise<T>;
  }

  private list<T>(path: string): Promise<ListResponse<T>> {
    return this.request<ListResponse<T>>(path);
  }

  async getSummary(): Promise<OperationsSummary> {
    const [incidents, observations] = await Promise.all([
      this.listIncidents(),
      this.list<ApiObservation>("/observations?limit=200"),
    ]);
    const latest = observations.items.at(-1);
    const throughput = [...observations.items]
      .reverse()
      .find((observation) => observation.metric === "throughput_tph" && observation.value !== null);
    const flagged = observations.items.filter((observation) => observation.quality_flags.length > 0).length;

    return {
      productionRate: throughput?.value ?? 0,
      productionDelta: 0,
      availability: observations.items.length ? 100 : 0,
      activeIncidents: incidents.filter((incident) => !["resolved", "dismissed"].includes(incident.state)).length,
      dataTrust: observations.items.length ? Math.max(0, 100 - Math.round((flagged / observations.items.length) * 100)) : 0,
      lastObservedAt: latest?.source_recorded_at ?? new Date(0).toISOString(),
    };
  }

  async listIncidents(): Promise<Incident[]> {
    const response = await this.list<ApiIncident>("/incidents");
    return response.items.map(toIncident);
  }

  async getIncident(id: string): Promise<IncidentDetail> {
    return toIncidentDetail(await this.request<ApiIncidentDetail>(`/incidents/${encodeURIComponent(id)}`));
  }

  async transitionIncident(id: string, input: TransitionInput): Promise<IncidentDetail> {
    const idempotencyKey = typeof crypto !== "undefined" ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    const response = await this.request<ApiIncidentDetail>(`/incidents/${encodeURIComponent(id)}/transitions`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ to_status: input.state, reason: input.reason, actor: "operator:web" }),
    });
    return toIncidentDetail(response);
  }

  async listAssets(): Promise<Asset[]> {
    const [assets, observations] = await Promise.all([
      this.list<ApiAsset>("/assets"),
      this.list<ApiObservation>("/observations?limit=200"),
    ]);
    const latestByAsset = new Map<string, ApiObservation>();
    for (const observation of observations.items) latestByAsset.set(observation.asset_ref.asset_id, observation);

    return assets.items.map((asset) => {
      const latest = latestByAsset.get(asset.asset_id);
      return {
        id: asset.asset_id,
        name: titleFor(asset.asset_id),
        area: asset.site_id,
        type: "Platform asset",
        health: latest?.quality_flags.length ? "attention" : "good",
        availability: latest ? 100 : 0,
        lastObservedAt: latest?.source_recorded_at ?? new Date(0).toISOString(),
      };
    });
  }

  async getDataTrust(): Promise<DataTrust> {
    const observations = await this.list<ApiObservation>("/observations?limit=200");
    const flagged = observations.items.filter((observation) => observation.quality_flags.length > 0).length;
    const score = observations.items.length ? Math.max(0, 100 - Math.round((flagged / observations.items.length) * 100)) : 0;
    const latest = observations.items.at(-1)?.source_recorded_at ?? new Date(0).toISOString();

    return {
      score,
      observedSources: observations.items.length ? 1 : 0,
      delayedSources: observations.items.some((observation) => observation.quality_flags.includes("late_arrival")) ? 1 : 0,
      schemaWarnings: observations.items.filter((observation) => observation.quality_flags.includes("invalid_unit")).length,
      lastEvaluatedAt: latest,
      feeds: [{
        name: "Platform observations",
        freshness: observations.items.length ? "Available" : "No observations",
        state: flagged ? "degraded" : "healthy",
        coverage: observations.items.length ? score : 0,
      }],
    };
  }

  async runAssistantTool(toolName: AssistantToolName, arguments_: Record<string, unknown>): Promise<AssistantEvidenceResult> {
    const response = await this.request<{ mode: "deterministic_evidence_tool"; tool_name: AssistantToolName; site_id: string; records: Array<Record<string, unknown>>; citations: Array<Record<string, unknown>>; uncertainty_notes: string[]; truncated: boolean }>(`/assistant/tools/${encodeURIComponent(toolName)}`, { method: "POST", body: JSON.stringify({ site_id: "sonoran-west", arguments: arguments_ }) });
    return { mode: response.mode, toolName: response.tool_name, siteId: response.site_id, records: response.records, citations: response.citations, uncertaintyNotes: response.uncertainty_notes, truncated: response.truncated };
  }
}

export const operationsApi: OperationsApi = demoEnabled ? demoApi : new HttpOperationsApi();
export const apiMode = demoEnabled ? "demo" : "live";
