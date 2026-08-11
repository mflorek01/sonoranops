import { describe, expect, it } from "vitest";
import {
  incidentDisplayTitle,
  replayModeLabel,
  sensorButtonLabel,
} from "./display";

describe("incidentDisplayTitle", () => {
  it("turns generic operational titles into friendly equipment language", () => {
    expect(
      incidentDisplayTitle("Operational anomaly on primary-crusher-01", [
        "primary-crusher-01",
      ]),
    ).toBe("Primary crusher operating pattern needs review");
  });

  it("turns generic data-quality titles into a clear review prompt", () => {
    expect(
      incidentDisplayTitle("Data quality issue on wash-plant-02", [
        "wash-plant-02",
      ]),
    ).toBe("Wash plant data needs review");
  });

  it("preserves specific issue titles", () => {
    expect(
      incidentDisplayTitle("Crusher drive vibration above operating envelope", [
        "primary-crusher-01",
      ]),
    ).toBe("Crusher drive vibration above operating envelope");
  });
});

describe("sensorButtonLabel", () => {
  it("does not expose the no-metric sentinel as a metric name", () => {
    expect(sensorButtonLabel("no_metric_observed", "No sensor data returned")).toBe(
      "No sensor data returned",
    );
  });

  it("keeps the status beside a real metric", () => {
    expect(sensorButtonLabel("vibration_mm_s", "Critical issue linked")).toBe(
      "Vibration: Critical issue linked",
    );
  });
});

describe("replayModeLabel", () => {
  it("turns internal replay modes into plain simulated-shift wording", () => {
    expect(replayModeLabel("stored_observation_replay")).toBe(
      "recorded simulated shift",
    );
    expect(replayModeLabel("synthetic replay")).toBe(
      "recorded simulated shift",
    );
    expect(replayModeLabel("frozen-synthetic-replay")).toBe(
      "recorded simulated shift",
    );
  });
});
