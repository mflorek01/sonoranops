export type IncidentState =
  | "open"
  | "acknowledged"
  | "investigating"
  | "mitigated"
  | "resolved"
  | "dismissed";
export type Severity = "critical" | "high" | "medium" | "low";

export interface Incident {
  id: string;
  title: string;
  sourceTitle?: string;
  state: IncidentState;
  severity: Severity;
  assetIds: string[];
  openedAt: string;
  updatedAt: string;
  summary: string;
  evidenceCount: number;
}

export interface LinkedObservation {
  id: string;
  observedAt: string;
  source: string;
  metric?: string;
  value?: number | null;
  unit?: string | null;
  qualityFlags: string[];
}

export interface Finding {
  id: string;
  detector: string;
  detectorVersion?: string;
  rationale: string;
  windowStartAt?: string;
  windowEndAt?: string;
  evidence: LinkedObservation[];
}

export interface TimelineEntry {
  id: string;
  occurredAt: string;
  kind: "created" | "transition" | "evidence";
  actor: string;
  text: string;
  reason?: string;
}

export interface IncidentDetail extends Incident {
  findings: Finding[];
  timeline: TimelineEntry[];
}

export interface OperationsBriefing {
  siteId: string;
  replay: {
    mode: string;
    observationTimeField: string;
    productionSeriesDefinition: string;
    windowStartAt?: string;
    windowEndAt?: string;
    calculationNote: string;
  };
  observationCount: number;
  flaggedCount: number;
  oldestObservedAt?: string;
  latestObservedAt?: string;
  production: {
    unit: string;
    currentValue?: number | null;
    baselineValue?: number | null;
    baselineSampleCount: number;
    deltaVsBaseline?: number | null;
    points: Array<{
      observationId: string;
      observedAt: string;
      value: number;
      qualityFlags: string[];
    }>;
  };
  quality: {
    flaggedCount: number;
    flagCounts: Array<{ flag: string; count: number }>;
  };
  assets: Array<{
    assetId: string;
    latestObservedAt?: string;
    observationCount: number;
    flaggedCount: number;
    activeIncidentCount: number;
  }>;
  visualAnalytics?: {
    metricSeries: Array<{
      assetId: string;
      metric: string;
      unit?: string;
      points: Array<{
        observedAt: string;
        value: number;
        qualityFlags: string[];
      }>;
    }>;
    observationKindCounts: Array<{ key: string; count: number }>;
    qualityFlagCountsByAsset: Array<{
      assetId: string;
      flag: string;
      count: number;
    }>;
    incidentCounts: Array<{
      assetId: string;
      severity: string;
      status: string;
      count: number;
    }>;
    processNodes: Array<{
      assetId: string;
      observationCount: number;
      latestObservedAt?: string;
      activeIncidentCount: number;
      flaggedObservationCount: number;
    }>;
    sensorStates?: Array<{
      assetId: string;
      metric: string;
      unit?: string;
      latestValue?: number | null;
      latestObservedAt?: string;
      latestQualityFlags: string[];
      flaggedObservationCount: number;
      observationCount: number;
      linkedActiveIncidentCount: number;
      linkedActiveIncidentHighestSeverity?: string;
      linkedFindingCount: number;
      state: "critical" | "attention" | "data_quality" | "no_issue" | "no_data";
      reason: string;
    }>;
  };
}

export interface TransitionInput {
  state: IncidentState;
  reason: string;
}
export type AssistantToolName =
  | "list_recent_incidents"
  | "get_incident_evidence"
  | "query_observations"
  | "list_recent_findings"
  | "compare_observation_periods";
export interface AssistantEvidenceResult {
  mode: "deterministic_evidence_tool";
  toolName: AssistantToolName;
  siteId: string;
  records: Array<Record<string, unknown>>;
  citations: Array<{
    objectId: string;
    objectType: string;
    timestamp?: string;
    startAt?: string;
    endAt?: string;
    assetId?: string;
    metric?: string;
    sourceId?: string;
    note?: string;
  }>;
  uncertaintyNotes: string[];
  truncated: boolean;
}

export interface AnalystCitation {
  label: string;
  objectId: string;
  objectType: string;
  note?: string;
  timestamp?: string;
}

export interface AnalystResponse {
  answer: string;
  mode?: string;
  citations: AnalystCitation[];
  uncertaintyNotes: string[];
  toolsUsed: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface OperationsApi {
  getBriefing(): Promise<OperationsBriefing>;
  listIncidents(): Promise<Incident[]>;
  getIncident(id: string): Promise<IncidentDetail>;
  transitionIncident(
    id: string,
    input: TransitionInput,
  ): Promise<IncidentDetail>;
  runAssistantTool(
    toolName: AssistantToolName,
    arguments_: Record<string, unknown>,
  ): Promise<AssistantEvidenceResult>;
  chat(messages: ChatMessage[]): Promise<AnalystResponse>;
}
