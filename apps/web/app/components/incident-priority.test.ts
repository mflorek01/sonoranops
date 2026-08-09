import { describe, expect, it } from "vitest";
import type { Incident } from "../../lib/api/types";
import { selectPriorityIncident } from "./incident-priority";

const incident = (overrides: Partial<Incident>): Incident => ({
  id: "inc-1",
  title: "Test incident",
  state: "open",
  severity: "low",
  assetIds: [],
  openedAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  summary: "Test summary",
  evidenceCount: 0,
  ...overrides,
});

describe("selectPriorityIncident", () => {
  it("uses severity, evidence count, then id and excludes closed records", () => {
    const priority = selectPriorityIncident([
      incident({
        id: "inc-4",
        severity: "critical",
        state: "resolved",
        evidenceCount: 99,
      }),
      incident({ id: "inc-3", severity: "high", evidenceCount: 6 }),
      incident({ id: "inc-2", severity: "critical", evidenceCount: 2 }),
      incident({ id: "inc-1", severity: "critical", evidenceCount: 2 }),
    ]);

    expect(priority?.id).toBe("inc-1");
  });
});
