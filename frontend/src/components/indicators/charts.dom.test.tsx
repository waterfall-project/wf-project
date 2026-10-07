// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import type { LineSeriesOption } from "echarts/charts";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ChartOption, ChartPalette } from "@/components/chart/chart";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
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
  // These charts draw lines alone.
  return (Array.isArray(series) ? series : []) as LineSeriesOption[];
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
    // The tests and commissioning have no schedule index the API could compute: no point, no
    // name drawn.
    expect(series.slice(0, -1).map((curve) => curve.endLabel?.show)).toEqual([
      true,
      true,
      false,
      true,
    ]);
    // A point for the reference, marked in progress, and one today: the offer, marked while
    // pricing, kept no index (WF-DAT-0040, #468).
    expect(series[0]?.data).toEqual([
      ["2026-02-01T09:00:00Z", "-"],
      ["2026-06-03T14:05:00Z", "0.9879"],
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
    expect(rows).toHaveLength(8);
    const [first, second] = rows;
    if (first === undefined || second === undefined) {
      throw new Error("The table lists no point");
    }
    const current = within(second);
    expect(current.getByRole("rowheader")).toHaveTextContent("Whole project");
    expect(current.getByText("Current revision")).toBeInTheDocument();
    expect(current.getByText("0.9879")).toBeInTheDocument();
    expect(current.getByText("Nominal")).toBeInTheDocument();
    const marked = within(first);
    expect(marked.getByText("Référence")).toBeInTheDocument();
    expect(
      marked.getByText("Not computable — No planned value at the calculation date."),
    ).toBeInTheDocument();
    expect(marked.queryByText(/Nominal|Watch|Alert/)).toBeNull();
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
    // A milestone that holds draws a horizontal line; one completed ends on the diagonal.
    expect(series[0]?.data).toEqual([
      ["2025-12-15T16:00:00Z", "2026-04-24T00:00:00Z"],
      ["2026-02-01T09:00:00Z", "2026-04-24T00:00:00Z"],
      ["2026-04-24T00:00:00Z", "2026-04-24T00:00:00Z"],
    ]);
    expect(series[1]?.data).toEqual([
      ["2026-02-01T09:00:00Z", "2026-06-30T00:00:00Z"],
      ["2026-06-03T14:05:00Z", "2026-06-30T00:00:00Z"],
    ]);
    expect(series[2]?.data).toEqual([
      ["2025-12-15T16:00:00Z", "2025-12-15T16:00:00Z"],
      ["2026-06-03T14:05:00Z", "2026-06-03T14:05:00Z"],
    ]);
    expect(series.map((each) => each.endLabel?.show)).toEqual([true, true, true]);
  });

  it("lists each forecast as a date of planning, and whether its milestone is completed [WF-IND-0090-A]", async () => {
    const { container } = english(<MilestoneChart tracking={TRACKING} provenance={PROVENANCE} />);
    const rows = screen.getAllByRole("row").slice(1);
    // The instant of a marking shows in the local time of the workstation (WF-INTF-0180), the
    // day itself moving with it: 15 December at 16:00 UTC is 16 December in Tokyo. The instants
    // are formatted as the screen formats them; the forecasts, dates of planning, are not.
    const [studies, factory] = TRACKING.milestones;
    const at = (point: { readonly marked_at: string } | undefined) =>
      formatTimestamp(point?.marked_at ?? "", "en");
    expect(rows.map((row) => row.textContent)).toEqual([
      // Completed on 24 April: its date of completion beside each forecast.
      ...(studies?.points ?? []).map(
        (point) => `Réception des études${at(point)}24 Apr 202624 Apr 2026`,
      ),
      ...(factory?.points ?? []).map(
        (point) => `Réception usine${at(point)}30 Jun 2026Not completed`,
      ),
    ]);
    expect(rows).toHaveLength(5);
    const figure = screen.getByRole("figure", { name: "Time/time diagram" });
    expect(figure.querySelector("time")).toHaveAttribute("datetime", TRACKING.context.computed_at);
    await expectAccessible(container);
  });

  it("starts the diagonal at the earliest marking of any milestone, not at the first one listed [WF-IND-0090-A]", () => {
    // The witness tracking, its first milestone at its completion only and the points of the
    // second in reverse: the earliest marking is the last point of the second.
    const [studies, factory] = TRACKING.milestones;
    if (studies === undefined || factory === undefined) {
      throw new Error("the example tracks two milestones");
    }
    const tracking = {
      ...TRACKING,
      milestones: [
        { ...studies, points: studies.points.slice(2) },
        { ...factory, points: [...factory.points].reverse() },
      ],
    };
    english(<MilestoneChart tracking={tracking} provenance={PROVENANCE} />);
    const diagonal = lastSeries().at(-1);
    expect(diagonal?.name).toBe("Equal dates");
    expect(diagonal?.data).toEqual([
      ["2026-02-01T09:00:00Z", "2026-02-01T09:00:00Z"],
      ["2026-06-03T14:05:00Z", "2026-06-03T14:05:00Z"],
    ]);
  });

  it("places and writes the ticks of its axes in UTC, whatever the zone of the workstation", () => {
    english(<MilestoneChart tracking={TRACKING} provenance={PROVENANCE} />);
    const option = lastOption();
    expect(option?.useUTC).toBe(true);
    const yAxis = option?.yAxis as { axisLabel: { formatter: (value: number) => string } };
    expect(yAxis.axisLabel.formatter(Date.parse("2026-05-01T00:00:00Z"))).toBe("May 2026");
    // The markings run from 15 December to 3 June: a tick on the first of each month, from
    // December to July, in UTC.
    const xAxis = option?.xAxis as { axisLabel: { customValues: number[] }; min: number };
    expect(xAxis.axisLabel.customValues.map((tick) => new Date(tick).toISOString())).toEqual([
      "2025-12-01T00:00:00.000Z",
      "2026-01-01T00:00:00.000Z",
      "2026-02-01T00:00:00.000Z",
      "2026-03-01T00:00:00.000Z",
      "2026-04-01T00:00:00.000Z",
      "2026-05-01T00:00:00.000Z",
      "2026-06-01T00:00:00.000Z",
      "2026-07-01T00:00:00.000Z",
    ]);
    expect(xAxis.min).toBe(Date.parse("2025-12-01T00:00:00Z"));
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
      // The amendment 1, which made the revision « Référence » the reference.
      "Steps of the reference budget",
    ]);
    expect(series[1]?.data?.slice(-2)).toEqual([
      ["2026-05-18T00:00:00Z", "105400.00"],
      ["2026-06-03T00:00:00Z", "105400.00"],
    ]);
    expect(series[2]?.data?.[0]).toEqual(["2026-06-03T00:00:00Z", "105400.00"]);
    expect(series[2]?.data?.at(-1)).toEqual(["2027-01-01T00:00:00Z", "126934.56"]);
    expect(series[0]?.data?.at(-1)).toEqual(["2027-01-01T00:00:00Z", "120834.56"]);
    // The actual cost cumulates dated documents: by steps; the budget and the projection, spread
    // over durations, by lines.
    expect(series.slice(0, 3).map((each) => each.step)).toEqual([undefined, "end", undefined]);
    // Dates of planning: the ticks are placed at midnight in UTC, as the points.
    expect(lastOption()?.useUTC).toBe(true);
  });

  it("marks a step of the reference budget at its date, named by its cause, and lists it [WF-IND-0100-A]", () => {
    curves("cost_curve_amendment");
    const steps = lastSeries().at(-1);
    expect(steps?.data).toEqual([]);
    const marks = steps?.markLine?.data as { xAxis: string; name: string }[] | undefined;
    expect(marks?.map(({ xAxis, name }) => [name, xAxis])).toEqual([
      ["Amendment", "2026-02-01T00:00:00Z"],
      ["Amendment", "2026-03-10T00:00:00Z"],
    ]);
    // The step is vertical: the curve bears the budget before and after it at its date.
    expect(lastSeries()[0]?.data?.slice(3, 5)).toEqual([
      ["2026-03-10T00:00:00Z", "23333.33"],
      ["2026-03-10T00:00:00Z", "26833.33"],
    ]);
    // Its two rows in the table of the values are told apart by their heading (#290).
    expect(
      screen.getByRole("row", { name: "Reference budget, before the step 10 Mar 2026 23,333.33" }),
    ).toBeVisible();
    expect(
      screen.getByRole("row", { name: "Reference budget, after the step 10 Mar 2026 26,833.33" }),
    ).toBeVisible();
    expect(screen.queryAllByRole("row", { name: /^Reference budget 10 Mar 2026/ })).toHaveLength(0);
    const table = screen.getByRole("table", { name: "Steps of the reference budget" });
    // The amount of the step, not the budget after it (26,833.33).
    expect(within(table).getByRole("columnheader", { name: "Amount of the step" })).toBeVisible();
    expect(
      within(table).getByRole("row", { name: "10 Mar 2026 Amendment 15,000.00" }),
    ).toBeVisible();
  });

  it("lists the cash out by month the API gives with the payment delays, the shifted points as given [WF-IND-0100-A]", async () => {
    const { container, data } = curves("cost_curve_payment_delays");
    // The studies, paid a month after their work: nothing paid out by the end of March.
    expect(lastSeries()[0]?.data).toContainEqual(["2026-03-31T00:00:00Z", "0.00"]);
    const table = screen.getByRole("table", { name: "Cash out by month" });
    expect(
      within(table)
        .getAllByRole("row")
        .map((row) => row.textContent)
        .slice(0, 5),
    ).toEqual([
      "MonthPaid outTo pay out",
      "March 20261,400.000.00",
      "April 2026101,600.000.00",
      "May 20262,400.000.00",
      "June 20260.001,700.00",
    ]);
    expect(data.cash_out_by_month).toHaveLength(11);
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
    expect(series[0]?.data?.at(-1)).toEqual(["2027-01-01T00:00:00Z", "120834.56"]);
    expect(series[1]?.data?.at(-1)).toEqual(["2026-06-03T00:00:00Z", "100000.00"]);
    // A task completed makes a step in the earned value at its date, as the actual cost at the
    // date of a document: both by steps, the planned value by a line.
    expect(series.map((each) => each.step)).toEqual([undefined, "end", "end"]);
    // No step, no cash out: neither a mark nor a table of them.
    expect(series).toHaveLength(3);
    expect(screen.queryByRole("table", { name: "Cash out by month" })).toBeNull();
    expect(screen.getByText(/^Computed on/)).toBeInTheDocument();
  });
});
