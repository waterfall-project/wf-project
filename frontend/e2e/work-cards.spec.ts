// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grids of work of a revision in cards (EP-25, US-2140/L1), measured rather than compared to an
 * image: the planning, the estimate, the remaining to commit and the task tree stay tight — their
 * card is as wide as the window leaves it, in no centred column —, the card fills the window, the
 * grid is as wide as the body of its card, the height of its rows is the one it had (`ROW`), and the
 * planning start date lies in the card, not under the title (WF-IHM-0100-A). That the screens are
 * walked entirely by the keyboard, their contrast measured in both modes and nothing lost at 911
 * points — a zoom of 150 % — is proven by `accessibility.spec.ts`, which draws them from the table
 * of the functions.
 */
import { expect, type Page, test } from "@playwright/test";

import { compile } from "./compile";
import { untilHydrated, WORKING } from "./hydration";
import { path } from "./routes";

test.describe.configure({ mode: "parallel" });
test.slow();

const WINDOWS = [
  { width: 1366, height: 900 },
  { width: 911, height: 900 },
] as const;

const REVISION = "/projects/[projectId]/revisions/[revisionId]";

/** The height of a row of a dense grid, in pixels (`h-7`): it does not change with the card. */
const ROW = 28;

/** The margin of a screen of work, in pixels: `px-5` on each side. */
const MARGIN = 20;

const GRIDS = [`${REVISION}/planning`, `${REVISION}/estimate`, `${REVISION}/remaining`] as const;

interface Fit {
  readonly main: { readonly left: number; readonly right: number; readonly width: number };
  readonly card: { readonly left: number; readonly right: number; readonly bottom: number };
  readonly body: number;
  readonly frame: number;
  readonly table: number;
  readonly row: number;
  /** Whether the date of the planning start is in the card, and the heading of the screen is not. */
  readonly start: boolean | undefined;
}

/** Measure the card of the grid against its screen and its window. */
function measure(page: Page): Promise<Fit> {
  return page.evaluate(() => {
    const main = document.querySelector("main");
    const card = main?.querySelector("[data-slot='work-card']");
    const body = card?.querySelector("[data-slot='card-content']");
    const grid = card?.querySelector("[role='grid'], [role='treegrid']");
    if (!(main instanceof HTMLElement) || !(card instanceof HTMLElement)) {
      throw new Error("the screen has no card of work");
    }
    if (!(body instanceof HTMLElement) || !(grid instanceof HTMLElement)) {
      throw new Error("the card has no body or no grid");
    }
    const frame = grid.parentElement;
    const style = getComputedStyle(body);
    const first = grid.querySelector("tbody tr");
    const date = Array.from(main.querySelectorAll("section")).find((section) =>
      /début de planning/i.test(section.getAttribute("aria-label") ?? ""),
    );
    const box = main.getBoundingClientRect();
    const around = card.getBoundingClientRect();
    return {
      main: { left: box.left, right: box.right, width: box.width },
      card: { left: around.left, right: around.right, bottom: around.bottom },
      body: body.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight),
      frame: frame?.getBoundingClientRect().width ?? 0,
      table: grid.getBoundingClientRect().width,
      row: first instanceof HTMLElement ? first.getBoundingClientRect().height : 0,
      start: date === undefined ? undefined : card.contains(date),
    };
  });
}

for (const address of GRIDS) {
  for (const size of WINDOWS) {
    test(`${address}: the card of the grid is as wide as the window, the grid as wide as the card, its rows as tall as ever, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
      page,
    }) => {
      const url = path(address);
      await compile(page.request, url);
      await page.setViewportSize(size);
      await page.goto(url);
      await expect(page.locator("main [role='grid'], main [role='treegrid']").first()).toBeVisible({
        timeout: WORKING,
      });
      await untilHydrated(page);
      const fit = await measure(page);
      // Tight, in no centred column: the card spans the window less the margin of the screen.
      expect(fit.card.left, "the card at the left margin").toBeCloseTo(fit.main.left + MARGIN, 0);
      expect(fit.card.right, "the card at the right margin").toBeGreaterThanOrEqual(
        fit.main.right - MARGIN - 20,
      );
      // It fills the window: its foot is no higher than the window, never above half of it.
      expect(fit.card.bottom).toBeGreaterThan(size.height / 2);
      expect(
        Math.abs(fit.frame - fit.body),
        "the frame is as wide as the body",
      ).toBeLessThanOrEqual(1);
      expect(fit.table, "the table fills its frame").toBeGreaterThanOrEqual(fit.frame - 2);
      if (fit.row > 0) {
        expect(fit.row, "the height of a row").toBeLessThanOrEqual(ROW + 4);
      }
      if (address.endsWith("/planning")) {
        expect(fit.start, "the planning start date is in the card").toBe(true);
      }
    });
  }
}

test("the task tree is in a card as wide as the window, no centred column [WF-IHM-0100-A]", async ({
  page,
}) => {
  const url = path(`${REVISION}/task-tree`);
  await compile(page.request, url);
  await page.setViewportSize(WINDOWS[0]);
  await page.goto(url);
  await expect(page.getByRole("tree")).toBeVisible({ timeout: WORKING });
  await untilHydrated(page);
  const { main, card } = await page.evaluate(() => {
    const screen = document.querySelector("main")?.getBoundingClientRect();
    const around = document.querySelector("main [data-slot='work-card']")?.getBoundingClientRect();
    if (screen === undefined || around === undefined) {
      throw new Error("no card in the task tree");
    }
    return { main: screen, card: around };
  });
  expect(card.left).toBeCloseTo(main.left + MARGIN, 0);
  expect(card.right).toBeGreaterThanOrEqual(main.right - MARGIN - 20);
});
