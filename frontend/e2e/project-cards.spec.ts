// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of a project in cards (EP-25, US-2130/L4), measured rather than compared to an
 * image: at 1366 points and at 1280, the threshold of the one line, at 1100 and 1024 — where the
 * commands of the work breakdown, which went out of their card on one line below 1280 points, wrap
 * (#3418) —, then at 911, what a zoom of 150 % leaves of it, the grid of each list is as wide as
 * the body of its card, its bar holds its commands on one line from 1280 points, and none goes out
 * of its card at any of them (WF-IHM-0100). That
 * the screens are walked entirely by the keyboard, their contrast measured in both modes and
 * nothing lost at 911 points is proven by `accessibility.spec.ts`.
 */
import { expect, type Page, test } from "@playwright/test";

import { WORKING } from "./bounds";
import { compile } from "./compile";
import { untilHydrated } from "./hydration";
import { path } from "./routes";

test.describe.configure({ mode: "parallel" });
test.slow();

const WINDOWS = [
  { width: 1366, height: 900 },
  { width: 1280, height: 900 },
  { width: 1100, height: 900 },
  { width: 1024, height: 900 },
  { width: 911, height: 900 },
] as const;

const SETTINGS = path("/projects/[projectId]/settings");

/** The width from which the bar of a grid holds its commands on one line (`xl:`), in points. */
const ONE_LINE_FROM = 1280;

/** The height of a bar on one line, in pixels, at most: the buttons are 28 or 32 high. */
const ONE_LINE = 34;

/** The widths a card gives a grid: the room of its body, the frame of the grid, its table. */
interface Fit {
  readonly card: string;
  readonly body: number;
  readonly frame: number;
  readonly table: number;
  /** The tops of the buttons of the bar of the grid, and the height of the bar. */
  readonly buttons: readonly number[];
  readonly bar: number;
  /** The right edge of the last button of the bar, and that of the card that holds it. */
  readonly reach: number;
  readonly edge: number;
}

/** Measure each grid of the screen against the body of the card that holds it. */
function measure(page: Page): Promise<Fit[]> {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll("main [data-slot='section-card']")).flatMap((card) => {
      const grid = card.querySelector("[role='grid'], [role='treegrid']");
      const body = card.querySelector("[data-slot='card-content']");
      const frame = grid?.parentElement;
      const bar = frame?.parentElement?.firstElementChild;
      if (
        grid === null ||
        !(body instanceof HTMLElement) ||
        !(frame instanceof HTMLElement) ||
        !(bar instanceof HTMLElement)
      ) {
        return [];
      }
      const style = getComputedStyle(body);
      return [
        {
          card: card.getAttribute("aria-label") ?? "",
          body: body.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight),
          frame: frame.getBoundingClientRect().width,
          table: grid.getBoundingClientRect().width,
          buttons: Array.from(bar.querySelectorAll("button"))
            .map((button) => button.getBoundingClientRect())
            .filter((rect) => rect.width > 0 && rect.height > 0)
            .map((rect) => rect.top),
          bar: bar.getBoundingClientRect().height,
          reach: Math.max(
            0,
            ...Array.from(bar.querySelectorAll("button")).map(
              (button) => button.getBoundingClientRect().right,
            ),
          ),
          edge: card.getBoundingClientRect().right,
        },
      ];
    }),
  );
}

for (const size of WINDOWS) {
  test(`the grids of the settings of a project are as wide as the body of their card, their bar on one line from 1280 points and no command out of its card, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await compile(page.request, SETTINGS);
    await page.setViewportSize(size);
    await page.goto(SETTINGS);
    await expect(page.locator("main [role='grid'], main [role='treegrid']").first()).toBeVisible({
      timeout: WORKING,
    });
    await untilHydrated(page);
    const fits = await measure(page);
    expect(
      fits.map(({ card }) => card),
      "the cards that hold a grid",
    ).toEqual(["Lotissement", "Sous-projets", "Contributeurs"]);
    for (const fit of fits) {
      expect(Math.abs(fit.frame - fit.body), `the frame of ${fit.card}`).toBeLessThanOrEqual(1);
      expect(fit.table, `the table of ${fit.card} fills its frame`).toBeGreaterThanOrEqual(
        fit.frame - 2,
      );
      // At 911 points the bar has not the room for its commands, its search and its filters on one
      // line: its commands wrap rather than widen the page (the walk by Tab of
      // `accessibility.spec.ts` would find a field under the sidebar).
      if (size.width >= ONE_LINE_FROM) {
        expect(fit.bar, `the bar of ${fit.card} on one line`).toBeLessThanOrEqual(ONE_LINE);
        expect(
          Math.max(...fit.buttons) - Math.min(...fit.buttons),
          `the commands of ${fit.card} on one line`,
        ).toBeLessThanOrEqual(2);
      }
      // Wrapped or on one line, no command goes out of its card (#3418).
      expect(fit.reach, `the commands of ${fit.card} stay in their card`).toBeLessThanOrEqual(
        fit.edge,
      );
    }
  });
}
