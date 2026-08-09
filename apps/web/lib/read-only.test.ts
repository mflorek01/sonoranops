import { describe, expect, it } from "vitest";

import { isPublicReadOnlyMode } from "./read-only";

describe("isPublicReadOnlyMode", () => {
  it("enables read-only mode only for the explicit true build value", () => {
    expect(isPublicReadOnlyMode("true")).toBe(true);
    expect(isPublicReadOnlyMode(undefined)).toBe(false);
    expect(isPublicReadOnlyMode("false")).toBe(false);
  });
});
