// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The families of the screens (US-2070; EP-25, « Deux familles d'écrans, dites par Screen »): every
 * function of the navigation, and every leaf with a screen of its own, in one family, and the
 * screens of work those the conception names.
 */
import { describe, expect, it } from "vitest";

import { FUNCTION_GROUPS } from "@/navigation/functions";

import { FUNCTION_DENSITY, LEAF_DENSITY } from "./function-display";
import { SCREEN } from "./page-header";

// Travail — planning, devis, reste à engager, arbre des tâches, coûts réels, Kanban, chronologies,
// registre des risques, journal d'audit —: serré, la fenêtre remplie.
const WORK = [
  "planning",
  "estimate",
  "remaining",
  "actual_costs",
  "risks",
  "audit_log",
  "FBS-4.3.5",
  "FBS-4.5.3",
  "FBS-4.3.1",
];

describe("the families of the screens", () => {
  it("set every function of the navigation and every leaf with its own screen in one", () => {
    const functions = FUNCTION_GROUPS.flatMap((group) => group.functions);
    // The installation (FBS-1.6) has its permissions and its tables here; its entry in the
    // navigation comes with its screen (EP-25, US-2120/L2).
    expect(Object.keys(FUNCTION_DENSITY).sort()).toEqual(
      [...functions.map((fn) => fn.permission), "installation"].sort(),
    );
    expect(Object.keys(LEAF_DENSITY).sort()).toEqual(
      functions.flatMap((fn) => (fn.leaves ?? []).map((leaf) => leaf.code)).sort(),
    );
  });

  it("make dense the screens of work alone, every other a screen of settings or of consultation", () => {
    const dense = Object.entries({ ...FUNCTION_DENSITY, ...LEAF_DENSITY })
      .filter(([, density]) => density === "dense")
      .map(([name]) => name);
    expect(dense.sort()).toEqual([...WORK].sort());
  });

  it("set a screen of settings or of consultation in a column centred and bounded, a screen of work across the window", () => {
    expect(SCREEN.airy.split(" ")).toEqual(
      expect.arrayContaining(["mx-auto", "w-full", "max-w-column"]),
    );
    expect(SCREEN.dense).not.toMatch(/max-w-|mx-auto/);
  });
});
