// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import type { BarSeriesOption, LineSeriesOption } from "echarts/charts";
import { getInstanceByDom } from "echarts/core";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import type { ChartOption } from "@/components/chart/chart";
import { ChartPatternsProvider } from "@/components/chart/patterns";
import { CurrencyProvider } from "@/currency/context";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { roomForCharts } from "@/test/chart-room";
import { example } from "@/test/fixtures";

import { SpendingChart } from "./spending-chart";
import type { SpendingPlan } from "./spending-rows";

const SPENDING = example("spending") as SpendingPlan;

const PROVENANCE = {
  project: "Modernisation du poste de commande",
  code: "PRJ-001",
  revision: "Current revision",
  detail:
    "Basis: Remaining of the current revision · Date of consumption · Subproject: Whole project",
};

/** Render the projection in English, as the screen hands it over. */
function spending(patterns = false, currency?: string) {
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      <CurrencyProvider currency={currency}>
        <ChartPatternsProvider patterns={patterns}>
          <SpendingChart spending={SPENDING} provenance={PROVENANCE} />
        </ChartPatternsProvider>
      </CurrencyProvider>
    </NextIntlClientProvider>,
  );
}

/** The option the drawing shows, once ECharts has it. */
async function shownOption(): Promise<ChartOption> {
  const image = screen.getByRole("img", {
    name: /^Stacked bars of the spending of each cost type/,
  });
  await waitFor(() => {
    expect(getInstanceByDom(image)).toBeDefined();
  });
  return getInstanceByDom(image)?.getOption() as ChartOption;
}

// Each drawing has the room a page gives it: ECharts measures it as it draws.
roomForCharts();

describe("the spending projection chart", () => {
  it("stacks the amount of each cost type by month, in the order of the API, the total of each month the server's [WF-DEV-0100-A]", async () => {
    spending();
    const option = await shownOption();
    const series = option.series as (BarSeriesOption | LineSeriesOption)[];
    expect(series.map((each) => [each.type, each.name])).toEqual([
      ["bar", "Débours"],
      ["bar", "Main-d'œuvre"],
      ["line", "Total"],
    ]);
    expect(series.slice(0, 2).map((each) => (each as BarSeriesOption).stack)).toEqual([
      "load",
      "load",
    ]);
    // The amounts are the strings of the API, aligned on the months, nothing summed.
    const [first] = SPENDING.cost_types;
    expect(series[0]?.data?.[0]).toEqual([
      `${first?.months[0]?.month ?? ""}-01T00:00:00Z`,
      first?.months[0]?.amount,
    ]);
    expect(series[2]?.data).toEqual(
      SPENDING.monthly_totals.map((each) => [`${each.month}-01T00:00:00Z`, each.amount]),
    );
    expect(option.yAxis).toMatchObject([{ min: 0 }]);
  });

  it("gives each cost type a pattern when the account asks for them [WF-IHM-0130-A]", async () => {
    spending(true);
    const option = await shownOption();
    const decals = (option.series as BarSeriesOption[])
      .filter((each) => each.type === "bar")
      .map((each) => (each.itemStyle?.decal as { symbol?: string } | undefined)?.symbol);
    expect(decals.every((symbol) => symbol !== undefined)).toBe(true);
    expect(new Set(decals).size).toBe(decals.length);
  });

  it("reads its values in a table: each month of each cost type, then the total of each month [WF-IHM-0130-A]", async () => {
    spending();
    await userEvent.click(screen.getByText("Values of the chart"));
    const table = screen.getByRole("table");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((cell) => cell.textContent),
    ).toEqual(["Cost type", "Month", "Amount"]);
    const rows = within(table).getAllByRole("row");
    const cells = (row: HTMLElement) =>
      within(row)
        .getAllByRole("cell")
        .map((c) => c.textContent);
    const [type] = SPENDING.cost_types;
    expect(rows).toHaveLength(
      1 +
        SPENDING.cost_types.reduce((count, each) => count + each.months.length, 0) +
        SPENDING.monthly_totals.length,
    );
    const first = rows[1];
    const last = rows.at(-1);
    if (first === undefined || last === undefined) {
      throw new Error("the table has no row");
    }
    expect(within(first).getByRole("rowheader").textContent).toBe(type?.label);
    expect(cells(first)[1]).toBe(
      new Intl.NumberFormat("en", { minimumFractionDigits: 2 }).format(
        Number(type?.months[0]?.amount),
      ),
    );
    // The last row is the total of the last month, the API's.
    expect(within(last).getByRole("rowheader").textContent).toBe("Total");
    expect(cells(last)[1]).toBe(
      new Intl.NumberFormat("en", { minimumFractionDigits: 2 }).format(
        Number(SPENDING.monthly_totals.at(-1)?.amount),
      ),
    );
  });

  it("writes the top of a bar and the tooltip of a month as its table does, in money [WF-IHM-0130-A]", async () => {
    spending(false, "EUR");
    const option = await shownOption();
    await userEvent.click(screen.getByText("Values of the chart"));
    const written = within(screen.getByRole("table"))
      .getAllByRole("row")
      .map((row) => within(row).queryAllByRole("cell").at(-1)?.textContent);
    const series = option.series as LineSeriesOption[];
    const total = series.find((each) => each.type === "line");
    const lastMonth = SPENDING.monthly_totals.at(-1);
    const point = { value: [`${lastMonth?.month ?? ""}-01T00:00:00Z`, lastMonth?.amount] };
    const top = (total?.label?.formatter as (point: { value: unknown }) => string)(point);
    expect(top).toBe(written.at(-1));
    expect(top).toMatch(/€/);
    const tooltip = (
      option.tooltip as unknown as { formatter: (params: unknown) => string }[]
    )[0]?.formatter([{ ...point, seriesName: "Total", marker: "" }]);
    expect(tooltip).toContain(`<b>${written.at(-1) ?? ""}</b>`);
  });

  it("is accessible, with its table folded out [WF-IHM-0130-A]", async () => {
    const { container } = spending();
    await shownOption();
    await userEvent.click(screen.getByText("Values of the chart"));
    await expectAccessible(container);
  });
});
