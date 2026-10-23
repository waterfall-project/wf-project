// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The frame of a dense grid in the window, measured (US-0560, #1033, #1041, #1042): on each of the
 * nine screens that fill the window, in a window too low for the grid at its floor, at the two
 * widths of the harness — 1366 points, then 911, what a zoom of 150 % leaves of it —, the frame
 * covers nothing that follows it; the bar above it is as wide as the frame, scroll bars included,
 * and holds on one line; and a grid of a few rows is no taller than its content. No requirement
 * carries this: it is the layout the guide, « Les grilles », states.
 */
import { expect, type Page, test } from "@playwright/test";

import { compile } from "./compile";
import { untilHydrated, WORKING } from "./hydration";
import { path } from "./routes";

test.describe.configure({ mode: "parallel" });
test.slow();

/** The window of the harness and the same window at a zoom of 150 %, both lower than any floor. */
const WINDOWS = [
  { width: 1366, height: 300 },
  { width: 911, height: 300 },
] as const;

const REVISION = "/projects/[projectId]/revisions/[revisionId]";

/** The nine screens that fill the window (`Screen`, `fill` or `fillWide`). */
const SCREENS = [
  "/",
  "/portfolio/projects",
  "/admin/users",
  "/admin/audit-log",
  path(`${REVISION}/estimate`),
  path(`${REVISION}/planning`),
  path(`${REVISION}/remaining`),
  path(`${REVISION}/actual-costs`),
  path(`${REVISION}/risks`),
] as const;

/** The height of a bar on one line, in pixels, at most: the buttons are 28 or 32 high. */
const ONE_LINE = 34;

/** Open a screen in a window, until its first grid shows and the page is hydrated. */
async function open(page: Page, address: string, size: { width: number; height: number }) {
  await page.setViewportSize(size);
  await page.goto(address);
  await expect(page.locator("main [role='grid'], main [role='treegrid']").first()).toBeVisible({
    timeout: WORKING,
  });
  await untilHydrated(page);
}

/** What the layout says of each grid of the screen: its frame, its bar, and what follows them. */
interface Measure {
  readonly name: string;
  /** The elements after the frame, at each level up to the page, that its box covers. */
  readonly covered: readonly string[];
  readonly frame: number;
  readonly bar: number;
  readonly barHeight: number;
  readonly narrowBar: { readonly width: number; readonly height: number };
}

/** Measure every grid of the screen, in the page. */
function measureGrids(page: Page): Promise<Measure[]> {
  return page.evaluate(() => {
    const main = document.querySelector("main");
    if (main === null) {
      throw new Error("the screen has no main");
    }
    const grids = Array.from(main.querySelectorAll("[role='grid'], [role='treegrid']"));
    return grids.map((grid) => {
      const frame = grid.parentElement;
      const holder = frame?.parentElement;
      const bar = holder?.firstElementChild;
      if (!(frame instanceof HTMLElement) || !(bar instanceof HTMLElement)) {
        throw new Error("the grid has no frame or no bar");
      }
      const box = frame.getBoundingClientRect();
      const covered: string[] = [];
      for (let level: Element | null = frame; level !== null && level !== main;) {
        for (let next = level.nextElementSibling; next !== null; next = next.nextElementSibling) {
          const rect = next.getBoundingClientRect();
          const across = Math.min(rect.right, box.right) - Math.max(rect.left, box.left);
          const down = Math.min(rect.bottom, box.bottom) - Math.max(rect.top, box.top);
          if (rect.height > 0 && across > 1 && down > 1) {
            covered.push(`${next.tagName} ${next.className}`.slice(0, 80));
          }
        }
        level = level.parentElement;
      }
      const measure = {
        name: grid.getAttribute("aria-label") ?? "",
        covered,
        frame: frame.offsetWidth,
        bar: bar.offsetWidth,
        barHeight: bar.offsetHeight,
      };
      // A table narrower than the bar: the bar keeps what it needs for one line.
      bar.style.width = "100px";
      const narrowBar = { width: bar.offsetWidth, height: bar.offsetHeight };
      bar.style.width = "";
      return { ...measure, narrowBar };
    });
  });
}

for (const address of SCREENS) {
  test(`${address}: the frame of each grid covers nothing in a low window, and its bar is as wide as the frame, on one line`, async ({
    page,
  }) => {
    await compile(page.request, address);
    for (const size of WINDOWS) {
      await open(page, address, size);
      const grids = await measureGrids(page);
      expect(grids.length, `${address} has a grid`).toBeGreaterThan(0);
      for (const grid of grids) {
        const where = `${grid.name} at ${String(size.width)}`;
        expect(grid.covered, `what the frame of ${where} covers`).toEqual([]);
        // The scroll bars the system draws beside the rows are in the width of the frame.
        expect(Math.abs(grid.bar - grid.frame), `the bar of ${where}`).toBeLessThanOrEqual(1);
        expect(grid.barHeight, `the bar of ${where} on one line`).toBeLessThanOrEqual(ONE_LINE);
        expect(
          grid.narrowBar.height,
          `the narrowed bar of ${where} on one line`,
        ).toBeLessThanOrEqual(ONE_LINE);
        expect(
          grid.narrowBar.width,
          `the narrowed bar of ${where} keeps its search`,
        ).toBeGreaterThan(100);
      }
    }
  });
}

test("a grid of a few rows is no taller than its content, in a window that would hold more", async ({
  page,
}) => {
  await compile(page.request, "/admin/users");
  await open(page, "/admin/users", { width: 1366, height: 1400 });
  const heights = await page.evaluate(() => {
    const grid = document.querySelector("main [role='grid']");
    const frame = grid?.parentElement;
    if (!(grid instanceof HTMLElement) || !(frame instanceof HTMLElement)) {
      throw new Error("the screen has no grid");
    }
    return { frame: frame.offsetHeight, table: grid.offsetHeight };
  });
  // The table and the two borders of the frame: no band under the totals (#1041).
  expect(heights.frame).toBeLessThanOrEqual(heights.table + 2);
});

/**
 * The screens whose key figures lie in cards above their grid (US-0550), with the widths at which
 * the totals of the grid stay in a window 768 high, measured — the cards take, at 1366 then at 911:
 * estimate 170 and 305 points, remaining to commit 189 and 476, actual costs 53 and 99, risks 103
 * and 145. At 911 the remaining to commit is left out: its four blocks need two rows of cards, 476
 * points, and the header and the bar of the screen leave 519 under them for the cards, the filter,
 * the bar of the grid and the 160 of its floor. So is the actual costs, whose cards are no cause:
 * below 1024 its grid and the journal of imports lie one under the other, and the grid takes the
 * height of the window (`max-h-svh`) from where it starts. The risks hold at both widths, their
 * cards 103 and 145 points high, with the chart of their matrix folded between the cards and the
 * grid (US-0550/L4b, #1252): unfolded, it takes its 288 points and the page scrolls.
 */
const CARD_SCREENS = [
  { address: path(`${REVISION}/estimate`), widths: [1366, 911], height: 768 },
  { address: path(`${REVISION}/remaining`), widths: [1366], height: 768 },
  { address: path(`${REVISION}/actual-costs`), widths: [1366], height: 768 },
  { address: path(`${REVISION}/risks`), widths: [1366, 911], height: 768 },
] as const;

for (const { address, widths, height } of CARD_SCREENS) {
  test(`${address}: the cards of figures leave the totals of the grid in the window`, async ({
    page,
  }) => {
    await compile(page.request, address);
    for (const width of widths) {
      await open(page, address, { width, height });
      const cards = await page.locator("main [data-slot='card'][role='region']").count();
      expect(cards, `the cards of ${address}`).toBeGreaterThan(0);
      const grid = page.locator("main [role='grid'], main [role='treegrid']").first();
      // The totals stick to the foot of the grid: the cell that holds them tells where they are.
      await expect(
        grid.getByRole("row").last().locator("td, th").first(),
        `the totals of ${address} at ${String(width)}`,
      ).toBeInViewport({ ratio: 1 });
    }
  });
}
