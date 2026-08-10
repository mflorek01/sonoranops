import type {
  AssistantEvidenceResult,
  AssistantToolName,
  IncidentDetail,
  OperationsApi,
  OperationsBriefing,
  TransitionInput,
} from "./types";

const delay = <T>(value: T) =>
  new Promise<T>((resolve) => setTimeout(() => resolve(value), 180));
const now = "2026-08-08T17:49:00Z";
const metricPoints = (
  values: number[],
  unit: string,
  flaggedIndexes: number[] = [],
) =>
  values.map((value, index) => ({
    observedAt: `2026-08-08T${String(15 + Math.floor((index * 5 + 4) / 60)).padStart(2, "0")}:${String((index * 5 + 4) % 60).padStart(2, "0")}:00Z`,
    value,
    unit,
    qualityFlags: flaggedIndexes.includes(index) ? ["outside_expected_range"] : [],
  }));
let incidents: IncidentDetail[] = [
  {
    id: "inc-2048",
    title: "Crusher drive vibration above operating envelope",
    state: "investigating",
    severity: "critical",
    assetIds: ["primary-crusher-01"],
    openedAt: "2026-08-08T13:14:00Z",
    updatedAt: "2026-08-08T17:31:00Z",
    summary:
      "Repeated high axial vibration during loaded cycles. Review the linked records before making a maintenance decision.",
    evidenceCount: 3,
    findings: [
      {
        id: "find-101",
        detector: "vibration-envelope",
        detectorVersion: "1.2",
        rationale:
          "Three axial-vibration observations exceeded the configured review threshold during loaded operation.",
        windowStartAt: "2026-08-08T15:09:00Z",
        windowEndAt: "2026-08-08T17:28:00Z",
        evidence: [
          {
            id: "obs-1",
            observedAt: "2026-08-08T17:28:00Z",
            source: "condition-monitor",
            metric: "axial_vibration",
            value: 12.8,
            unit: "mm/s",
            qualityFlags: [],
          },
          {
            id: "obs-2",
            observedAt: "2026-08-08T16:42:00Z",
            source: "condition-monitor",
            metric: "axial_vibration",
            value: 12.1,
            unit: "mm/s",
            qualityFlags: [],
          },
        ],
      },
    ],
    timeline: [
      {
        id: "tl-1",
        occurredAt: "2026-08-08T13:14:00Z",
        kind: "created",
        actor: "Detection service",
        text: "Incident opened from correlated condition findings.",
      },
      {
        id: "tl-2",
        occurredAt: "2026-08-08T15:21:00Z",
        kind: "transition",
        actor: "J. Rivera",
        text: "State changed to acknowledged",
        reason: "Confirmed trend and assigned field inspection.",
      },
    ],
  },
  {
    id: "inc-2044",
    title: "Conveyor 17 throughput variance",
    state: "acknowledged",
    severity: "high",
    assetIds: ["conveyor-17"],
    openedAt: "2026-08-08T10:06:00Z",
    updatedAt: "2026-08-08T16:10:00Z",
    summary:
      "Measured flow intermittently diverges from expected line balance.",
    evidenceCount: 2,
    findings: [],
    timeline: [],
  },
];

const briefing: OperationsBriefing = {
  siteId: "sonoran-west",
  replay: {
    mode: "synthetic replay",
    observationTimeField: "observed_at",
    productionSeriesDefinition:
      "Clean recorded throughput observations in the returned replay window",
    windowStartAt: "2026-08-08T15:49:00Z",
    windowEndAt: now,
    calculationNote:
      "The server calculates the baseline from clean production records only.",
  },
  observationCount: 1524,
  flaggedCount: 61,
  oldestObservedAt: "2026-08-08T08:00:00Z",
  latestObservedAt: now,
  production: {
    unit: "TPH",
    currentValue: 842,
    baselineValue: 790,
    baselineSampleCount: 11,
    deltaVsBaseline: 52,
    points: [710, 730, 722, 761, 750, 781, 773, 808, 796, 825, 814, 842].map(
      (value, index) => ({
        observationId: `feed-${index + 1}`,
        observedAt: `2026-08-08T${String(15 + Math.floor((index + 49) / 60)).padStart(2, "0")}:${String((index * 10 + 49) % 60).padStart(2, "0")}:00Z`,
        value,
        qualityFlags: index === 3 ? ["late_arrival"] : [],
      }),
    ),
  },
  quality: {
    flaggedCount: 61,
    flagCounts: [
      { flag: "late_arrival", count: 35 },
      { flag: "outside_expected_range", count: 19 },
      { flag: "missing_value", count: 7 },
    ],
  },
  assets: [
    {
      assetId: "primary-crusher-01",
      latestObservedAt: now,
      observationCount: 510,
      flaggedCount: 30,
      activeIncidentCount: 1,
    },
    {
      assetId: "conveyor-17",
      latestObservedAt: now,
      observationCount: 503,
      flaggedCount: 22,
      activeIncidentCount: 1,
    },
    {
      assetId: "wash-plant-02",
      latestObservedAt: now,
      observationCount: 511,
      flaggedCount: 9,
      activeIncidentCount: 0,
    },
  ],
  visualAnalytics: {
    metricSeries: [
      {
        assetId: "primary-crusher-01",
        metric: "axial_vibration",
        unit: "mm/s",
        points: metricPoints([7.1, 7.3, 7.2, 8.4, 9.1, 10.8, 12.1, 12.8], "mm/s", [5, 6, 7]),
      },
      {
        assetId: "primary-crusher-01",
        metric: "motor_current",
        unit: "A",
        points: metricPoints([182, 188, 191, 194, 201, 208, 213, 216], "A"),
      },
      {
        assetId: "conveyor-17",
        metric: "belt_speed",
        unit: "m/s",
        points: metricPoints([3.2, 3.1, 3.0, 2.7, 2.8, 3.0, 3.2, 3.1], "m/s", [3]),
      },
      {
        assetId: "wash-plant-02",
        metric: "water_flow",
        unit: "L/min",
        points: metricPoints([410, 414, 412, 418, 421, 416, 419, 423], "L/min"),
      },
    ],
    observationKindCounts: [
      { key: "condition_record", count: 550 },
      { key: "production_record", count: 530 },
      { key: "quality_record", count: 444 },
    ],
    qualityFlagCountsByAsset: [
      { assetId: "primary-crusher-01", flag: "outside_expected_range", count: 19 },
      { assetId: "primary-crusher-01", flag: "late_arrival", count: 11 },
      { assetId: "conveyor-17", flag: "late_arrival", count: 22 },
      { assetId: "wash-plant-02", flag: "missing_value", count: 9 },
    ],
    incidentCounts: [
      { assetId: "primary-crusher-01", severity: "critical", status: "investigating", count: 1 },
      { assetId: "conveyor-17", severity: "high", status: "acknowledged", count: 1 },
    ],
    processNodes: [
      { assetId: "primary-crusher-01", observationCount: 510, latestObservedAt: now, activeIncidentCount: 1, flaggedObservationCount: 30 },
      { assetId: "conveyor-17", observationCount: 503, latestObservedAt: now, activeIncidentCount: 1, flaggedObservationCount: 22 },
      { assetId: "wash-plant-02", observationCount: 511, latestObservedAt: now, activeIncidentCount: 0, flaggedObservationCount: 9 },
    ],
  },
};

export const demoApi: OperationsApi = {
  getBriefing: () => delay(briefing),
  listIncidents: () =>
    delay(incidents.map(({ findings, timeline, ...incident }) => incident)),
  getIncident: async (id) => {
    const incident = incidents.find((item) => item.id === id);
    if (!incident) throw new Error("Incident not found");
    return delay(incident);
  },
  transitionIncident: async (id, input: TransitionInput) => {
    if (!input.reason.trim())
      throw new Error("A reason is required for lifecycle changes.");
    const index = incidents.findIndex((item) => item.id === id);
    if (index < 0) throw new Error("Incident not found");
    const prior = incidents[index];
    const at = new Date().toISOString();
    incidents[index] = {
      ...prior,
      state: input.state,
      updatedAt: at,
      timeline: [
        ...prior.timeline,
        {
          id: `tl-${at}`,
          occurredAt: at,
          kind: "transition",
          actor: "Demo operator",
          text: `State changed to ${input.state}`,
          reason: input.reason,
        },
      ],
    };
    return delay(incidents[index]);
  },
  runAssistantTool: async (
    toolName: AssistantToolName,
    arguments_: Record<string, unknown>,
  ): Promise<AssistantEvidenceResult> => {
    const incidentId =
      typeof arguments_.incident_id === "string"
        ? arguments_.incident_id
        : undefined;
    const assetId =
      typeof arguments_.asset_id === "string" ? arguments_.asset_id : undefined;
    const selected = incidentId
      ? incidents.filter((item) => item.id === incidentId)
      : assetId
        ? incidents.filter((item) => item.assetIds.includes(assetId))
        : incidents;
    const records: Array<Record<string, unknown>> =
      toolName === "get_incident_evidence"
        ? selected.flatMap((item) =>
            item.findings.flatMap((finding) =>
              finding.evidence.map((evidence) => ({ ...evidence })),
            ),
          )
        : toolName === "list_recent_findings"
          ? selected.flatMap((item) =>
              item.findings.map((finding) => ({ ...finding })),
            )
          : selected.map(({ findings, timeline, ...item }) => ({ ...item }));
    return delay({
      mode: "deterministic_evidence_tool",
      toolName,
      siteId: "sonoran-west",
      records,
      citations: records.map((record, index) => ({
        objectId: String(record.id ?? `local-${index + 1}`),
        objectType: toolName,
        sourceId: "local-demo-adapter",
        timestamp: String(record.observedAt ?? record.updatedAt ?? now),
        assetId,
        note: "Local demo adapter record.",
      })),
      uncertaintyNotes: [
        "Local demo evidence only; it is not a live platform query.",
      ],
      truncated: false,
    });
  },
  chat: async () => {
    throw new Error(
      "The AI analyst is available in the deployed demonstration when its secured service is enabled.",
    );
  },
};
