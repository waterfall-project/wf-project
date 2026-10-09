// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import type { LineSeriesOption } from "echarts/charts";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ChartOption } from "@/components/chart/chart";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import { roomForCharts } from "@/test/chart-room";
import { example } from "@/test/fixtures";

import { MilestoneChart, type MilestoneTracking } from "./milestone-chart";

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

/** The background of the charter in the light mode, as `globals.css` declares its token. */
const BACKGROUND = (() => {
  const css = readFileSync(join(import.meta.dirname, "../../theme/globals.css"), "utf-8");
  const light = /--background:\s*light-dark\((#[0-9a-f]{6}),/i.exec(css)?.[1];
  if (light === undefined) {
    throw new Error("globals.css declares no background token");
  }
  return light;
})();

const TRACKING = example("milestone_tracking") as MilestoneTracking;
const PROJECT = "Modernisation du poste de commande";

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

// Each drawing has the room a page gives it: ECharts measures it as it draws.
roomForCharts();

describe("the export of a chart", () => {
  it("draws at the keyboard a PNG image that bears its title, the name of the project, the revision and the date of calculation, on the background of the charter", async () => {
    const user = userEvent.setup();
    render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
        <MilestoneChart
          tracking={TRACKING}
          provenance={{ project: PROJECT, code: "PRJ-001", revision: "Current revision" }}
        />
      </NextIntlClientProvider>,
    );
    const command = screen.getByRole("button", { name: "Export as PNG" });
    await user.tab();
    expect(command).toHaveFocus();
    await user.keyboard("{Enter}");

    expect(canvas.options).toHaveLength(1);
    const option = canvas.options[0] as ChartOption;
    expect(option.title).toMatchObject({
      text: `Time/time diagram — ${PROJECT}`,
      subtext: `Revision: Current revision · Computed on ${formatTimestamp(TRACKING.context.computed_at, "en")}`,
    });
    // The colour the probe of the token resolves to, as the simulated document writes it back.
    expect(option.backgroundColor).toBe(BACKGROUND);
    // Its curves as on the screen, below the title, drawn at once.
    // The head: a line of title, a line of provenance, and their margins (12 + 24 + 6 + 16 + 14).
    expect(option.grid).toMatchObject({ top: 24 + 72 });
    expect((option.series as LineSeriesOption[]).map((each) => each.name)).toEqual([
      "Réception des études",
      "Réception usine",
      "Equal dates",
    ]);
    expect(option.animation).toBe(false);
    expect(canvas.images).toEqual([{ type: "png", pixelRatio: 2, backgroundColor: BACKGROUND }]);
    expect(saved).toEqual([
      { href: "data:image/png;base64,iVBORw0KGgo=", download: "milestone-tracking-PRJ-001.png" },
    ]);
    // The instance out of the screen is released, and its host gone.
    expect(canvas.disposed).toBe(1);
    expect(canvas.hosts[0]?.isConnected).toBe(false);
  });

  it("folds a long title within the width of the image, the chart moved down by its lines, the provenance whole", async () => {
    const user = userEvent.setup();
    // The longest name of a project the contract admits: three hundred characters.
    const project = Array.from({ length: 30 }, () => "Ouvrage 12")
      .join(" ")
      .slice(0, 300);
    render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
        <MilestoneChart
          tracking={TRACKING}
          provenance={{ project, code: "PRJ-001", revision: "Current revision" }}
        />
      </NextIntlClientProvider>,
    );
    await user.click(screen.getByRole("button", { name: "Export as PNG" }));
    const option = canvas.options[0] as ChartOption;
    const title = option.title as { text: string; subtext: string };
    const lines = title.text.split("\n");
    expect(lines.length).toBeGreaterThan(1);
    expect(lines.join(" ")).toBe(`Time/time diagram — ${project}`);
    // Each line within the width of the image less its margins (1280 - 32), at the size of the
    // title, as the simulated document estimates it without a canvas: 0.6 of 18 pixels a letter.
    for (const line of lines) {
      expect(line.length * 18 * 0.6).toBeLessThanOrEqual(1280 - 32);
    }
    expect(title.subtext).toBe(
      `Revision: Current revision · Computed on ${formatTimestamp(TRACKING.context.computed_at, "en")}`,
    );
    expect(option.grid).toMatchObject({ top: 24 + 12 + lines.length * 24 + 6 + 16 + 14 });
  });
});
