export type IncidentState = "open" | "acknowledged" | "investigating" | "mitigated" | "resolved" | "dismissed";
export type Severity = "critical" | "high" | "medium" | "low";

export interface Asset { id: string; name: string; area: string; type: string; health: "good" | "watch" | "attention"; availability: number; lastObservedAt: string; }
export interface Evidence { id: string; observedAt: string; source: string; title: string; detail: string; quality: "verified" | "review" | "degraded"; }
export interface TimelineEntry { id: string; occurredAt: string; kind: "created" | "transition" | "evidence"; actor: string; text: string; reason?: string; }
export interface Incident { id: string; title: string; state: IncidentState; severity: Severity; assetIds: string[]; openedAt: string; updatedAt: string; summary: string; confidence: number; evidenceCount: number; }
export interface IncidentDetail extends Incident { evidence: Evidence[]; timeline: TimelineEntry[]; }
export interface DataTrust { score: number; observedSources: number; delayedSources: number; schemaWarnings: number; lastEvaluatedAt: string; feeds: Array<{ name: string; freshness: string; state: "healthy" | "delayed" | "degraded"; coverage: number }>; }
export interface OperationsSummary { productionRate: number; productionDelta: number; availability: number; activeIncidents: number; dataTrust: number; lastObservedAt: string; }
export interface TransitionInput { state: IncidentState; reason: string; }
export type AssistantToolName = "list_recent_incidents" | "get_incident_evidence" | "query_observations" | "list_recent_findings" | "compare_observation_periods";
export interface AssistantEvidenceResult { mode: "deterministic_evidence_tool"; toolName: AssistantToolName; siteId: string; records: Array<Record<string, unknown>>; citations: Array<Record<string, unknown>>; uncertaintyNotes: string[]; truncated: boolean; }

export interface OperationsApi {
  getSummary(): Promise<OperationsSummary>;
  listIncidents(): Promise<Incident[]>;
  getIncident(id: string): Promise<IncidentDetail>;
  transitionIncident(id: string, input: TransitionInput): Promise<IncidentDetail>;
  listAssets(): Promise<Asset[]>;
  getDataTrust(): Promise<DataTrust>;
  runAssistantTool(toolName: AssistantToolName, arguments_: Record<string, unknown>): Promise<AssistantEvidenceResult>;
}
