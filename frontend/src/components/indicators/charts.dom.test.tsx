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

import { IndexChart, type IndexHistory } from "./index-chart";
import { MilestoneChart, type MilestoneTracking } from "./milestone-chart";

const drawn = vi.hoisted(() => ({ options: [] as ((palette: ChartPalette) => ChartOption)[] }));

// The envelope is tested on its own (chart.dom.test.tsx): here, what a chart is handed to draw.
vi.mock("@/components/chart/chart", async (actual) => ({
  ...(await actual<typeof import("@/components/chart/chart")>()),
  Chart: ({
    title,
    description,
    option,
    children,
  }: {
    title: string;
    description: string;
    option: (palette: ChartPalette) => ChartOption;
    children: ReactNode;
  }) => {
    drawn.options.push(option);
    return (
      <figure aria-label={title}>
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
  font: "font",
};

const HISTORY = example("index_history") as IndexHistory;

/**
 * The tracking of the milestones of the witness project: the contract cites no example for
 * `getMilestoneTracking` yet, so the data is written here in the shape of its schema, with the
 * milestones, the revisions and the date of calculation of the other examples.
 */
const TRACKING: MilestoneTracking = {
  context: {
    revision_id: "01926f3a-7c00-7000-8000-000000000102",
    revision_status: "draft",
    computed_at: "2026-03-16T14:05:00Z",
    scope: "project",
    is_stored: false,
  },
  milestones: [
    {
      lineage_id: "01926f3a-7c00-7000-8000-000000000625",
      label: "Réception des études",
      completed_on: null,
      points: [
        { marked_at: "2025-12-15T16:00:00Z", forecast_date: "2026-04-10" },
        { marked_at: "2026-03-16T14:05:00Z", forecast_date: "2026-04-24" },
      ],
    },
    {
      lineage_id: "01926f3a-7c00-7000-8000-000000000612",
      label: "Réception usine",
      completed_on: "2026-03-02",
      points: [{ marked_at: "2025-12-15T16:00:00Z", forecast_date: "2026-03-02" }],
    },
  ],
};

/** Render in English. */
function english(node: ReactNode) {
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {node}
    </NextIntlClientProvider>,
  );
}

/** The series of the last option a chart was handed, drawn in the palette of the test. */
function lastSeries() {
  const option = drawn.options.at(-1);
  const series = option?.(PALETTE).series;
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
    ]);
    expect(series[0]?.data).toEqual([
      ["2025-12-15T16:00:00Z", "-"],
      ["2026-02-01T09:00:00Z", "-"],
      ["2026-03-16T14:05:00Z", "0"],
    ]);
  });

  it("draws the thresholds of its index from the reference, as the API gave them [WF-IND-0130-A]", () => {
    english(<IndexChart kind="cost" history={HISTORY} />);
    const [project] = lastSeries();
    const marks = project?.markLine?.data as { yAxis: string; name: string }[] | undefined;
    expect(marks?.map(({ yAxis, name }) => [name, yAxis])).toEqual([
      ["Watch threshold", "0.9"],
      ["Alert threshold", "0.8"],
    ]);
    expect(
      screen.getByText(/with the watch threshold at 0\.9 and the alert threshold at 0\.8/),
    ).toBeInTheDocument();
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

describe("the tracking of the milestones", () => {
  it("draws each milestone by the dates its revisions forecast, at midnight in UTC, and the diagonal of equal dates up to the date of calculation [WF-IND-0090-A]", () => {
    english(<MilestoneChart tracking={TRACKING} />);
    const series = lastSeries();
    expect(series.map((each) => each.name)).toEqual([
      "Réception des études",
      "Réception usine",
      "Equal dates",
    ]);
    expect(series[0]?.data).toEqual([
      ["2025-12-15T16:00:00Z", "2026-04-10T00:00:00Z"],
      ["2026-03-16T14:05:00Z", "2026-04-24T00:00:00Z"],
    ]);
    expect(series[2]?.data).toEqual([
      ["2025-12-15T16:00:00Z", "2025-12-15T16:00:00Z"],
      ["2026-03-16T14:05:00Z", "2026-03-16T14:05:00Z"],
    ]);
  });

  it("lists each forecast as a date of planning, and when a milestone was completed [WF-IND-0090-A]", async () => {
    const { container } = english(<MilestoneChart tracking={TRACKING} />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringMatching(/^Réception des études.*10 Apr 2026Not completed$/),
      expect.stringMatching(/^Réception des études.*24 Apr 2026Not completed$/),
      expect.stringMatching(/^Réception usine.*2 Mar 2026$/),
    ]);
    expect(rows[2]).toHaveTextContent("2 Mar 20262 Mar 2026");
    await expectAccessible(container);
  });

  it("formats its axes in the language of the interface, the forecasts in UTC", () => {
    english(<MilestoneChart tracking={TRACKING} />);
    const option = drawn.options.at(-1)?.(PALETTE);
    const yAxis = option?.yAxis as { axisLabel: { formatter: (value: number) => string } };
    // The first of May at midnight in UTC is still in May, whatever the zone of the workstation.
    expect(yAxis.axisLabel.formatter(Date.parse("2026-05-01T00:00:00Z"))).toBe("May 2026");
  });
});
