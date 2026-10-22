// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { mainStructure } from "./grid-screen";

const STRUCTURES = example("structures") as components["schemas"]["CostStructure"][];

describe("the main structure of a revision", () => {
  it("is the one the revision lists as main, whatever its place among the others", () => {
    const main = STRUCTURES.find((structure) => structure.kind === "main");
    expect(main).toBeDefined();
    expect(mainStructure([...STRUCTURES].reverse())).toBe(main);
  });

  it("is an unexpected answer when the revision lists none, which the contract rules out", () => {
    const others = STRUCTURES.filter((structure) => structure.kind !== "main");
    expect(() => mainStructure(others)).toThrow(
      expect.objectContaining({ name: "UnexpectedAnswer", operation: "listCostStructures" }),
    );
    expect(() => mainStructure([])).toThrow(expect.objectContaining({ name: "UnexpectedAnswer" }));
  });
});
