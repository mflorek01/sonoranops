import { describe, expect, it } from "vitest";
import { demoApi } from "./demo";

describe("demo operations adapter", () => {
  it("keeps lifecycle changes behind the OperationsApi contract", async () => {
    const before = await demoApi.getIncident("inc-2048");
    const after = await demoApi.transitionIncident("inc-2048", {
      state: "mitigated",
      reason: "Controlled test transition",
    });

    expect(after.state).toBe("mitigated");
    expect(after.timeline).toHaveLength(before.timeline.length + 1);
    expect(after.timeline.at(-1)?.reason).toBe("Controlled test transition");
  });

  it("requires an auditable reason for lifecycle changes", async () => {
    await expect(
      demoApi.transitionIncident("inc-2048", { state: "resolved", reason: "" }),
    ).rejects.toThrow("reason is required");
  });

  it("returns labeled deterministic evidence through the assistant boundary", async () => {
    const result = await demoApi.runAssistantTool("get_incident_evidence", {
      incident_id: "inc-2048",
    });
    expect(result.mode).toBe("deterministic_evidence_tool");
    expect(result.toolName).toBe("get_incident_evidence");
    expect(result.siteId).toBe("sonoran-west");
    expect(result.records.length).toBeGreaterThan(0);
    expect(result.uncertaintyNotes[0]).toContain("Local demo");
  });

  it("makes the analyst's unavailable state explicit in local demo mode", async () => {
    await expect(demoApi.chat("What should I review?")).rejects.toThrow(
      "AI analyst is available",
    );
  });

  it("provides bounded visual analytics with returned points and process facts", async () => {
    const briefing = await demoApi.getBriefing();
    const analytics = briefing.visualAnalytics;

    expect(analytics?.metricSeries).toHaveLength(4);
    expect(analytics?.metricSeries.every((series) => series.points.length > 0)).toBe(true);
    expect(analytics?.processNodes.map((node) => node.assetId)).toEqual([
      "primary-crusher-01",
      "conveyor-17",
      "wash-plant-02",
    ]);
  });
});
