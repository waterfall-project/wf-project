// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import type { BarSeriesOption, LineSeriesOption } from "echarts/charts";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { ChartPalette, ChartProps } from "@/components/chart/chart";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { roomForCharts } from "@/test/chart-room";
import { example } from "@/test/fixtures";

import { WorkloadView } from "./portfolio-views";

type Workload = components["schemas"]["PortfolioWorkload"];

// The charts render as they would, and keep what they were handed: their option among it.
const charts = vi.hoisted((): { props: ChartProps[] } => ({ props: [] }));
vi.mock("@/components/chart/chart", async (original) => {
  const actual = await original<typeof import("@/components/chart/chart")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    Chart: (props: ChartProps) => {
      charts.props.push(props);
      return createElement(actual.Chart, props);
    },
  };
});

/** The colours and the font a chart is drawn in, as the probes would read them. */
const PALETTE: ChartPalette = {
  series: ["rgb(1, 1, 1)", "rgb(2, 2, 2)"],
  text: "rgb(3, 3, 3)",
  mark: "rgb(4, 4, 4)",
  axis: "rgb(5, 5, 5)",
  grid: "rgb(6, 6, 6)",
  background: "rgb(7, 7, 7)",
  zones: { nominal: "nominal", watch: "watch", alert: "alert" },
  font: "sans-serif",
};

const WORKLOAD = example("portfolio_workload") as Workload;
const NODE_WORKLOAD = example("portfolio_workload_org_node") as Workload;

/** The aggregated workload in English, as the page hands it over. */
function aggregated(workload: Workload = WORKLOAD) {
  charts.props = [];
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      <WorkloadView workload={workload} />
    </NextIntlClientProvider>,
  );
}

/** The option of the chart the view drew, in the palette above. */
function drawn() {
  const option = charts.props.at(-1)?.option(PALETTE);
  return { option, series: [option?.series].flat() as (BarSeriesOption | LineSeriesOption)[] };
}

roomForCharts();

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the aggregated workload in a stack of bars", () => {
  it("stacks the load of each role by month, the total of each month at the top of its bar, as the server gave them [WF-PTF-0060-A]", () => {
    aggregated();
    const { option, series } = drawn();
    const roles = series.slice(0, 3) as BarSeriesOption[];
    expect(roles.map((each) => [each.type, each.name, each.stack])).toEqual([
      ["bar", "Ingénieur électricien", "load"],
      ["bar", "Technicien de mise en service", "load"],
      ["bar", "Monteur câbleur", "load"],
    ]);
    // Each role told apart without its colour too: the pattern of the symbol of its rank.
    expect(roles.map((each) => each.itemStyle?.decal)).toMatchObject([
      { symbol: "circle" },
      { symbol: "triangle" },
      { symbol: "rect" },
    ]);
    expect(roles[0]?.data?.slice(0, 2)).toEqual([
      ["2026-06-01T00:00:00Z", "636241.09"],
      ["2026-07-01T00:00:00Z", "733321.89"],
    ]);
    // The total of a month is the server's, drawn as the label of an invisible line, never a sum.
    const total = series[3] as LineSeriesOption;
    expect(total).toMatchObject({ type: "line", name: "Total", silent: true });
    expect(total.data?.slice(0, 2)).toEqual([
      ["2026-06-01T00:00:00Z", "985866.36"],
      ["2026-07-01T00:00:00Z", "1135130.19"],
    ]);
    const label = total.label?.formatter as (point: unknown) => string;
    expect(label({ value: ["2026-06-01T00:00:00Z", "985866.36"] })).toBe("985,866.36");
    // The legend names the roles alone.
    expect(option?.legend).toMatchObject({ data: roles.map((each) => each.name) });
    expect(option?.useUTC).toBe(true);
  });

  it("draws the capacity of the perimeter the server rendered as a dashed line, and says it [WF-PTF-0060-A]", () => {
    aggregated();
    const { series } = drawn();
    const capacity = series[4] as LineSeriesOption;
    expect(capacity.data).toEqual([]);
    expect(capacity.markLine?.data).toEqual([
      {
        yAxis: WORKLOAD.capacity_monthly_hours,
        name: "Capacity: 1,360,640.5 h per month",
        label: { formatter: "Capacity: 1,360,640.5 h per month" },
        lineStyle: { color: PALETTE.mark, type: "dashed" },
      },
    ]);
    expect(screen.getByText("Capacity of the perimeter: 1,360,640.5 h per month.")).toBeVisible();
  });

  it("extends the axis to the capacity, which ECharts would cut off, and to the tallest bar when it is higher [WF-PTF-0060-A]", () => {
    aggregated();
    const { option } = drawn();
    const { max } = option?.yAxis as { max: (range: { max: number }) => number };
    // The tallest total of the example, 1,135,130.19 h, is under the capacity, 1,360,640.5 h.
    expect(max({ max: 1_135_130.19 })).toBe(Number(WORKLOAD.capacity_monthly_hours));
    expect(max({ max: 2_000_000 })).toBe(2_000_000);
  });

  it("lists the roles and their hours in the tooltip of a month, the label of a role escaped", () => {
    aggregated();
    const { option } = drawn();
    const tooltip = option?.tooltip as { formatter: (params: unknown) => string };
    const row = (name: string, hours: string, marker: string) => ({
      seriesName: name,
      marker,
      value: ["2026-07-01T00:00:00Z", hours],
    });
    expect(
      tooltip.formatter([
        row("Ingénieur <b>électricien</b>", "733321.89", "<i></i>"),
        row("Monteur câbleur", "0", "<u></u>"),
        row("Total", "1135130.19", ""),
      ]),
    ).toBe(
      [
        "<b>July 2026</b>",
        "<i></i>Ingénieur &lt;b&gt;électricien&lt;/b&gt; <b>733,321.89 h</b>",
        "<u></u>Monteur câbleur <b>0 h</b>",
        "Total <b>1,135,130.19 h</b>",
      ].join("<br/>"),
    );
  });

  it("shows the zone the server rendered for a month, a month at 120 % of the capacity signalled as such [WF-PTF-0060-A]", async () => {
    // The front shows the zone the server renders, it classes nothing: a variant of
    // `portfolio_workload` whose first month of the first role, 0.966, is written as the server
    // would write it at 1.2, in the alert zone.
    const [role, ...others] = WORKLOAD.roles;
    const [month, ...rest] = role?.months ?? [];
    if (role === undefined || month === undefined) {
      throw new Error("The example lacks a role with its months");
    }
    const overloaded = {
      ...month,
      load_ratio: { is_computable: true, value: "1.2", reason: null },
      zone: "alert" as const,
    };
    const { container } = aggregated({
      ...WORKLOAD,
      roles: [{ ...role, months: [overloaded, ...rest] }, ...others],
    });
    const figure = screen.getByRole("figure", { name: "Stacked load by role and by month" });
    const table = screen.getByRole("table", { name: "Load by role and by month" });
    // Under the chart, in the order of the page.
    expect(figure.compareDocumentPosition(table)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    const cells = within(screen.getByRole("row", { name: /Ingénieur électricien/ })).getAllByRole(
      "cell",
    );
    expect(cells[1]).toHaveTextContent("658,654 h");
    expect(cells[2]).toHaveTextContent("636,241.09 h");
    expect(cells[2]).toHaveTextContent("120%");
    // The zone the server classes the month in, by the one signal.
    expect(cells[2]?.querySelector("[role=img]")).toHaveAccessibleName("Alert");
    await expectAccessible(container);
  });

  it("lists the total of each month in the values of the chart", () => {
    aggregated();
    const figure = screen.getByRole("figure", { name: "Stacked load by role and by month" });
    const rows = within(figure).getAllByRole("row", { hidden: true });
    expect(rows[0]).toHaveTextContent("MonthTotal (h)");
    expect(rows[1]).toHaveTextContent("June 2026985,866.36");
    expect(rows).toHaveLength(1 + WORKLOAD.monthly_totals.length);
  });
});

describe("the export of the aggregated workload", () => {
  it("names the perimeter, the node of organisation and the date of calculation in the image [WF-IHM-0130-A]", () => {
    aggregated(NODE_WORKLOAD);
    const exported = charts.props.at(-1)?.exported?.();
    expect(exported).toEqual({
      title: "Aggregated workload",
      subtitle:
        "In progress and Pricing · 300 projects · calculated on 3 Jun 2026 · Horizon: June 2026 to November 2026 · Labour of Direction technique and of its descendants",
      fileName: "aggregated-workload-portfolio-2026-06-03.png",
    });
    expect(screen.getByRole("button", { name: "Export as PNG" })).toBeVisible();
  });
});
