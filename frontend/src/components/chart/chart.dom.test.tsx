// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { getInstanceByDom } from "echarts/core";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";

import { Chart, type ChartOption, type ChartPalette, curve, GAP } from "./chart";

/** A chart of one series of two points, its option recorded with each palette it is drawn in. */
function drawn(option: (palette: ChartPalette) => ChartOption, note?: string) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <Chart title="Indice" description="Une courbe de deux points." note={note} option={option}>
        <table>
          <tbody>
            <tr>
              <td>0,8</td>
            </tr>
          </tbody>
        </table>
      </Chart>
    </NextIntlClientProvider>,
  );
}

/** The option of a line of two points, in the colours of the palette. */
function line(palette: ChartPalette): ChartOption {
  return {
    xAxis: { type: "category", data: ["a", "b"] },
    yAxis: { type: "value" },
    series: [
      curve(palette, 0, [
        ["a", "0.8"],
        ["b", "0.9"],
      ]),
    ],
  };
}

afterEach(() => {
  document.documentElement.removeAttribute("data-theme");
  vi.restoreAllMocks();
});

describe("the envelope of the charts", () => {
  it("is a figure named by its caption, its drawing an image described in a sentence, its values a table [WF-IHM-0100-A]", async () => {
    const { container } = drawn(line);
    expect(screen.getByRole("figure", { name: "Indice" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Une courbe de deux points." })).toBeInTheDocument();
    expect(screen.getByText("Valeurs du graphique")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "0,8" })).toBeInTheDocument();
    await expectAccessible(container);
  });

  it("draws in SVG, with the option aria of ECharts on and the description of the chart", async () => {
    const option = vi.fn(line);
    drawn(option);
    const image = screen.getByRole("img", { name: "Une courbe de deux points." });
    await waitFor(() => {
      expect(image.querySelector("svg")).not.toBeNull();
    });
    expect(option).toHaveBeenCalledOnce();
    expect(image).toHaveAttribute("aria-label", "Une courbe de deux points.");
  });

  it("makes the entries of its legend inert: no series is hidden by a click the keyboard cannot give [WF-IHM-0100-A]", async () => {
    const legended = (palette: ChartPalette): ChartOption => ({
      ...line(palette),
      legend: { data: ["Projet"], selectedMode: "multiple" },
    });
    drawn(legended);
    const image = screen.getByRole("img", { name: "Une courbe de deux points." });
    await waitFor(() => {
      expect(image.querySelector("svg")).not.toBeNull();
    });
    const { legend } = getInstanceByDom(image)?.getOption() ?? {};
    expect(legend).toMatchObject([{ data: ["Projet"], selectedMode: false }]);
  });

  it("draws at once, without animation, and names each of twenty curves at its end [WF-IHM-0100-A]", async () => {
    const names = Array.from({ length: 20 }, (_, rank) => `Courbe ${(rank + 1).toString()}`);
    const many = (palette: ChartPalette): ChartOption => ({
      xAxis: { type: "category", data: ["a", "b"] },
      yAxis: { type: "value" },
      series: names.map((name, rank) => ({
        name,
        ...curve(palette, rank, [
          ["a", "1"],
          ["b", (rank + 1).toString()],
        ]),
      })),
    });
    // happy-dom lays nothing out: the drawing is given the size a page would give it, without
    // which ECharts has no room to write a name in.
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(600);
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(300);
    drawn(many);
    const image = screen.getByRole("img", { name: "Une courbe de deux points." });
    await waitFor(() => {
      expect(image.querySelector("svg")).not.toBeNull();
    });
    expect(getInstanceByDom(image)?.getOption()).toMatchObject({ animation: false });
    const labels = [...image.querySelectorAll("svg text")].map((text) => text.textContent);
    for (const name of names) {
      expect(labels).toContain(name);
    }
  });

  it("says under its caption what it is handed to say: the date of its values", () => {
    drawn(line, "Calculé le 16 mars 2026");
    const figure = screen.getByRole("figure", { name: "Indice" });
    expect(figure).toHaveTextContent(/^IndiceCalculé le 16 mars 2026/);
  });

  it("reads its colours from the tokens of the charter, and draws again in the mode the account forces", async () => {
    const option = vi.fn(line);
    drawn(option);
    await waitFor(() => {
      expect(option).toHaveBeenCalledOnce();
    });
    const [palette] = option.mock.calls[0] ?? [];
    expect(palette?.series).toHaveLength(4);
    expect(Object.keys(palette ?? {})).toEqual(["series", "text", "mark", "axis", "grid", "font"]);
    // Each colour is a probe painted by the class of its token, which the browser resolves.
    const probes = document.querySelectorAll("[data-probe]");
    expect([...probes].map((probe) => probe.className)).toEqual([
      "text-chart-1",
      "text-chart-2",
      "text-chart-3",
      "text-chart-4",
      "text-muted-foreground",
      "text-foreground",
      "text-input",
      "text-border",
    ]);
    document.documentElement.setAttribute("data-theme", "dark");
    await waitFor(() => {
      expect(option).toHaveBeenCalledTimes(2);
    });
  });

  it("lets go of ECharts once it is gone: a change of mode draws nothing more", async () => {
    const option = vi.fn(line);
    const { unmount } = drawn(option);
    await waitFor(() => {
      expect(option).toHaveBeenCalledOnce();
    });
    unmount();
    document.documentElement.setAttribute("data-theme", "light");
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(option).toHaveBeenCalledOnce();
  });
});

describe("the look of a curve", () => {
  const palette: ChartPalette = {
    series: ["one", "two", "three", "four"],
    text: "text",
    mark: "mark",
    axis: "axis",
    grid: "grid",
    font: "font",
  };
  const points = [
    ["a", "0.9"],
    ["b", GAP],
  ] as const;

  it("names each of twenty curves at its end, its colour, symbol and stroke in turn", () => {
    const looks = Array.from({ length: 20 }, (_, rank) => curve(palette, rank, points));
    // The name of its own series (`{a}`) is what never repeats; names that would overlap move
    // apart.
    for (const look of looks) {
      expect(look.endLabel).toEqual({
        show: true,
        formatter: "{a}",
        width: 128,
        overflow: "truncate",
        lineHeight: 16,
      });
      expect(look.labelLayout).toEqual({ moveOverlap: "shiftY" });
    }
    const firstTwelve = looks.slice(0, 12).map((look) => `${look.symbol}/${look.lineStyle.type}`);
    expect(new Set(firstTwelve).size).toBe(12);
    expect(looks[4]?.color).toBe("one");
    expect(looks[0]?.data).toEqual([
      ["a", "0.9"],
      ["b", GAP],
    ]);
  });

  it("names no curve that has no drawn point: ECharts would stop moving the other names apart", () => {
    const look = curve(palette, 0, [
      ["a", GAP],
      ["b", GAP],
    ]);
    expect(look.endLabel.show).toBe(false);
  });
});
