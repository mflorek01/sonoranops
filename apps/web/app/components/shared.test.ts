import { describe, expect, it } from "vitest";
import { metricLabel } from "./shared";

describe("metricLabel", () => {
  it("removes canonical unit suffixes from displayed metric labels", () => {
    expect(metricLabel("belt_speed_mps")).toBe("Belt speed");
    expect(metricLabel("feed_rate_tph")).toBe("Feed rate");
    expect(metricLabel("motor_current_amps")).toBe("Motor current");
    expect(metricLabel("vibration_mm_s")).toBe("Vibration");
    expect(metricLabel("screen_load_percent")).toBe("Screen load");
  });
});
