// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { getInstanceByDom } from "echarts/core";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { roomForCharts } from "@/test/chart-room";

import {
  Chart,
  type ChartOption,
  type ChartPalette,
  curve,
  GAP,
  monthTicks,
  wrapLines,
} from "./chart";

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

// Each drawing has the room a page gives it: ECharts measures it as it draws.
roomForCharts();

describe("the envelope of the charts", () => {
  it("is a figure named by its caption, its drawing an image described in a sentence, its values a table [WF-IHM-0100-A]", async () => {
    const { container } = drawn(line);
    expect(screen.getByRole("figure", { name: "Indice" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Une courbe de deux points." })).toBeInTheDocument();
    expect(screen.getByText("Valeurs du graphique")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "0,8" })).toBeInTheDocument();
    // Offered for export only when its caller says what the image is to say of itself.
    expect(screen.queryByRole("button", { name: "Exporter en PNG" })).toBeNull();
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
    // The legend names the series it lists: an entry for no series is a warning of ECharts.
    const legended = (palette: ChartPalette): ChartOption => ({
      ...line(palette),
      series: [
        {
          name: "Projet",
          ...curve(palette, 0, [
            ["a", "0.8"],
            ["b", "0.9"],
          ]),
        },
      ],
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
    // The drawing has the room a page gives it (`roomForCharts`), without which ECharts has none
    // to write a name in.
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
    expect(Object.keys(palette ?? {})).toEqual([
      "series",
      "text",
      "mark",
      "axis",
      "grid",
      "background",
      "font",
    ]);
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
      "text-background",
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
    background: "background",
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

describe("the ticks of an axis of time", () => {
  const iso = (ticks: number[]) => ticks.map((tick) => new Date(tick).toISOString().slice(0, 10));

  it("falls on the first of each month, from the month of the earliest instant to the one after the latest", () => {
    expect(iso(monthTicks(["2026-03-16T14:05:00Z", "2026-01-31T23:00:00Z"], true))).toEqual([
      "2026-01-01",
      "2026-02-01",
      "2026-03-01",
      "2026-04-01",
    ]);
  });

  it("lengthens its step over a long range, a step falling on a multiple of it from January", () => {
    const ticks = iso(monthTicks(["2020-05-10T00:00:00Z", "2031-02-01T00:00:00Z"], true));
    expect(ticks).toEqual([
      "2020-01-01",
      "2021-01-01",
      "2022-01-01",
      "2023-01-01",
      "2024-01-01",
      "2025-01-01",
      "2026-01-01",
      "2027-01-01",
      "2028-01-01",
      "2029-01-01",
      "2030-01-01",
      "2031-01-01",
      "2032-01-01",
    ]);
    const quarters = iso(monthTicks(["2026-02-10T00:00:00Z", "2028-08-01T00:00:00Z"], true));
    expect(quarters[0]).toBe("2026-01-01");
    expect(quarters.length).toBeLessThanOrEqual(13);
    expect(new Set(quarters.map((tick) => tick.slice(5)))).toEqual(
      new Set(["01-01", "04-01", "07-01", "10-01"]),
    );
  });

  it("falls, at a step of several years, on the years that are a multiple of it (#415)", () => {
    // Fifteen years from 2025: every two years, from the even year before.
    const biennial = iso(monthTicks(["2025-05-10T00:00:00Z", "2040-02-01T00:00:00Z"], true));
    expect(biennial).toEqual([
      "2024-01-01",
      "2026-01-01",
      "2028-01-01",
      "2030-01-01",
      "2032-01-01",
      "2034-01-01",
      "2036-01-01",
      "2038-01-01",
      "2040-01-01",
      "2042-01-01",
    ]);
    // Twenty-nine years from 2023: every five years, from the year a multiple of five before.
    const lustral = iso(monthTicks(["2023-05-10T00:00:00Z", "2052-02-01T00:00:00Z"], true));
    expect(lustral.map((tick) => tick.slice(0, 4))).toEqual([
      "2020",
      "2025",
      "2030",
      "2035",
      "2040",
      "2045",
      "2050",
      "2055",
    ]);
  });

  it.each(["America/Los_Angeles", "Asia/Tokyo"])(
    "falls on the first of the month in the local time of the workstation for an axis of instants, under %s",
    (zone) => {
      vi.stubEnv("TZ", zone);
      try {
        const [first] = monthTicks(["2026-03-16T14:05:00Z"], false);
        expect(first).toBe(new Date(2026, 2, 1).getTime());
        expect(first).not.toBe(Date.UTC(2026, 2, 1));
        // Two in the morning in UTC on 1 March is still February west of Greenwich.
        const [month] = monthTicks(["2026-03-01T02:00:00Z"], false);
        expect(new Date(month ?? 0).getMonth()).toBe(zone === "Asia/Tokyo" ? 2 : 1);
      } finally {
        vi.unstubAllEnvs();
      }
    },
  );

  it("writes thirteen ticks at most, its step lengthened when the alignment on January would add one", () => {
    // Thirty-five months from March: every third month would be thirteen ticks from March, one
    // more aligned on January (#290).
    const ticks = iso(monthTicks(["2026-03-10T00:00:00Z", "2029-01-15T00:00:00Z"], true));
    expect(ticks.length).toBeLessThanOrEqual(13);
    expect(ticks[0]).toBe("2026-01-01");
    expect(new Set(ticks.map((tick) => tick.slice(5)))).toEqual(new Set(["01-01", "07-01"]));
  });

  it("has none without an instant", () => {
    expect(monthTicks([], true)).toEqual([]);
  });
});

describe("the lines of the head of an exported image", () => {
  // A measure of ten pixels a letter.
  const measure = (text: string) => text.length * 10;

  it("cut a text at its spaces within the width, and a word wider than it within the word", () => {
    expect(wrapLines("Plan de charge du projet", 100, measure)).toEqual([
      "Plan de",
      "charge du",
      "projet",
    ]);
    expect(wrapLines("Modernisation", 50, measure)).toEqual(["Moder", "nisat", "ion"]);
    expect(wrapLines("Court", 100, measure)).toEqual(["Court"]);
  });
});
