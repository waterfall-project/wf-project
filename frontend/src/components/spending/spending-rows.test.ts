// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { type SpendingPlan, spendingDetail } from "./spending-rows";

const PLAN = example("spending") as SpendingPlan;

describe("the rows of the grid of the spending projection", () => {
  it("lists each cost type then its categories, in the order of the API, the amounts as the API gives them [WF-DEV-0100-A]", () => {
    const detail = spendingDetail(PLAN);
    expect(detail.rows.map((row) => [row.kind, row.label])).toEqual([
      ["cost_type", "Débours"],
      ["category", "Sous-traitance"],
      ["category", "Matériel électrique"],
      ["cost_type", "Main-d'œuvre"],
      ["category", "Ingénierie électrique"],
      ["category", "Mise en service"],
    ]);
    const [type, category] = detail.rows;
    expect(type?.parent).toBeNull();
    expect(category?.parent).toBe(type?.key);
    expect(type?.total).toBe(PLAN.cost_types[0]?.total);
    expect(category?.total).toBe(PLAN.cost_types[0]?.categories[0]?.total);
  });

  it("keeps the amount of a month of a cost type as the API gives it [WF-DEV-0100-A]", () => {
    const [type] = PLAN.cost_types;
    const month = type?.months[0];
    expect(spendingDetail(PLAN).rows[0]?.months[month?.month ?? ""]).toBe(month?.amount);
  });

  it("takes the totals of the months and of the projection from the API, never summing them [WF-DEV-0100-A] [WF-ARC-0020-A]", () => {
    const detail = spendingDetail(PLAN);
    expect(detail.totals.total).toBe(PLAN.total);
    expect(detail.months).toEqual(PLAN.monthly_totals.map((each) => each.month));
    for (const each of PLAN.monthly_totals) {
      expect(detail.totals.months[each.month]).toBe(each.amount);
    }
  });

  it("leaves a month a row has no amount on out, never filled with a zero [WF-DEV-0100-A]", () => {
    const detail = spendingDetail(PLAN);
    const category = detail.rows.find((row) => row.kind === "category");
    const lacking = detail.months.filter((month) => category?.months[month] === undefined);
    for (const month of lacking) {
      expect(category?.months).not.toHaveProperty(month);
    }
  });
});
