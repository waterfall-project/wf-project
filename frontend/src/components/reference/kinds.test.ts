// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import type { CostCategory } from "./cost-kinds";
import { type Choice, labourOf, offered } from "./kinds";

// The two hundred categories of the volumes, each saying the type of its nature — labour,
// disbursement, provision —: a hundred and fifty of labour, coded MO-.
const categories = (example("volume/cost_categories") as { items: CostCategory[] }).items;

describe("the categories a role may be attached to", () => {
  it("are those whose nature is of labour, as each says it, in the order of the server, as choices [WF-REF-0090-A]", () => {
    const labour = labourOf(categories);
    // Son rattachement à une catégorie hors main-d'œuvre est refusé : none is offered.
    expect(labour).toHaveLength(150);
    expect(labour?.every((choice) => choice.code?.startsWith("MO-"))).toBe(true);
    expect(labour?.some((choice) => choice.code === "ACH-001")).toBe(false);
    // The order of the server: the purchases first, then the labour from MO-001.
    const first = categories.find((category) => category.code === "MO-001");
    expect(labour?.[0]).toEqual({
      id: first?.cost_category_id,
      code: "MO-001",
      label: first?.label,
      active: true,
    });
  });

  it("are none known when the categories were not read", () => {
    expect(labourOf(undefined)).toBeUndefined();
  });
});

describe("the objects offered to an entry", () => {
  const choices: Choice[] = [
    { id: "a", label: "Actif", active: true },
    { id: "d", label: "Désactivé", active: false },
  ];

  it("are the active ones, and the one attached marked deactivated when the list does not offer it", () => {
    expect(offered(choices, { id: "d", label: "Désactivé" })).toEqual([
      { id: "a", label: "Actif", active: true, deactivated: false },
      { id: "d", label: "Désactivé", active: false, deactivated: true },
    ]);
    expect(offered(choices, { id: "x", label: "Absent", level: 2 })).toEqual([
      { id: "a", label: "Actif", active: true, deactivated: false },
      { id: "x", label: "Absent", level: 2, active: false, deactivated: true },
    ]);
  });

  it("are the one attached alone, without a mark, when the list was not read", () => {
    expect(offered(undefined, { id: "x", label: "Inconnu" })).toEqual([
      { id: "x", label: "Inconnu", active: false, deactivated: false },
    ]);
    expect(offered(undefined, undefined)).toEqual([]);
  });
});
