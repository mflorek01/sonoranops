import type { Incident } from "../../lib/api/types";

const severityRank: Record<Incident["severity"], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export function isOpenIncident(incident: Incident) {
  return !["resolved", "dismissed"].includes(incident.state);
}

export function selectPriorityIncident(incidents: Incident[]) {
  return [...incidents]
    .filter(isOpenIncident)
    .sort(
      (left, right) =>
        severityRank[left.severity] - severityRank[right.severity] ||
        right.evidenceCount - left.evidenceCount ||
        left.id.localeCompare(right.id),
    )[0];
}
