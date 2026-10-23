// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { ScatterSeriesOption } from "echarts/charts";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { updateChartPreferences } from "@/api/actions/preferences";
import type { components } from "@/api/generated/schema";
import type { Settled } from "@/api/problem";
import type { ChartPalette, ChartProps } from "@/components/chart/chart";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { roomForCharts } from "@/test/chart-room";
import { example } from "@/test/fixtures";

import type { RiskState } from "./address";
import { PortfolioRiskMatrix, ProjectRiskMatrix } from "./risk-bubble-chart";
import type { RiskMatrix } from "./risk-matrix";

type Schemas = components["schemas"];

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

// The server action that keeps the state of the chart: what it is asked, and the answer a test gives.
vi.mock("@/api/actions/preferences", () => ({ updateChartPreferences: vi.fn() }));

// The instance of the screen is the real one; the instances made and released are counted. The
// image is drawn on a canvas, which the simulated document does not paint: an instance in its
// place records what it is asked to draw.
const instances = vi.hoisted(() => ({ made: 0, disposed: 0, images: [] as unknown[] }));
vi.mock("echarts/core", async (actual) => {
  const echarts = await actual<typeof import("echarts/core")>();
  return {
    ...echarts,
    init: (...args: Parameters<typeof echarts.init>) => {
      if (args[2]?.renderer === "canvas") {
        return {
          setOption: () => undefined,
          getDataURL: (image: unknown) => {
            instances.images.push(image);
            return "data:image/png;base64,iVBORw0KGgo=";
          },
          dispose: () => undefined,
        };
      }
      instances.made += 1;
      const chart = echarts.init(...args);
      const dispose = chart.dispose.bind(chart);
      chart.dispose = () => {
        instances.disposed += 1;
        dispose();
      };
      return chart;
    },
  };
});

const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const PATHNAME = "/projects/p/revisions/r/risks";
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams("sort_by=provision_amount&sort_order=asc"),
}));

/** The colours and the font a chart is drawn in, as the probes would read them. */
const PALETTE: ChartPalette = {
  series: ["rgb(1, 1, 1)", "rgb(2, 2, 2)", "rgb(8, 8, 8)"],
  text: "rgb(3, 3, 3)",
  mark: "rgb(4, 4, 4)",
  axis: "rgb(5, 5, 5)",
  grid: "rgb(6, 6, 6)",
  background: "rgb(7, 7, 7)",
  zones: { nominal: "zone-nominal", watch: "zone-watch", alert: "zone-alert" },
  font: "sans-serif",
};

/** The ratio of a point, which the examples of the matrix give computable. */
function ratioOf(point: RiskMatrix["points"][number]): string | null | undefined {
  return point.severity_ratio.value;
}

const MATRIX = example("risk_matrix") as RiskMatrix;
const RISKS = example("volume/portfolio_risks") as Schemas["PortfolioRisks"];
const CABLING = "01926f3a-7c00-7000-8000-000000000751";
const DELIVERY = "01926f3a-7c00-7000-8000-000000000752";
const AUTOMATON = "01926f3a-7c00-7000-8000-000000000753";
const PROVENANCE = {
  project: "Modernisation du poste de commande",
  code: "PRJ-001",
  revision: "V1",
};

/** The matrix of a project in English, the states asked drawn. */
function project(states: readonly RiskState[] = [], matrix: RiskMatrix = MATRIX, folded = true) {
  charts.props = [];
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      <ProjectRiskMatrix
        matrix={matrix}
        states={states}
        provenance={PROVENANCE}
        computedAt="2026-06-03T14:05:00Z"
        folded={folded}
      />
    </NextIntlClientProvider>,
  );
}

/** The option the chart drew, in the palette above, with the series of bubbles and of zones. */
function drawn() {
  const option = charts.props.at(-1)?.option(PALETTE);
  const series = [option?.series].flat() as ScatterSeriesOption[];
  const [zones, ...bubbles] = series;
  return { option, zones, bubbles };
}

/** The `[probability, severity ratio]` of each bubble of a series, by the risk it stands for. */
function placed(series: ScatterSeriesOption | undefined) {
  return Object.fromEntries(
    (series?.data as { id: string; value: string[]; symbolSize: number }[] | undefined)?.map(
      (each) => [each.id, each.value] as const,
    ) ?? [],
  );
}

roomForCharts();

beforeEach(() => {
  router.push.mockClear();
  vi.mocked(updateChartPreferences).mockReset();
  vi.mocked(updateChartPreferences).mockResolvedValue({ kind: "done", data: null });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the risk matrix as a bubble chart", () => {
  it("is a figure named « Risk matrix » that lays each risk at its exact probability and severity ratio, one series for each state", () => {
    project();
    expect(screen.getByRole("figure", { name: "Risk matrix" })).toBeInTheDocument();
    const { option, bubbles } = drawn();
    expect(bubbles.map((each) => [each.type, each.name, each.symbol])).toEqual([
      ["scatter", "Identified", "circle"],
      ["scatter", "Occurred", "diamond"],
      ["scatter", "Dismissed", "triangle"],
    ]);
    // Placed at the values of the point, the strings of the API as they are, never rounded to a
    // cell nor read as floats: 0.000003 stays 0.000003.
    expect(placed(bubbles[0])).toEqual({ [CABLING]: ["0.4", "0.0191"] });
    expect(placed(bubbles[1])).toEqual({ [DELIVERY]: ["0.3", "0.000003"] });
    expect(placed(bubbles[2])).toEqual({ [AUTOMATON]: ["0.05", "0.1834"] });
    // The states are told apart by the shape of the bubble, and the legend names them.
    expect(option?.legend).toMatchObject({ data: ["Identified", "Occurred", "Dismissed"] });
  });

  it("sizes a bubble by the severity in amount, within bounds, the heaviest risk the largest bubble", () => {
    project();
    const { bubbles } = drawn();
    const [cabling, delivery, automaton] = bubbles.map(
      (each) => (each.data as { symbolSize: number }[])[0]?.symbolSize ?? Number.NaN,
    );
    // The heaviest of the three (12,000,000.00) is the largest, the lightest (200.00) the smallest.
    expect(automaton).toBe(40);
    expect(delivery).toBeGreaterThanOrEqual(12);
    expect(delivery).toBeLessThan(cabling ?? 0);
    expect(cabling).toBeLessThan(automaton ?? 0);
  });

  it("draws the sixteen zones as areas under the bubbles, from the bounds of the levels the server gives, the last level up to the end of the axis", () => {
    project();
    const { option, zones } = drawn();
    const areas = zones?.markArea?.data as unknown as [
      { name: string; xAxis: number; yAxis: number },
      { xAxis: number; yAxis: number },
    ][];
    expect(areas).toHaveLength(16);
    // The first cell: probability level 1 (0 to 10 %), severity level 1 (0 to 1 %), nominal.
    expect(areas[0]).toMatchObject([
      { name: "Nominal", xAxis: 0, yAxis: 0 },
      { xAxis: 0.1, yAxis: 0.01 },
    ]);
    // The last: the highest levels, unbounded, up to the end of both axes.
    const axis = option?.yAxis as { max: number };
    expect(areas[15]).toMatchObject([
      { name: "Alert", xAxis: 0.6, yAxis: 0.1 },
      { xAxis: 1, yAxis: axis.max },
    ]);
    // The axis reaches over the heaviest bubble (18.34 %) and the end of the last level.
    expect(axis.max).toBeGreaterThan(0.1834);
    expect(zones).toMatchObject({ silent: true, data: [] });
  });

  it("tells the zones apart without their colour: each is named in its area, its sides have a stroke of its own, two sides each [WF-IHM-0070-A]", () => {
    project();
    const { zones } = drawn();
    const areas = zones?.markArea?.data as unknown as [
      {
        name: string;
        label: { show: boolean };
        itemStyle: { color: string };
      },
      unknown,
    ][];
    const looks = areas.map(([area]) => [area.name, area.label.show]);
    // The left side and the lower side of each zone, in the stroke of the zone: a side shared by
    // two zones is the side of one of them only, never two strokes one over the other; the zones
    // of the last column and of the last row add their outer side, the right one or the upper one
    // — the corner has both —: 32 sides and 8 more, a frame all around the matrix.
    const edges = zones?.markLine?.data as unknown as [
      { name: string; coord: [number, number]; lineStyle: { type: string } },
      { coord: [number, number] },
    ][];
    expect(edges).toHaveLength(40);
    const along = (index: 0 | 1) =>
      edges.filter(([from, to]) => from.coord[index] === to.coord[index]);
    // The right sides, at the end of the probability axis: one for each of the four levels.
    expect(along(0).filter(([from]) => from.coord[0] === 1)).toHaveLength(4);
    // The upper sides, at the end of the severity axis, one for each of the four levels.
    const top = Math.max(...edges.map(([from]) => from.coord[1]));
    expect(along(1).filter(([from]) => from.coord[1] === top)).toHaveLength(4);
    expect(new Set(edges.map(([edge]) => [edge.name, edge.lineStyle.type].join(" ")))).toEqual(
      new Set(["Nominal solid", "Watch dashed", "Alert dotted"]),
    );
    // Named in its area when the band has room for a line: the four thinner bands of the lowest
    // severity level are not, and the stroke of their sides tells their zone.
    expect(looks.map(([, shown]) => shown)).toEqual(
      Array.from({ length: 16 }, (_, cell) => cell % 4 !== 0),
    );
    expect(new Set(looks.filter(([, shown]) => shown === true).map(([name]) => name))).toEqual(
      new Set(["Nominal", "Watch", "Alert"]),
    );
    // The colour of a zone is the token of its zone, read from the document.
    expect(areas.map(([area]) => area.itemStyle.color)).toContain("zone-alert");
    // The cells of the server stay in words under the chart, each with its signal and its count.
    const counts = screen.getByRole("table", {
      name: "Count of the risks by cell of the matrix, all states together",
      hidden: true,
    });
    expect(within(counts).getAllByRole("img", { hidden: true, name: "Alert" })).toHaveLength(3);
  });

  it("draws the risks in the states the address filters on, every one without a filter", () => {
    project(["occurred", "dismissed"]);
    const filtered = drawn();
    expect(filtered.bubbles.map((each) => each.name)).toEqual(["Occurred", "Dismissed"]);
    expect(Object.keys(placed(filtered.bubbles[0]))).toEqual([DELIVERY]);
    project([]);
    expect(drawn().bubbles).toHaveLength(3);
  });

  it("keeps the axis and the zones where they are whatever the states asked: the top of the axis is the matrix's, not the bubbles drawn's", () => {
    const zonesOf = () => {
      const { option, zones } = drawn();
      const areas = zones?.markArea?.data as unknown as [{ label: { show: boolean } }, unknown][];
      return {
        max: (option?.yAxis as { max: number }).max,
        shown: areas.map(([area]) => area.label.show),
      };
    };
    project([]);
    const every = zonesOf();
    project(["identified"]);
    expect(zonesOf()).toEqual(every);
    project(["occurred"]);
    expect(zonesOf()).toEqual(every);
  });

  it("counts the cells of every risk under the chart, whatever the states asked, and says so in the name of the table", () => {
    const counts = () =>
      screen.getByRole("table", {
        name: "Count of the risks by cell of the matrix, all states together",
        hidden: true,
      }).textContent;
    const { unmount } = project([]);
    const every = counts();
    unmount();
    project(["identified"]);
    expect(counts()).toBe(every);
    expect(drawn().bubbles).toHaveLength(1);
  });

  it("leaves a ratio it cannot read out of the top of the axis, which stays a number", () => {
    project([]);
    const reference = (drawn().option?.yAxis as { max: number }).max;
    project([], {
      ...MATRIX,
      points: MATRIX.points.map((point, rank) =>
        rank === 0
          ? { ...point, severity_ratio: { is_computable: true, value: "n/a", reason: null } }
          : point,
      ),
    });
    expect((drawn().option?.yAxis as { max: number }).max).toBe(reference);
  });

  /** The count the table of the counts gives at a level of probability and the first of severity. */
  function countAtLowestSeverity(probabilityLevel: number): string {
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    // Two rows of heads, then the levels of probability from the highest down to the first.
    const row = rows.at(2 + (MATRIX.probability_levels.length - probabilityLevel));
    if (row === undefined) {
      throw new Error("no such row in the table of the counts");
    }
    const [first] = within(row).getAllByRole("cell");
    return (first?.textContent ?? "").trim();
  }

  it("draws no bubble for a risk whose ratio the server could not compute, its cell still counting it", () => {
    // #1240: on a base of nought, the ratio is not computable and the risk is at the lowest level
    // of severity; the chart has no ordinate for it, and computes none.
    const noBasis = example("risk_matrix_no_basis") as RiskMatrix;
    project([], noBasis);
    const { bubbles, option, zones } = drawn();
    expect(bubbles.map((each) => each.data)).toEqual([[], [], []]);
    expect(zones?.markArea?.data).toHaveLength(16);
    // The lowest level of severity holds the risks at probabilities 0.4 and 0.3 (level 3), and 0.05 (level 1).
    expect(countAtLowestSeverity(3)).toBe("2");
    expect(countAtLowestSeverity(1)).toBe("1");
    // No ratio to lay out: the top of the axis is the one of the last level alone, a number.
    expect((option?.yAxis as { max: number }).max).toBeCloseTo(0.15);
  });

  it("says how many risks have no bubble, and why, and no more once every risk has a share", () => {
    project([], example("risk_matrix_no_basis") as RiskMatrix);
    expect(
      screen.getByText(
        "3 risks are not drawn: their severity cannot be set as a share of the budget — No reference budget.",
      ),
    ).toBeInTheDocument();
    cleanup();
    project();
    expect(screen.queryByText(/are not drawn|is not drawn/)).not.toBeInTheDocument();
  });

  it("keeps the bubble of a risk with a share beside a risk without one, which it counts apart", () => {
    const top = MATRIX.points.reduce((a, b) => (Number(ratioOf(b)) > Number(ratioOf(a)) ? b : a));
    // Before it loses its share, the risk of the highest ratio sets the top of the axis, above the
    // last level's: the fall back below is the removal's, not the matrix's.
    project([]);
    expect((drawn().option?.yAxis as { max: number }).max).toBeGreaterThan(0.15);
    cleanup();
    project([], {
      ...MATRIX,
      points: MATRIX.points.map((point) =>
        point === top
          ? {
              ...point,
              severity_ratio: {
                is_computable: false,
                value: null,
                reason: "no_reference_budget",
              },
            }
          : point,
      ),
    });
    const ids = drawn().bubbles.flatMap((each) =>
      (each.data as { id: string }[]).map(({ id }) => id),
    );
    expect(ids.sort()).toEqual(
      MATRIX.points
        .filter((point) => point !== top)
        .map((point) => point.risk_id)
        .sort(),
    );
    expect(
      screen.getByText(
        "1 risk is not drawn: its severity cannot be set as a share of the budget — No reference budget.",
      ),
    ).toBeInTheDocument();
    // The highest ratio is gone from the axis, which falls back on the last level and stays a number.
    const max = (drawn().option?.yAxis as { max: number }).max;
    expect(max).toBeCloseTo(0.15);
    // The tooltip of the risk without a bubble says nothing.
    const tooltip = drawn().option?.tooltip as { formatter: (params: unknown) => string };
    expect(tooltip.formatter({ data: { id: top.risk_id } })).toBe("");
  });

  it("says so when the filter leaves nothing to draw, and still draws the zones", () => {
    project(["identified"], {
      ...MATRIX,
      points: MATRIX.points.filter((p) => p.state !== "identified"),
    });
    expect(screen.getByText("No risk to draw for this filter.")).toBeInTheDocument();
    const { zones, bubbles } = drawn();
    expect(bubbles).toEqual([]);
    expect(zones?.markArea?.data).toHaveLength(16);
  });

  it("tells a bubble in a tooltip, its label escaped, its figures as the server gave them", () => {
    const tricky: RiskMatrix = {
      ...MATRIX,
      points: MATRIX.points.map((point, rank) =>
        rank === 0 ? { ...point, label: "Câblage <b>& co</b>" } : point,
      ),
    };
    project([], tricky);
    const { option } = drawn();
    const tooltip = option?.tooltip as { formatter: (params: unknown) => string };
    expect(tooltip.formatter({ data: { id: CABLING } })).toBe(
      [
        "<b>Câblage &lt;b&gt;&amp; co&lt;/b&gt;</b>",
        "Probability : 40%",
        "Severity : 1,250,000.00 (1.91%)",
        "Provision : 500,000.00",
        "State : Identified",
        "Zone : Watch",
      ].join("<br/>"),
    );
    // No bubble, no tooltip.
    expect(tooltip.formatter({ data: { id: "other" } })).toBe("");
  });

  it("leads a click on a bubble to the detail of its risk, from the address asked", () => {
    project();
    const { onPoint } = charts.props.at(-1) ?? {};
    act(() => {
      onPoint?.(CABLING);
    });
    expect(router.push).toHaveBeenCalledExactlyOnceWith(
      `${PATHNAME}?sort_by=provision_amount&sort_order=asc&risk=${CABLING}`,
      { scroll: false },
    );
    // A bubble filtered out cannot be clicked: no point of its own, nothing opens.
    router.push.mockClear();
    project(["occurred"]);
    act(() => {
      charts.props.at(-1)?.onPoint?.(CABLING);
    });
    expect(router.push).not.toHaveBeenCalled();
  });

  it("exports a PNG image that names the project, the revision and the date of calculation [WF-IHM-0130-A]", () => {
    project();
    expect(screen.getByRole("button", { name: "Export as PNG" })).toBeInTheDocument();
    expect(charts.props.at(-1)?.exported?.()).toEqual({
      title: "Risk matrix — Modernisation du poste de commande",
      subtitle: expect.stringMatching(/^Revision: V1 · Computed on .*2026/) as string,
      fileName: "risk-matrix-PRJ-001.png",
    });
  });

  it("starts folded, makes no instance of the chart until a command unfolds it, and folds it again (#1252)", () => {
    instances.made = 0;
    instances.disposed = 0;
    project();
    const drawing = /^Bubble chart of the risks: the probability across/;
    expect(screen.queryByRole("img", { name: drawing })).not.toBeInTheDocument();
    expect(instances.made).toBe(0);
    const unfold = screen.getByRole("button", { name: "Chart" });
    expect(unfold).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(unfold);
    expect(screen.getByRole("img", { name: drawing })).toBeInTheDocument();
    expect(instances.made).toBe(1);
    const fold = screen.getByRole("button", { name: "Chart" });
    expect(fold).toHaveAttribute("aria-expanded", "true");
    expect(fold).toHaveAttribute("aria-controls", screen.getByRole("img", { name: drawing }).id);
    fireEvent.click(fold);
    expect(screen.queryByRole("img", { name: drawing })).not.toBeInTheDocument();
    // One instance made, one released: the fold leaves none behind.
    expect(instances.made).toBe(1);
    expect(instances.disposed).toBe(1);
  });

  it("starts unfolded when the account kept it so, and folded when it kept nothing: the state read is the one drawn", () => {
    project([], MATRIX, false);
    expect(screen.getByRole("button", { name: "Chart" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("img", { name: /^Bubble chart of the risks/ })).toBeInTheDocument();
    cleanup();
    project();
    expect(screen.getByRole("button", { name: "Chart" })).toHaveAttribute("aria-expanded", "false");
  });

  it("keeps the state under « risk_matrix » at each click, without waiting for the answer, the focus staying on the command", () => {
    // An answer that never comes: the chart changes at once, and the command stays usable.
    vi.mocked(updateChartPreferences).mockReturnValue(new Promise<Settled>(() => undefined));
    project();
    const command = screen.getByRole("button", { name: "Chart" });
    command.focus();
    fireEvent.click(command);
    expect(updateChartPreferences).toHaveBeenLastCalledWith("risk_matrix", { folded: false });
    expect(command).toHaveAttribute("aria-expanded", "true");
    expect(command).toHaveFocus();
    fireEvent.click(command);
    expect(updateChartPreferences).toHaveBeenLastCalledWith("risk_matrix", { folded: true });
    expect(command).toHaveAttribute("aria-expanded", "false");
    expect(updateChartPreferences).toHaveBeenCalledTimes(2);
    expect(command).toHaveFocus();
  });

  it("tells a refusal of the service, which can be dismissed, the chart staying as the user left it", async () => {
    vi.mocked(updateChartPreferences).mockResolvedValue({ kind: "unreachable" });
    project();
    fireEvent.click(screen.getByRole("button", { name: "Chart" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Chart" })).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(screen.getByRole("button", { name: /dismiss|close/i }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("folds into another node than the one ECharts styled, which keeps neither its role nor its styles (#1252)", () => {
    project();
    fireEvent.click(screen.getByRole("button", { name: "Chart" }));
    const drawing = screen.getByRole("img", { name: /^Bubble chart of the risks/ });
    expect(drawing.getAttribute("style")).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Chart" }));
    const folded = document.getElementById(drawing.id);
    expect(folded).not.toBeNull();
    expect(folded).not.toBe(drawing);
    expect(folded?.getAttribute("role")).toBeNull();
    expect(folded?.getAttribute("style")).toBeNull();
    expect(folded?.className).toBe("");
  });

  it("exports a PNG image while the matrix is unfolded, the instance of the screen kept (#1252, WF-IHM-0130-A)", () => {
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    project();
    fireEvent.click(screen.getByRole("button", { name: "Chart" }));
    instances.images = [];
    fireEvent.click(screen.getByRole("button", { name: "Export as PNG" }));
    expect(instances.images).toHaveLength(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("img", { name: /^Bubble chart of the risks/ })).toBeInTheDocument();
  });

  it("describes its drawing in a sentence and breaks no rule of accessibility [WF-IHM-0100-A]", async () => {
    const { container } = project();
    fireEvent.click(screen.getByRole("button", { name: "Chart" }));
    expect(
      screen.getByRole("img", { name: /^Bubble chart of the risks: the probability across/ }),
    ).toBeInTheDocument();
    await expectAccessible(container);
  });
});

describe("the risk matrix of the portfolio", () => {
  /** The matrix of the portfolio, in English. */
  function portfolio() {
    charts.props = [];
    return render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
        <PortfolioRiskMatrix matrix={RISKS.matrix} scope={RISKS.scope} />
      </NextIntlClientProvider>,
    );
  }

  it("draws every risk of the points the server rendered, and counts the cells as it gave them", () => {
    portfolio();
    const { bubbles } = drawn();
    expect(bubbles.map((each) => each.name)).toEqual(["Identified"]);
    expect(bubbles[0]?.data).toHaveLength(RISKS.matrix.points.length);
    expect(screen.getByRole("figure", { name: "Risk matrix" })).toBeInTheDocument();
  });

  it("tells the project of a bubble in its tooltip", () => {
    portfolio();
    const tooltip = drawn().option?.tooltip as { formatter: (params: unknown) => string };
    expect(tooltip.formatter({ data: { id: CABLING } })).toContain(
      "Project : Modernisation du poste de commande",
    );
  });

  it("opens the project of a bubble the caller can open, and only that one [WF-PTF-0030-A]", () => {
    portfolio();
    const open = RISKS.matrix.points.find((point) => point.can_open === true);
    const closed = RISKS.matrix.points.find((point) => point.can_open === false);
    const onPoint = charts.props.at(-1)?.onPoint;
    act(() => {
      onPoint?.(closed?.risk_id ?? "");
    });
    expect(router.push).not.toHaveBeenCalled();
    act(() => {
      onPoint?.(open?.risk_id ?? "");
    });
    expect(router.push).toHaveBeenCalledExactlyOnceWith(`/projects/${open?.project_id ?? ""}`);
  });

  it("tells in its tooltip a project that cannot be opened, and only that one", () => {
    portfolio();
    const tooltip = drawn().option?.tooltip as { formatter: (params: unknown) => string };
    const closed = RISKS.matrix.points.find((point) => point.can_open === false);
    const open = RISKS.matrix.points.find((point) => point.can_open === true);
    expect(tooltip.formatter({ data: { id: closed?.risk_id } })).toContain(
      "Project cannot be opened",
    );
    expect(tooltip.formatter({ data: { id: open?.risk_id } })).not.toContain("cannot be opened");
  });

  it("makes one instance of the chart, a render with the same props making no other", () => {
    instances.made = 0;
    const view = () => (
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
        <PortfolioRiskMatrix matrix={RISKS.matrix} scope={RISKS.scope} />
      </NextIntlClientProvider>
    );
    const { rerender } = render(view());
    expect(instances.made).toBe(1);
    const renders = charts.props.length;
    // A new element, so that React renders the chart again: the states handed down are the same
    // array, the option is the same function, and no other instance is made.
    rerender(view());
    expect(charts.props.length).toBeGreaterThan(renders);
    expect(instances.made).toBe(1);
  });

  it("exports a PNG image that names the perimeter the server retained and its date of calculation [WF-IHM-0130-A]", () => {
    portfolio();
    expect(charts.props.at(-1)?.exported?.()).toEqual({
      title: "Risk matrix",
      subtitle: expect.stringContaining("calculated on 3 Jun 2026") as string,
      fileName: "risk-matrix-portfolio-2026-06-03.png",
    });
  });
});
