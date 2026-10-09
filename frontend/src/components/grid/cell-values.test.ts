// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { estimateReference } from "@/test/reference";

import { firstChoice, startingText } from "./cell-values";

const { categories = [], roles = [] } = estimateReference();

describe("a choice searched by what was typed", () => {
  it("is the first of the list whose name starts with it: « Mi » is the commissioning", () => {
    expect(firstChoice(categories, "Mi", "fr")?.id).toBe("01926f3a-7c00-7000-8000-000000000405");
    expect(firstChoice(categories, "Mise en service", "fr")?.label).toBe("Mise en service");
  });

  it("reads neither case nor accents, and skips a deactivated choice", () => {
    expect(firstChoice(roles, "ingenieur", "fr")?.label).toBe("Ingénieur électricien");
    expect(firstChoice(roles, "Auto", "fr")).toBeUndefined();
  });

  it("opens a list at the first choice the character typed starts, at the one made otherwise", () => {
    const kind = { type: "choice", choices: () => categories, nullable: false } as const;
    const made = "01926f3a-7c00-7000-8000-000000000402";
    // The categories come by code: « M » starts the electrical equipment first.
    expect(startingText(kind, made, "M", "fr")).toBe("01926f3a-7c00-7000-8000-000000000403");
    expect(startingText(kind, made, undefined, "fr")).toBe(made);
    expect(startingText(kind, made, "§", "fr")).toBe(made);
  });
});
