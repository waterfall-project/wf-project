// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import type { BarSeriesOption, LineSeriesOption } from "echarts/charts";
import { getInstanceByDom } from "echarts/core";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { ChartOption } from "@/components/chart/chart";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { WorkloadChart, type WorkloadPlan } from "./workload-chart";
import { WorkloadSection } from "./workload-section";

/** What the instance out of the screen was handed, and what became of it. */
const canvas = vi.hoisted(() => ({
  hosts: [] as HTMLElement[],
  options: [] as unknown[],
  images: [] as unknown[],
  disposed: 0,
}));

// The screen draws in SVG, as it does; the image is drawn on a canvas, which the simulated
// document does not paint: an instance in its place records what it is asked to draw.
vi.mock("echarts/core", async (actual) => {
  const echarts = await actual<typeof import("echarts/core")>();
  return {
    ...echarts,
    init: (...args: Parameters<typeof echarts.init>) => {
      const [host, , options] = args;
      if (options?.renderer !== "canvas") {
        return echarts.init(...args);
      }
      if (host instanceof HTMLElement) {
        canvas.hosts.push(host);
      }
      return {
        setOption: (option: unknown) => canvas.options.push(option),
        getDataURL: (image: unknown) => {
          canvas.images.push(image);
          return "data:image/png;base64,iVBORw0KGgo=";
        },
        dispose: () => {
          canvas.disposed += 1;
        },
      };
    },
  };
});

type Revision = components["schemas"]["Revision"];
type OrgNode = components["schemas"]["OrgNode"];

/** The background of the charter in the light mode, as `globals.css` declares its token. */
const BACKGROUND = (() => {
  const css = readFileSync(join(import.meta.dirname, "../../theme/globals.css"), "utf-8");
  const light = /--background:\s*light-dark\((#[0-9a-f]{6}),/i.exec(css)?.[1];
  if (light === undefined) {
    throw new Error("globals.css declares no background token");
  }
  return light;
})();

const WORKLOAD = example("workload") as WorkloadPlan;
const PROJECT = "Modernisation du poste de commande";

/** Where the workload of the witness project comes from, as its screen names it. */
const PROVENANCE = {
  project: PROJECT,
  code: "PRJ-001",
  revision: "Current revision",
  detail:
    "Basis: Remaining of the current revision · Organisation node and its descendants: Bureau d’études électricité",
};

/** Render the workload in English, as the screen hands it over. */
function english(node: ReactNode) {
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {node}
    </NextIntlClientProvider>,
  );
}

/** The workload of the witness project, on the revision under way. */
function workload() {
  return english(<WorkloadChart workload={WORKLOAD} provenance={PROVENANCE} />);
}

/** The links the export clicked: the file the browser is asked to save. */
let saved: { href: string; download: string }[] = [];

beforeEach(() => {
  canvas.hosts = [];
  canvas.options = [];
  canvas.images = [];
  canvas.disposed = 0;
  saved = [];
  // The token of the background, as the charter paints it in the light mode: the simulated
  // document loads no style sheet of the application.
  const style = document.createElement("style");
  style.textContent = `.text-background { color: ${BACKGROUND}; }`;
  document.head.append(style);
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    saved.push({ href: this.href, download: this.download });
  });
});

afterEach(() => {
  document.head.querySelectorAll("style").forEach((style) => {
    style.remove();
  });
  vi.restoreAllMocks();
});

describe("the workload of a project", () => {
  it("draws the load of each role by month in bars, its capacity across, as the API gave them [WF-DEV-0070-A]", async () => {
    workload();
    const image = screen.getByRole("img", { name: /^Bars of the load of each resource role/ });
    await waitFor(() => {
      expect(getInstanceByDom(image)).toBeDefined();
    });
    const option = getInstanceByDom(image)?.getOption() as ChartOption;
    const series = option.series as (BarSeriesOption | LineSeriesOption)[];
    expect(series.slice(0, 2).map((each) => [each.type, each.name])).toEqual([
      ["bar", "Ingénieur électricien"],
      ["bar", "Technicien de mise en service"],
    ]);
    // Each role told apart without its colour too: the pattern of the symbol of its rank.
    expect(
      series.slice(0, 2).map((each) => (each as BarSeriesOption).itemStyle?.decal),
    ).toMatchObject([{ symbol: "circle" }, { symbol: "triangle" }]);
    // What is left of the connection of the terminal blocks, in June after the calculation,
    // then the wiring on site.
    expect(series[0]?.data?.slice(0, 2)).toEqual([
      ["2026-06-01T00:00:00Z", "12.5"],
      ["2026-07-01T00:00:00Z", "22.44"],
    ]);
    // The capacity of each role over the months of its load, a role without load left to the
    // table.
    expect(series.slice(0, 3).map((each) => each.type)).toEqual(["bar", "bar", "bar"]);
    const capacities = series.slice(3);
    expect(
      capacities.map((each) => [each.type, each.name, (each.data as unknown[]).at(0)]),
    ).toEqual([
      ["line", "Capacity — Ingénieur électricien", ["2026-06-01T00:00:00Z", "658654"]],
      ["line", "Capacity — Technicien de mise en service", ["2026-07-01T00:00:00Z", "485324"]],
    ]);
    // Its months on an axis in UTC, a tick on the first of each, June 2026 to February 2027.
    expect(option.useUTC).toBe(true);
    // The instance gives back each of its components as a list.
    const [xAxis] = option.xAxis as { axisLabel: { customValues: number[] } }[];
    const ticks = xAxis?.axisLabel.customValues.map((tick) => new Date(tick).toISOString());
    expect([ticks?.at(0), ticks?.at(-1), ticks?.length]).toEqual([
      "2026-06-01T00:00:00.000Z",
      "2027-02-01T00:00:00.000Z",
      9,
    ]);
  });

  it("lists each month of each role, its capacity, its ratio and its zone by the one signal, a role without load said so [WF-IHM-0070-A]", async () => {
    const { container } = workload();
    const rows = screen.getAllByRole("row").slice(1);
    const listed = rows.map((row) => row.textContent);
    expect(listed.slice(0, 2)).toEqual([
      // The capacity of a role is that of the installation, at the scale of the portfolio: the
      // load of one project is a share of it too small to be written to the hundredth.
      "Ingénieur électricienJune 202612.5658,6540%Nominal",
      "Ingénieur électricienJuly 202622.44658,6540%Nominal",
    ]);
    // The commissioning on site in December, the one month whose ratio is written: the format of
    // a ratio of the portfolio's scale kept in proof.
    expect(listed).toContain("Technicien de mise en serviceDecember 202676.55485,3240.02%Nominal");
    expect(listed.slice(-2)).toEqual([
      "Technicien de mise en serviceJanuary 20278485,3240%Nominal",
      "Monteur câbleurNo load216,662.5",
    ]);
    expect(listed).toHaveLength(7 + 7 + 1);
    expect(within(container).getByText(/^Computed on/)).toBeInTheDocument();
    await expectAccessible(container);
  });

  it("exports at the keyboard a PNG image that bears the name of the project, the revision and the date of calculation, the basis and the node filtered, on the background of the charter [WF-IHM-0130-A]", async () => {
    const user = userEvent.setup();
    workload();
    const command = screen.getByRole("button", { name: "Export as PNG" });
    await user.tab();
    expect(command).toHaveFocus();
    await user.keyboard("{Enter}");

    expect(canvas.options).toHaveLength(1);
    const option = canvas.options[0] as ChartOption;
    expect(option.title).toMatchObject({
      text: `Project workload — ${PROJECT}`,
      subtext: `Revision: Current revision · Basis: Remaining of the current revision · Organisation node and its descendants: Bureau d’études électricité · Computed on ${formatTimestamp(WORKLOAD.context.computed_at, "en")}`,
    });
    // The colour the probe of the token resolves to, as the simulated document writes it back.
    expect(option.backgroundColor).toBe(BACKGROUND);
    // Its legend and its bars as on the screen, below the head — a line of title, a line of
    // provenance, and their margins (12 + 24 + 6 + 16 + 14) —, drawn at once.
    expect(option.legend).toMatchObject({ top: 72, selectedMode: false });
    expect(option.grid).toMatchObject({ top: 48 + 72 });
    expect((option.series as BarSeriesOption[]).map((each) => each.name)).toEqual([
      "Ingénieur électricien",
      "Technicien de mise en service",
      "Monteur câbleur",
      "Capacity — Ingénieur électricien",
      "Capacity — Technicien de mise en service",
    ]);
    expect(option.animation).toBe(false);
    expect(canvas.images).toEqual([{ type: "png", pixelRatio: 2, backgroundColor: BACKGROUND }]);
    expect(saved).toEqual([
      { href: "data:image/png;base64,iVBORw0KGgo=", download: "workload-PRJ-001.png" },
    ]);
    // The instance out of the screen is released, and its host gone.
    expect(canvas.disposed).toBe(1);
    expect(canvas.hosts[0]?.isConnected).toBe(false);
  });
});

describe("the export of the workload from its section", () => {
  it("names in its image the basis the API read and the label of the node the address filters, as the section composes them [WF-IHM-0130-A]", async () => {
    const user = userEvent.setup();
    const marked = example("workload_marked_remaining") as WorkloadPlan;
    english(
      <WorkloadSection
        workload={{ kind: "read", data: marked }}
        asked={{
          basis: "marked_remaining",
          revision: undefined,
          orgNode: "01926f3a-7c00-7000-8000-000000000471",
        }}
        bases={["reference_budget", "marked_remaining", "current_remaining"]}
        marked={(example("revisions_marked") as { items: Revision[] }).items}
        orgNodes={example("org_nodes") as OrgNode[]}
        address={{ pathname: "/workload", parameters: [] }}
        project={{ label: PROJECT, code: "PRJ-001" }}
        shown={undefined}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Export as PNG" }));
    const option = canvas.options[0] as ChartOption;
    expect(option.title).toMatchObject({
      text: `Project workload — ${PROJECT}`,
      subtext: `Revision: Référence · Basis: Remaining of a marked revision · Organisation node and its descendants: Bureau d'études électricité · Computed on ${formatTimestamp(marked.context.computed_at, "en")}`,
    });
    expect(saved).toEqual([
      { href: "data:image/png;base64,iVBORw0KGgo=", download: "workload-PRJ-001.png" },
    ]);
  });
});
