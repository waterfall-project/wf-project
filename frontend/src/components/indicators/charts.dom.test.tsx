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
