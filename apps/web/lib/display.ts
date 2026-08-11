export const pretty = (value: string) =>
  value
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const metricLabels: Record<string, string> = {
  belt_speed_mps: "Belt speed",
  feed_rate_tph: "Feed rate",
  motor_current_amps: "Motor current",
  screen_load_percent: "Screen load",
  vibration_mm_s: "Vibration",
};

export const metricLabel = (metric: string) =>
  metricLabels[metric] ?? pretty(metric);

const assetLabels: Record<string, string> = {
  "primary-crusher-01": "Primary crusher",
  "conveyor-17": "Conveyor",
  "secondary-crusher-01": "Secondary crusher",
  "screen-01": "Screen",
  "stacker-01": "Stacker",
  "stockpile-01": "Stockpile",
  "feeder-01": "Feeder",
  "wash-plant-02": "Wash plant",
};

export const assetLabel = (assetId: string) =>
  assetLabels[assetId] ?? pretty(assetId);

export const incidentDisplayTitle = (title: string, assetIds: string[]) => {
  const genericTitle = /^(operational anomaly|data quality issue) on (.+)$/i.exec(
    title.trim(),
  );
  if (!genericTitle) return title;

  const equipment = assetLabel(assetIds[0] ?? genericTitle[2]);
  return genericTitle[1].toLowerCase() === "data quality issue"
    ? `${equipment} data needs review`
    : `${equipment} operating pattern needs review`;
};

export const sensorButtonLabel = (
  metric: string,
  statusLabel: string,
) =>
  metric === "no_metric_observed"
    ? "No sensor data returned"
    : `${metricLabel(metric)}: ${statusLabel}`;
