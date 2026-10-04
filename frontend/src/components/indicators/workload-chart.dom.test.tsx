// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import type { BarSeriesOption, LineSeriesOption } from "echarts/charts";
import { getInstanceByDom } from "echarts/core";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ChartOption } from "@/components/chart/chart";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { WorkloadChart, type WorkloadPlan } from "./workload-chart";

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

const WORKLOAD = example("workload") as WorkloadPlan;
const PROJECT = "Modernisation du poste de commande";

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
  return english(
    <WorkloadChart
      workload={WORKLOAD}
      project={PROJECT}
      revision="Current revision"
      fileName="workload-PRJ-001.png"
    />,
  );
}

/** The links the export clicked: the file the browser is asked to save. */
let saved: { href: string; download: string }[] = [];

beforeEach(() => {
  canvas.hosts = [];
  canvas.options = [];
  canvas.images = [];
  canvas.disposed = 0;
  saved = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    saved.push({ href: this.href, download: this.download });
  });
});

afterEach(() => {
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
    expect(series[0]?.data).toEqual([
      ["2026-05-01T00:00:00Z", "5.95"],
      ["2026-06-01T00:00:00Z", "6.55"],
    ]);
    // The capacity of each role over the months of its load, a role without load left to the
    // table.
    const capacities = series.slice(2);
    expect(capacities.map((each) => [each.type, each.name, each.data])).toEqual([
      [
        "line",
        "Capacity — Ingénieur électricien",
        [
          ["2026-05-01T00:00:00Z", "910.02"],
          ["2026-06-01T00:00:00Z", "910.02"],
        ],
      ],
    ]);
  });

  it("lists each month of each role, its capacity, its ratio and its zone by the one signal, a role without load said so [WF-IHM-0070-A]", async () => {
    const { container } = workload();
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      "Ingénieur électricienMay 20265.95910.020.65%Nominal",
      "Ingénieur électricienJune 20266.55910.020.72%Nominal",
      "Technicien de mise en serviceNo load606.68",
    ]);
    expect(within(container).getByText(/^Computed on/)).toBeInTheDocument();
    await expectAccessible(container);
  });

  it("exports at the keyboard a PNG image that bears the name of the project, the revision and the date of calculation [WF-IHM-0130-A]", async () => {
    const user = userEvent.setup();
    workload();
    const command = screen.getByRole("button", { name: "Export as PNG" });
    await user.tab();
    expect(command).toHaveFocus();
    await user.keyboard("{Enter}");

    expect(canvas.options).toHaveLength(1);
    const option = canvas.options[0] as ChartOption;
    expect(option.title).toMatchObject({
      text: `Workload — ${PROJECT}`,
      subtext: `Revision: Current revision · Remaining of the current revision · Computed on ${formatTimestamp(WORKLOAD.context.computed_at, "en")}`,
    });
    // Its legend and its bars as on the screen, below the title, drawn at once.
    expect(option.legend).toMatchObject({ top: 64, selectedMode: false });
    expect(option.grid).toMatchObject({ top: 48 + 64 });
    expect((option.series as BarSeriesOption[]).map((each) => each.name)).toEqual([
      "Ingénieur électricien",
      "Technicien de mise en service",
      "Capacity — Ingénieur électricien",
    ]);
    expect(option.animation).toBe(false);
    expect(canvas.images).toEqual([
      { type: "png", pixelRatio: 2, backgroundColor: option.backgroundColor },
    ]);
    expect(saved).toEqual([
      { href: "data:image/png;base64,iVBORw0KGgo=", download: "workload-PRJ-001.png" },
    ]);
    // The instance out of the screen is released, and its host gone.
    expect(canvas.disposed).toBe(1);
    expect(canvas.hosts[0]?.isConnected).toBe(false);
  });
});
