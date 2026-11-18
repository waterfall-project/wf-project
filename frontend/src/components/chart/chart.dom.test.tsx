// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, renderHook, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { getInstanceByDom, init } from "echarts/core";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import { expectAccessible } from "@/test/axe";
import { roomForCharts } from "@/test/chart-room";

import {
  bars,
  Chart,
  type ChartOption,
  type ChartPalette,
  curve,
  exportPng,
  GAP,
  monthTicks,
  presented,
  timeAxis,
  useProvenance,
  valueAxis,
  wrapLines,
} from "./chart";
import { ChartPatternsProvider } from "./patterns";

// `init` stays ECharts', except where a test takes it over to read the option an export hands it.
vi.mock("echarts/core", async (importOriginal) => {
  const actual = await importOriginal<typeof import("echarts/core")>();
  return { ...actual, init: vi.fn(actual.init) };
});

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

  it("holds the table of its values in a group named after them, in the order of the keyboard", () => {
    drawn(line);
    const values = screen.getByRole("group", { name: "Valeurs du graphique" });
    expect(values).toHaveAttribute("tabindex", "0");
    expect(values).toContainElement(screen.getByRole("cell", { name: "0,8" }));
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
      "card",
      "zones",
      "font",
      "patterns",
    ]);
    // Without the preference of the account, no patterns (WF-IHM-0070).
    expect(palette?.patterns).toBe(false);
    expect(Object.keys(palette?.zones ?? {})).toEqual(["nominal", "watch", "alert"]);
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
      "text-card",
      "text-signal-nominal",
      "text-signal-watch",
      "text-signal-alert",
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
    card: "card",
    zones: { nominal: "nominal", watch: "watch", alert: "alert" },
    font: "font",
    patterns: false,
  };
  const points = [
    ["a", "0.9"],
    ["b", GAP],
  ] as const;

  it("names each of twenty curves at its end, its colour and stroke in turn, a plain dot on its points without the patterns [WF-IHM-0070-A]", () => {
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
      // The symbols wait for the preference: a small dot on each point of every curve.
      expect([look.symbol, look.symbolSize]).toEqual(["circle", 5]);
      // Under the pointer, the curve stands out and the others fade.
      expect(look.emphasis).toEqual({ focus: "series" });
    }
    // The colour and the stroke in turn: the fifth curve is not the first.
    const firstTwelve = looks.slice(0, 12).map((look) => `${look.color}/${look.lineStyle.type}`);
    expect(new Set(firstTwelve).size).toBe(12);
    expect(looks[4]?.color).toBe("one");
    expect(looks[0]?.data).toEqual([
      ["a", "0.9"],
      ["b", GAP],
    ]);
  });

  it("marks the points of a curve with the symbol of its rank when the account asks for the patterns, its stroke changing once the symbols are taken [WF-IHM-0070-A]", () => {
    const looks = Array.from({ length: 12 }, (_, rank) =>
      curve({ ...palette, patterns: true }, rank, points),
    );
    expect(looks.slice(0, 4).map((look) => look.symbol)).toEqual([
      "circle",
      "triangle",
      "rect",
      "diamond",
    ]);
    expect(looks[0]?.symbolSize).toBe(8);
    const told = looks.map((look) => `${look.symbol}/${look.lineStyle.type}`);
    expect(new Set(told).size).toBe(12);
  });

  it("names no curve that has no drawn point: ECharts would stop moving the other names apart", () => {
    const look = curve(palette, 0, [
      ["a", GAP],
      ["b", GAP],
    ]);
    expect(look.endLabel.show).toBe(false);
  });
});

describe("the presentation common to the charts (#3097)", () => {
  const palette: ChartPalette = {
    series: ["one", "two", "three", "four"],
    text: "text",
    mark: "mark",
    axis: "axis",
    grid: "grid",
    background: "background",
    card: "card",
    zones: { nominal: "nominal", watch: "watch", alert: "alert" },
    font: "font",
    patterns: false,
  };

  it("draws slim bars in plain colours, each part rounded and parted from the next by a thread of the colour of the page", () => {
    const look = bars(palette, 1);
    expect(look).toMatchObject({
      type: "bar",
      color: "two",
      barWidth: "50%",
      barMaxWidth: 28,
      itemStyle: { borderRadius: 3, borderColor: "background", borderWidth: 1 },
      emphasis: { focus: "series" },
    });
    // Plain: no pattern unless the account asks for it.
    expect(look.itemStyle).not.toHaveProperty("decal");
  });

  it("bears on the bars the pattern of the symbol of their rank, in the colour of the page, when the account asks for it [WF-IHM-0070-A]", () => {
    const patterned = { ...palette, patterns: true };
    const decals = [0, 1, 2, 3].map((rank) => {
      const { itemStyle } = bars(patterned, rank);
      return "decal" in itemStyle ? itemStyle.decal : undefined;
    });
    expect(decals).toEqual(
      ["circle", "triangle", "rect", "diamond"].map((symbol) => ({
        symbol,
        symbolSize: 0.6,
        color: "background",
      })),
    );
  });

  it("reads its values across the plot, by a grid of light dashes, on an axis without line nor tick, and draws no vertical line", () => {
    const values = valueAxis(palette, (value) => `${value.toString()} h`);
    expect(values).toMatchObject({
      type: "value",
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "text" },
      splitLine: { lineStyle: { color: "grid", type: "dashed" } },
    });
    expect(values.axisLabel.formatter(12)).toBe("12 h");
    expect(timeAxis(palette, "fr", ["2026-06-01T00:00:00Z"], true).splitLine).toEqual({
      show: false,
    });
  });

  // aucune exigence : propre à l'US (US-2160, les marques propres aux chronologies ne changent pas).
  it("keeps the vertical lines of a timeline, which asks for them", () => {
    expect(timeAxis(palette, "fr", ["2026-06-01T00:00:00Z"], true, true).splitLine).toEqual({
      lineStyle: { color: "grid" },
    });
  });

  // aucune exigence : propre à l'US (US-2160, le style de carte vaut pour chaque infobulle).
  it("puts each tooltip of a list in a card", () => {
    const option = presented({ tooltip: [{ trigger: "axis" }, { trigger: "item" }] }, palette);
    expect(option.tooltip).toMatchObject([
      { trigger: "axis", backgroundColor: "card", borderRadius: 8 },
      { trigger: "item", backgroundColor: "card", borderRadius: 8 },
    ]);
  });

  it("puts its legend at the top left, an entry a dot of its colour, and its tooltip in a card, on the screen and in the image", () => {
    const option = presented(
      {
        legend: { top: 0, data: ["Rôle"] },
        tooltip: { trigger: "axis" },
        series: [{ name: "Rôle", ...bars(palette, 0), data: [] }],
      },
      palette,
    );
    expect(option.legend).toEqual({
      left: 0,
      itemGap: 16,
      textStyle: { color: "text" },
      icon: "circle",
      itemWidth: 10,
      itemHeight: 10,
      top: 0,
      data: ["Rôle"],
      selectedMode: false,
    });
    expect(option.tooltip).toMatchObject({
      trigger: "axis",
      backgroundColor: "card",
      borderColor: "grid",
      borderWidth: 1,
      borderRadius: 8,
      shadowColor: "grid",
      textStyle: { color: "mark", fontFamily: "font" },
    });
  });

  it("shows in its legend the mark each series is drawn with when the account asks for the patterns [WF-IHM-0070-A]", () => {
    const option = presented({ legend: { data: ["Rôle"] } }, { ...palette, patterns: true });
    // No dot of its own: ECharts draws the bar with its pattern, the curve with its symbol.
    expect(option.legend).not.toHaveProperty("icon");
    expect(option.legend).toMatchObject({ left: 0, itemWidth: 22, itemHeight: 14 });
  });

  it("draws in its legend the bar with its pattern, as the account asked for them [WF-IHM-0070-A]", async () => {
    const barred = (palette: ChartPalette): ChartOption => ({
      legend: { data: ["Rôle"] },
      xAxis: { type: "category", data: ["a"] },
      yAxis: { type: "value" },
      series: [{ name: "Rôle", ...bars(palette, 1), data: [1] }],
    });
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <ChartPatternsProvider patterns>
          <Chart title="Charge" description="Une barre." option={barred}>
            <p>1</p>
          </Chart>
        </ChartPatternsProvider>
      </NextIntlClientProvider>,
    );
    const image = screen.getByRole("img", { name: "Une barre." });
    await waitFor(() => {
      expect(image.querySelector("svg")).not.toBeNull();
    });
    // The legend is the bar itself, 22 by 14, not a dot, and the decal of the series is among the
    // patterns of the drawing: the bar and its entry are told apart without their colour.
    const [legend] = (getInstanceByDom(image)?.getOption().legend ?? []) as {
      itemWidth: number;
      itemHeight: number;
    }[];
    expect(legend).toMatchObject({ itemWidth: 22, itemHeight: 14 });
    expect(image.querySelectorAll("pattern").length).toBeGreaterThanOrEqual(1);
  });

  it("follows the preference of the account, one point for every chart, and draws again when it changes [WF-ADM-0040-A]", async () => {
    const option = vi.fn(line);
    const figure = (patterns: boolean) => (
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <ChartPatternsProvider patterns={patterns}>
          <Chart title="Indice" description="Une courbe de deux points." option={option}>
            <p>0,8</p>
          </Chart>
        </ChartPatternsProvider>
      </NextIntlClientProvider>
    );
    const { rerender } = render(figure(true));
    await waitFor(() => {
      expect(option).toHaveBeenCalledOnce();
    });
    expect(option.mock.calls[0]?.[0].patterns).toBe(true);
    rerender(figure(false));
    await waitFor(() => {
      expect(option).toHaveBeenCalledTimes(2);
    });
    expect(option.mock.calls[1]?.[0].patterns).toBe(false);
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

describe("the option an exported image is drawn from (WF-IHM-0130)", () => {
  const palette: ChartPalette = {
    series: ["one", "two", "three", "four"],
    text: "text",
    mark: "mark",
    axis: "axis",
    grid: "grid",
    background: "background",
    card: "card",
    zones: { nominal: "nominal", watch: "watch", alert: "alert" },
    font: "font",
    patterns: false,
  };
  const computedAt = "2026-02-01T09:00:00Z";

  /** The option ECharts is handed when an image is exported under a provenance. */
  function optionExported(detail?: string) {
    const { result } = renderHook(
      () =>
        useProvenance(
          {
            project: "Projet témoin",
            code: "PRJ-001",
            revision: "Révision 102",
            ...(detail === undefined ? {} : { detail }),
          },
          "Courbe en S",
          computedAt,
          "courbe-en-s",
        ),
      {
        wrapper: ({ children }) => (
          <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
            {children}
          </NextIntlClientProvider>
        ),
      },
    );
    const setOption = vi.fn();
    const chart = { setOption, getDataURL: () => "data:,", dispose: vi.fn() };
    vi.mocked(init).mockImplementationOnce(() => chart as unknown as ReturnType<typeof init>);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    exportPng(line(palette), palette, result.current());
    expect(setOption).toHaveBeenCalledOnce();
    return setOption.mock.calls[0]?.[0] as { title: { text: string; subtext: string } };
  }

  it("carries, as the title and the subtitle of the image, the project, the revision and the date of calculation [WF-IHM-0130-A]", () => {
    const { title } = optionExported();
    expect(title.text).toBe("Courbe en S — Projet témoin");
    expect(title.subtext).toBe(
      `Révision : Révision 102 · Calculé le ${formatTimestamp(computedAt, "fr")}`,
    );
  });

  it("names, between the revision and the date, what else the chart is computed on [WF-IHM-0130-A]", () => {
    const { title } = optionExported("Base : budget de référence");
    expect(title.subtext).toBe(
      `Révision : Révision 102 · Base : budget de référence · Calculé le ${formatTimestamp(computedAt, "fr")}`,
    );
  });
});
