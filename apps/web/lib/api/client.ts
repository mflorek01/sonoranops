import type {
  AssistantEvidenceResult,
  AssistantToolName,
  AnalystResponse,
  ChatMessage,
  Finding,
  Incident,
  IncidentDetail,
  OperationsApi,
  OperationsBriefing,
  Severity,
  TimelineEntry,
  TransitionInput,
} from "./types";
import { demoApi } from "./demo";

const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
const rawBasePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const basePath =
  rawBasePath === "/"
    ? ""
    : `/${rawBasePath.replace(/^\/+|\/+$/g, "")}`.replace(/^\/$/, "");
const demoEnabled = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

type ListResponse<T> = { items: T[]; next_cursor?: string | null };
type ApiAsset = { site_id: string; asset_id: string };
type ApiObservation = {
  observation_id: string;
  observed_at: string;
  source_recorded_at?: string;
  source_id?: string;
  asset_ref: ApiAsset;
  metric?: string | null;
  value?: number | null;
  unit?: string | null;
  quality_flags?: string[];
};
type ApiFinding = {
  finding_id?: string;
  detector?: Record<string, string>;
  evaluated_window?: Record<string, string>;
  rationale?: string;
  evidence?: Array<Record<string, string>>;
};
type ApiIncident = {
  incident_id: string;
  status: Incident["state"];
  title: string;
  severity: "info" | "warning" | "critical";
  asset_refs: ApiAsset[];
  finding_ids?: string[];
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
type ApiIncidentDetail = ApiIncident & {
  timeline?: ApiTimelineEntry[];
  linked_findings?: ApiFinding[];
  linked_observations?: ApiObservation[];
};
type ApiBriefing = {
  site_id: string;
  replay_boundary: {
    mode: string;
    observation_time_field: string;
    production_series_definition: string;
    window_start_at?: string;
    window_end_at?: string;
    calculation_note: string;
  };
  observation_count: number;
  flagged_observation_count: number;
  oldest_observed_at?: string;
  latest_observed_at?: string;
  production: {
    series: Array<{
      observation_id: string;
      observed_at: string;
      value: number;
      unit?: string | null;
      quality_status?: string;
      quality_flags?: string[];
    }>;
    current?: { value: number; unit?: string | null } | null;
    baseline: {
      method: "median_of_clean_production_records";
      value?: number | null;
      sample_count: number;
    };
    delta_vs_baseline?: number | null;
  };
  data_quality_flag_counts: Array<{ flag: string; observation_count: number }>;
  assets: Array<{
    asset_id: string;
    latest_observed_at?: string;
    observation_count: number;
    flagged_observation_count: number;
    active_incident_count: number;
  }>;
  visual_analytics?: {
    metric_series: Array<{
      asset_id: string;
      metric: string;
      unit?: string | null;
      points: Array<{
        observed_at: string;
        value: number;
        quality_flags?: string[];
      }>;
    }>;
    observation_kind_counts: Array<{ key: string; count: number }>;
    quality_flag_counts_by_asset: Array<{
      asset_id: string;
      flag: string;
      observation_count: number;
    }>;
    incident_counts: Array<{
      asset_id: string;
      severity: string;
      status: string;
      count: number;
    }>;
    process_nodes: Array<{
      asset_id: string;
      observation_count: number;
      latest_observed_at?: string;
      active_incident_count: number;
      flagged_observation_count: number;
    }>;
    sensor_states?: Array<{
      asset_id: string;
      metric: string;
      unit?: string | null;
      latest_value?: number | null;
      latest_observed_at?: string;
      latest_quality_flags?: string[];
      flagged_observation_count: number;
      observation_count: number;
      linked_active_incident_count: number;
      linked_active_incident_highest_severity?: string | null;
      linked_finding_count: number;
      state: "critical" | "attention" | "data_quality" | "no_issue" | "no_data";
      reason: string;
    }>;
  };
};

const severityFor = (severity: ApiIncident["severity"]): Severity =>
  severity === "critical"
    ? "critical"
    : severity === "warning"
      ? "medium"
      : "low";
const toIncident = (incident: ApiIncident): Incident => ({
  id: incident.incident_id,
  title: incident.title,
  state: incident.status,
  severity: severityFor(incident.severity),
  assetIds: incident.asset_refs.map((asset) => asset.asset_id),
  openedAt: incident.opened_at,
  updatedAt: incident.updated_at,
  summary: `${incident.finding_ids?.length ?? 0} linked automated check${(incident.finding_ids?.length ?? 0) === 1 ? "" : "s"}.`,
  evidenceCount: incident.finding_ids?.length ?? 0,
});
const toObservation = (item: ApiObservation) => ({
  id: item.observation_id,
  observedAt: item.observed_at,
  source: item.source_id ?? item.asset_ref.asset_id,
  metric: item.metric ?? undefined,
  value: item.value,
  unit: item.unit,
  qualityFlags: item.quality_flags ?? [],
});
const toFinding = (finding: ApiFinding, index: number): Finding => ({
  id: finding.finding_id ?? `finding-${index + 1}`,
  detector:
    finding.detector?.name ??
    finding.detector?.detector_name ??
    "Platform detector",
  detectorVersion: finding.detector?.version,
  rationale:
    finding.rationale ??
    "The platform did not return a human-readable rationale.",
  windowStartAt:
    finding.evaluated_window?.start_at ?? finding.evaluated_window?.start,
  windowEndAt:
    finding.evaluated_window?.end_at ?? finding.evaluated_window?.end,
  evidence: [],
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
const toIncidentDetail = (incident: ApiIncidentDetail): IncidentDetail => {
  const findings = (incident.linked_findings ?? []).map(toFinding);
  const unattached = (incident.linked_observations ?? []).map(toObservation);
  if (unattached.length)
    findings.push({
      id: "linked-observations",
      detector: "Linked source observations",
      rationale: "Observations linked directly to this incident record.",
      evidence: unattached,
    });
  return {
    ...toIncident(incident),
    findings,
    timeline: (incident.timeline ?? []).map(toTimeline),
  };
};
const toBriefing = (data: ApiBriefing): OperationsBriefing => ({
  siteId: data.site_id,
  replay: {
    mode: data.replay_boundary.mode,
    observationTimeField: data.replay_boundary.observation_time_field,
    productionSeriesDefinition:
      data.replay_boundary.production_series_definition,
    windowStartAt: data.replay_boundary.window_start_at,
    windowEndAt: data.replay_boundary.window_end_at,
    calculationNote: data.replay_boundary.calculation_note,
  },
  observationCount: data.observation_count,
  flaggedCount: data.flagged_observation_count,
  oldestObservedAt: data.oldest_observed_at,
  latestObservedAt: data.latest_observed_at,
  production: {
    unit:
      data.production.current?.unit ??
      data.production.series.find((point) => point.unit)?.unit ??
      "TPH",
    currentValue: data.production.current?.value,
    baselineValue: data.production.baseline.value,
    baselineSampleCount: data.production.baseline.sample_count,
    deltaVsBaseline: data.production.delta_vs_baseline,
    points: data.production.series.map((point) => ({
      observationId: point.observation_id,
      observedAt: point.observed_at,
      value: point.value,
      qualityFlags: point.quality_flags ?? [],
    })),
  },
  quality: {
    flaggedCount: data.flagged_observation_count,
    flagCounts: data.data_quality_flag_counts.map((item) => ({
      flag: item.flag,
      count: item.observation_count,
    })),
  },
  assets: data.assets.map((asset) => ({
    assetId: asset.asset_id,
    latestObservedAt: asset.latest_observed_at,
    observationCount: asset.observation_count,
    flaggedCount: asset.flagged_observation_count,
    activeIncidentCount: asset.active_incident_count,
  })),
  visualAnalytics: data.visual_analytics
    ? {
        metricSeries: data.visual_analytics.metric_series.map((series) => ({
          assetId: series.asset_id,
          metric: series.metric,
          unit: series.unit ?? undefined,
          points: series.points.map((point) => ({
            observedAt: point.observed_at,
            value: point.value,
            qualityFlags: point.quality_flags ?? [],
          })),
        })),
        observationKindCounts: data.visual_analytics.observation_kind_counts,
        qualityFlagCountsByAsset: data.visual_analytics.quality_flag_counts_by_asset.map(
          (item) => ({
            assetId: item.asset_id,
            flag: item.flag,
            count: item.observation_count,
          }),
        ),
        incidentCounts: data.visual_analytics.incident_counts.map((item) => ({
          assetId: item.asset_id,
          severity: item.severity,
          status: item.status,
          count: item.count,
        })),
        processNodes: data.visual_analytics.process_nodes.map((item) => ({
          assetId: item.asset_id,
          observationCount: item.observation_count,
          latestObservedAt: item.latest_observed_at,
          activeIncidentCount: item.active_incident_count,
          flaggedObservationCount: item.flagged_observation_count,
        })),
        sensorStates: data.visual_analytics.sensor_states?.map((item) => ({
          assetId: item.asset_id,
          metric: item.metric,
          unit: item.unit ?? undefined,
          latestValue: item.latest_value,
          latestObservedAt: item.latest_observed_at,
          latestQualityFlags: item.latest_quality_flags ?? [],
          flaggedObservationCount: item.flagged_observation_count,
          observationCount: item.observation_count,
          linkedActiveIncidentCount: item.linked_active_incident_count,
          linkedActiveIncidentHighestSeverity:
            item.linked_active_incident_highest_severity ?? undefined,
          linkedFindingCount: item.linked_finding_count,
          state: item.state,
          reason: item.reason,
        })),
      }
    : undefined,
});

class HttpOperationsApi implements OperationsApi {
  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl || basePath}/api/v1${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as {
        error?: { message?: string };
      } | null;
      throw new Error(
        body?.error?.message ?? `API request failed (${response.status})`,
      );
    }
    return response.json() as Promise<T>;
  }
  private list<T>(path: string): Promise<ListResponse<T>> {
    return this.request<ListResponse<T>>(path);
  }
  async getBriefing(): Promise<OperationsBriefing> {
    return toBriefing(
      await this.request<ApiBriefing>(
        "/operations/briefing?site_id=sonoran-west",
      ),
    );
  }
  async listIncidents(): Promise<Incident[]> {
    return (await this.list<ApiIncident>("/incidents")).items.map(toIncident);
  }
  async getIncident(id: string): Promise<IncidentDetail> {
    return toIncidentDetail(
      await this.request<ApiIncidentDetail>(
        `/incidents/${encodeURIComponent(id)}`,
      ),
    );
  }
  async transitionIncident(
    id: string,
    input: TransitionInput,
  ): Promise<IncidentDetail> {
    const idempotencyKey =
      typeof crypto !== "undefined"
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random()}`;
    return toIncidentDetail(
      await this.request<ApiIncidentDetail>(
        `/incidents/${encodeURIComponent(id)}/transitions`,
        {
          method: "POST",
          headers: { "Idempotency-Key": idempotencyKey },
          body: JSON.stringify({
            to_status: input.state,
            reason: input.reason,
            actor: "operator:web",
          }),
        },
      ),
    );
  }
  async runAssistantTool(
    toolName: AssistantToolName,
    arguments_: Record<string, unknown>,
  ): Promise<AssistantEvidenceResult> {
    const response = await this.request<{
      mode: "deterministic_evidence_tool";
      tool_name: AssistantToolName;
      site_id: string;
      records: Array<Record<string, unknown>>;
      citations: Array<{
        object_id: string;
        object_type: string;
        timestamp?: string;
        start_at?: string;
        end_at?: string;
        asset_id?: string;
        metric?: string;
        source_id?: string;
        note?: string;
      }>;
      uncertainty_notes: string[];
      truncated: boolean;
    }>(`/assistant/tools/${encodeURIComponent(toolName)}`, {
      method: "POST",
      body: JSON.stringify({ site_id: "sonoran-west", arguments: arguments_ }),
    });
    return {
      mode: response.mode,
      toolName: response.tool_name,
      siteId: response.site_id,
      records: response.records,
      citations: response.citations.map((citation) => ({
        objectId: citation.object_id,
        objectType: citation.object_type,
        timestamp: citation.timestamp,
        startAt: citation.start_at,
        endAt: citation.end_at,
        assetId: citation.asset_id,
        metric: citation.metric,
        sourceId: citation.source_id,
        note: citation.note,
      })),
      uncertaintyNotes: response.uncertainty_notes,
      truncated: response.truncated,
    };
  }
  async chat(messages: ChatMessage[]): Promise<AnalystResponse> {
    const response = await this.request<{
      answer?: string;
      response?: string;
      mode?: string;
      citations?: Array<{
        label?: string;
        record_id?: string;
        record_type?: string;
        observed_at?: string;
        object_id?: string;
        object_type?: string;
        note?: string;
        timestamp?: string;
      }>;
      uncertainty_notes?: string[];
      uncertaintyNotes?: string[];
      tools_used?: string[];
    }>("/assistant/chat", {
      method: "POST",
      body: JSON.stringify({
        site_id: "sonoran-west",
        messages,
      }),
    });

    return {
      answer:
        response.answer ??
        response.response ??
        "The analyst returned no written response.",
      mode: response.mode,
      citations: (response.citations ?? []).map((citation, index) => ({
        label: citation.label ?? `Citation ${index + 1}`,
        objectId: citation.record_id ?? citation.object_id ?? `citation-${index + 1}`,
        objectType: citation.record_type ?? citation.object_type ?? "record",
        note: citation.note,
        timestamp: citation.observed_at ?? citation.timestamp,
      })),
      uncertaintyNotes: response.uncertainty_notes ?? response.uncertaintyNotes ?? [],
      toolsUsed: response.tools_used ?? [],
    };
  }
}
export const operationsApi: OperationsApi = demoEnabled
  ? demoApi
  : new HttpOperationsApi();
export const apiMode = demoEnabled ? "demo" : "live";
