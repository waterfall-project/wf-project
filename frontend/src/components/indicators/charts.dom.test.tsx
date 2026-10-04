// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ChartOption, ChartPalette } from "@/components/chart/chart";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { type CurveSeries, CurveSeriesChart } from "./curve-series-chart";
import { IndexChart, type IndexHistory } from "./index-chart";
import { MilestoneChart, type MilestoneTracking } from "./milestone-chart";

const drawn = vi.hoisted(() => ({ options: [] as ((palette: ChartPalette) => ChartOption)[] }));

// The envelope is tested on its own (chart.dom.test.tsx): here, what a chart is handed to draw.
vi.mock("@/components/chart/chart", async (actual) => ({
  ...(await actual<typeof import("@/components/chart/chart")>()),
  Chart: ({
    title,
    description,
    note,
    option,
    children,
  }: {
    title: string;
    description: string;
    note?: ReactNode;
    option: (palette: ChartPalette) => ChartOption;
    children: ReactNode;
  }) => {
    drawn.options.push(option);
    return (
      <figure aria-label={title}>
        {note}
        <p>{description}</p>
        {children}
      </figure>
    );
  },
}));

const PALETTE: ChartPalette = {
  series: ["s1", "s2", "s3", "s4"],
  text: "text",
  mark: "mark",
  axis: "axis",
  grid: "grid",
  background: "background",
  font: "font",
};

const HISTORY = example("index_history") as IndexHistory;

/** Render in English. */
function english(node: ReactNode) {
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {node}
    </NextIntlClientProvider>,
  );
}

/** The last option a chart was handed, drawn in the palette of the test. */
function lastOption() {
  return drawn.options.at(-1)?.(PALETTE);
}

/** The series of the last option a chart was handed. */
function lastSeries() {
  const series = lastOption()?.series;
  return Array.isArray(series) ? series : [];
}

beforeEach(() => {
  drawn.options = [];
});

describe("the evolution of an index", () => {
  it("draws one curve per scope, in the order of the API, from the strings it gave, a value it could not compute a gap [WF-IND-0130-A]", () => {
    english(<IndexChart kind="schedule" history={HISTORY} />);
    const series = lastSeries();
    expect(series.map((each) => each.name)).toEqual([
      "Whole project",
      "Poste de commande",
      "Essais et mise en service",
      "No subproject",
      "Thresholds",
    ]);
    // No legend, which would overflow onto the plot: each curve is named at its end.
    expect(lastOption()?.legend).toBeUndefined();
    // The sub-projects have no schedule index the API could compute: no point, no name drawn.
    expect(series.slice(0, -1).map((curve) => curve.endLabel?.show)).toEqual([
      true,
      false,
      false,
      true,
    ]);
    expect(series[0]?.data).toEqual([
      ["2025-12-15T16:00:00Z", "-"],
      ["2026-02-01T09:00:00Z", "-"],
      ["2026-03-16T14:05:00Z", "0"],
    ]);
  });

  it("draws the thresholds of its index from the reference, as the API gave them, on a series of their own [WF-IND-0130-A]", () => {
    english(<IndexChart kind="cost" history={HISTORY} />);
    const series = lastSeries();
    // No curve carries them: a curve the reader could no longer see would take them away.
    expect(series.slice(0, -1).map((curve) => curve.markLine)).toEqual([
      undefined,
      undefined,
      undefined,
      undefined,
    ]);
    const thresholds = series.at(-1);
    expect(thresholds?.data).toEqual([]);
    // In the colour of the marks of the charter, not the default of ECharts.
    expect(thresholds?.color).toBe("mark");
    const marks = thresholds?.markLine?.data as { yAxis: string; name: string }[] | undefined;
    expect(marks?.map(({ yAxis, name }) => [name, yAxis])).toEqual([
      ["Watch threshold", "0.9"],
      ["Alert threshold", "0.8"],
    ]);
    expect(
      screen.getByText(/with the watch threshold at 0\.9 and the alert threshold at 0\.8/),
    ).toBeInTheDocument();
  });

  it("bears the date its evolution is computed at, under its caption [WF-IHM-0020-A]", () => {
    english(<IndexChart kind="cost" history={HISTORY} />);
    const figure = screen.getByRole("figure", { name: "Evolution of the cost index" });
    expect(within(figure).getByText(/^Computed on/)).toBeInTheDocument();
    expect(figure.querySelector("time")).toHaveAttribute("datetime", HISTORY.context.computed_at);
  });

  it("lists each point, its revision, its value or why it has none, and its zone by the one signal [WF-IHM-0070-A]", async () => {
    const { container } = english(<IndexChart kind="schedule" history={HISTORY} />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(12);
    const [first, , third] = rows;
    if (first === undefined || third === undefined) {
      throw new Error("The table lists no point");
    }
    const current = within(third);
    expect(current.getByRole("rowheader")).toHaveTextContent("Whole project");
    expect(current.getByText("Current revision")).toBeInTheDocument();
    expect(current.getByText("0")).toBeInTheDocument();
    expect(current.getByText("Alert")).toBeInTheDocument();
    const offer = within(first);
    expect(offer.getByText("Offre v1.0")).toBeInTheDocument();
    expect(
      offer.getByText("Not computable — No planned value at the calculation date."),
    ).toBeInTheDocument();
    expect(offer.queryByText(/Nominal|Watch|Alert/)).toBeNull();
    await expectAccessible(container);
  });
});

const TRACKING = example("milestone_tracking") as MilestoneTracking;

/** Where the charts of the witness project come from. */
const PROVENANCE = {
  project: "Modernisation du poste de commande",
  code: "PRJ-001",
  revision: "Current revision",
};

describe("the tracking of the milestones", () => {
  it("draws each milestone by the dates its revisions forecast, at midnight in UTC, and the diagonal of equal dates up to the date of calculation [WF-IND-0090-A]", () => {
    english(<MilestoneChart tracking={TRACKING} provenance={PROVENANCE} />);
    const series = lastSeries();
    expect(series.map((each) => each.name)).toEqual([
      "Réception des études",
      "Réception usine",
      "Equal dates",
    ]);
    // A milestone that holds draws a horizontal line, one that slips climbs.
    expect(series[1]?.data).toEqual([
      ["2025-12-15T16:00:00Z", "2026-06-30T00:00:00Z"],
      ["2026-02-01T09:00:00Z", "2026-06-30T00:00:00Z"],
      ["2026-03-16T14:05:00Z", "2026-09-30T00:00:00Z"],
    ]);
    expect(series[2]?.data).toEqual([
      ["2025-12-15T16:00:00Z", "2025-12-15T16:00:00Z"],
      ["2026-03-16T14:05:00Z", "2026-03-16T14:05:00Z"],
    ]);
    expect(series.map((each) => each.endLabel?.show)).toEqual([true, true, true]);
  });

  it("lists each forecast as a date of planning, and whether its milestone is completed [WF-IND-0090-A]", async () => {
    const { container } = english(<MilestoneChart tracking={TRACKING} provenance={PROVENANCE} />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringMatching(/^Réception des études.*10 Apr 2026Not completed$/),
      expect.stringMatching(/^Réception des études.*24 Apr 2026Not completed$/),
      expect.stringMatching(/^Réception des études.*24 Apr 2026Not completed$/),
      expect.stringMatching(/^Réception usine.*30 Jun 2026Not completed$/),
      expect.stringMatching(/^Réception usine.*30 Jun 2026Not completed$/),
      expect.stringMatching(/^Réception usine.*30 Sept 2026Not completed$/),
    ]);
    const figure = screen.getByRole("figure", { name: "Time/time diagram" });
    expect(figure.querySelector("time")).toHaveAttribute("datetime", TRACKING.context.computed_at);
    await expectAccessible(container);
  });

  it("places and writes the ticks of its axes in UTC, whatever the zone of the workstation", () => {
    english(<MilestoneChart tracking={TRACKING} provenance={PROVENANCE} />);
    const option = lastOption();
    expect(option?.useUTC).toBe(true);
    const yAxis = option?.yAxis as { axisLabel: { formatter: (value: number) => string } };
    expect(yAxis.axisLabel.formatter(Date.parse("2026-05-01T00:00:00Z"))).toBe("May 2026");
  });
});

/** Render cumulative curves under a caption of the test. */
function curves(name: string) {
  const data = example(name) as CurveSeries;
  return {
    data,
    ...english(
      <CurveSeriesChart
        curves={data}
        title="Curves"
        description="Drawn."
        file="curves"
        provenance={PROVENANCE}
      />,
    ),
  };
}

describe("the cumulative curves", () => {
  it("draws the reference budget, the actual cost to the date of calculation and the projection from it, as the API gave them [WF-IND-0100-A]", () => {
    curves("cost_curve");
    const series = lastSeries();
    expect(series.map((each) => each.name)).toEqual([
      "Reference budget",
      "Actual cost",
      "Project manager’s projection",
    ]);
    expect(series[1]?.data).toEqual([
      ["2026-03-01T00:00:00Z", "0.00"],
      ["2026-03-16T00:00:00Z", "0.00"],
    ]);
    expect(series[2]?.data?.[0]).toEqual(["2026-03-16T00:00:00Z", "0.00"]);
    expect(series[0]?.data?.at(-1)).toEqual(["2026-06-30T00:00:00Z", "100000.00"]);
    // Dates of planning: the ticks are placed at midnight in UTC, as the points.
    expect(lastOption()?.useUTC).toBe(true);
  });

  it("marks a step of the reference budget at its date, named by its cause, and lists it [WF-IND-0100-A]", () => {
    curves("cost_curve_amendment");
    const steps = lastSeries().at(-1);
    expect(steps?.data).toEqual([]);
    const marks = steps?.markLine?.data as { xAxis: string; name: string }[] | undefined;
    expect(marks?.map(({ xAxis, name }) => [name, xAxis])).toEqual([
      ["Amendment", "2026-03-10T00:00:00Z"],
    ]);
    const table = screen.getByRole("table", { name: "Steps of the reference budget" });
    expect(
      within(table).getByRole("row", { name: "10 Mar 2026 Amendment 15,000.00" }),
    ).toBeVisible();
  });

  it("lists the cash out by month the API gives with the payment delays, the shifted points as given [WF-IND-0100-A]", async () => {
    const { container, data } = curves("cost_curve_payment_delays");
    expect(lastSeries()[0]?.data?.[0]).toEqual(["2026-03-31T00:00:00Z", "0.00"]);
    const table = screen.getByRole("table", { name: "Cash out by month" });
    expect(
      within(table)
        .getAllByRole("row")
        .map((row) => row.textContent),
    ).toEqual([
      "MonthPaid outTo pay out",
      "March 20260.000.00",
      "April 20260.0060,000.00",
      "May 20260.0040,000.00",
    ]);
    expect(data.cash_out_by_month).toHaveLength(3);
    await expectAccessible(container);
  });

  it("draws the planned value to the end of the reference, the earned value and the actual cost to the date of calculation [WF-IND-0110-A]", () => {
    curves("earned_value_curves");
    const series = lastSeries();
    expect(series.map((each) => each.name)).toEqual([
      "Planned value",
      "Earned value",
      "Actual cost",
    ]);
    expect(series[0]?.data?.at(-1)).toEqual(["2026-06-30T00:00:00Z", "100000.00"]);
    expect(series[1]?.data?.at(-1)).toEqual(["2026-03-16T00:00:00Z", "0.00"]);
    // No step, no cash out: neither a mark nor a table of them.
    expect(series).toHaveLength(3);
    expect(screen.queryByRole("table", { name: "Cash out by month" })).toBeNull();
    expect(screen.getByText(/^Computed on/)).toBeInTheDocument();
  });
});
