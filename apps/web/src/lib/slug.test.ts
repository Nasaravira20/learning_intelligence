import { describe, expect, it } from "vitest";

import { slugify } from "./slug";

describe("slugify", () => {
  it("builds a registry-safe slug", () => {
    expect(slugify(" Chain Rule! ")).toBe("chain-rule");
  });

  it("returns an empty slug when the title has no usable characters", () => {
    expect(slugify("!!!")).toBe("");
  });
});
