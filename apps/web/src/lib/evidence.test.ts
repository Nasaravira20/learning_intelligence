import { describe, expect, it } from "vitest";

import { evidenceLabel } from "./evidence";

describe("evidence labels", () => {
  it("keeps observed and inferred distinct", () => {
    expect(evidenceLabel("observed")).toBe("Observed");
    expect(evidenceLabel("inferred")).toBe("Inferred, not confirmed");
    expect(evidenceLabel("inferred")).not.toBe(evidenceLabel("observed"));
  });
});
