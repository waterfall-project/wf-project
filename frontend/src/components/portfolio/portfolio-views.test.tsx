// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { PortfolioValueView } from "./portfolio-value";
import { CostStructureView, WorkloadView } from "./portfolio-views";

type Schemas = components["schemas"];

/** What a view says in English, its tags left out, one space apart. */
function text(view: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {view}
    </NextIntlClientProvider>,
  )
    .replace(/<[^>]*>/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ");
}

/** A share too small to show, as the catalogue says it in English. */
const TINY = "<0.01%";

describe("the shares of the portfolio, never « 0 % » when they are not nil (#626)", () => {
  it("says a share of the cost structure given nil while its amount is not below the smallest shown", () => {
    // A variant of `volume/portfolio_cost_structure`: the share of the provision in the budget,
    // 0.1, changed to 0 — its amount kept.
    const structure = example(
      "volume/portfolio_cost_structure",
    ) as Schemas["PortfolioCostStructure"];
    const budget = structure.budget_by_cost_type.map((part) =>
      part.label === "Provision" ? { ...part, share: "0" } : part,
    );
    const said = text(
      <CostStructureView structure={{ ...structure, budget_by_cost_type: budget }} />,
    );
    expect(said).toContain(`Provision 266,262,019.77 ${TINY}`);
  });

  it("says a load too small to show below the smallest shown", () => {
    // A variant of `portfolio_workload`: the load of the first month of the first role, 0.966,
    // changed to 0.00003.
    const workload = example("portfolio_workload") as Schemas["PortfolioWorkload"];
    const [role, ...others] = workload.roles;
    const [month, ...rest] = role?.months ?? [];
    if (role === undefined || month === undefined) {
      throw new Error("The example lacks a role with its months");
    }
    const load = { ...month, load_ratio: { is_computable: true, value: "0.00003", reason: null } };
    const said = text(
      <WorkloadView
        workload={{ ...workload, roles: [{ ...role, months: [load, ...rest] }, ...others] }}
      />,
    );
    expect(said).toContain(`636,241.09 h ${TINY}`);
  });

  it("says a conversion rate too small to show below the smallest shown", () => {
    // A variant of `volume/portfolio_value`: its conversion rate, 0.4, changed to 0.00003.
    const value = example("volume/portfolio_value") as Schemas["PortfolioValue"];
    const rate = { is_computable: true, value: "0.00003", reason: null };
    expect(text(<PortfolioValueView value={{ ...value, conversion_rate: rate }} />)).toContain(
      `Conversion rate ${TINY}`,
    );
  });
});
