// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Scrolling a dense grid in a journey, as a user would with the wheel or the scroll bar: the
 * fake back serves a structure of a thousand tasks and five thousand lines (§4.6.2), of which
 * the grid renders only the rows in view — a row further down is reached by scrolling to it.
 */
import { expect, type Locator } from "@playwright/test";

/** The element a grid scrolls in. */
export function scroller(grid: Locator): Locator {
  return grid.locator("xpath=..");
}

/**
 * Scroll the page until the whole box of a grid is in the window. Only a window too low for the
 * grid at its least — its floor, and the header and indicators of its screen above it — needs
 * it: the page overflows it and scrolls; on any other, the grid holds in the window as it opens.
 */
export async function scrollPageToGrid(grid: Locator): Promise<void> {
  await scroller(grid).scrollIntoViewIfNeeded();
}

/**
 * Scroll a grid to its foot, until it stays there: the grid may still be taking its first
 * measures when the page shows.
 */
export async function scrollToFoot(grid: Locator): Promise<void> {
  await expect
    .poll(() =>
      scroller(grid).evaluate((element) => {
        element.scrollTop = element.scrollHeight;
        return (
          element.scrollTop > 0 &&
          element.scrollTop + element.clientHeight >= element.scrollHeight - 1
        );
      }),
    )
    .toBe(true);
}

/**
 * The row at a position among the rows of the answer, counted from 1 — its `aria-rowindex`, the
 * header being the first —, whatever number the service gave it.
 */
export function rowAt(grid: Locator, position: number): Locator {
  return grid.getByRole("row").and(grid.locator(`[aria-rowindex="${(position + 1).toString()}"]`));
}

/**
 * Scroll a grid until the row at a position among the rows of the answer is in the middle of its
 * box, by the height of the rows it renders — every row has the same —, and give that row.
 */
export async function scrollToPosition(grid: Locator, position: number): Promise<Locator> {
  const row = rowAt(grid, position);
  await expect
    .poll(async () => {
      await scroller(grid).evaluate((element, target) => {
        const rendered = element.querySelector("tbody tr[aria-rowindex]");
        const height = rendered?.getBoundingClientRect().height ?? 0;
        element.scrollTop = (target - 1) * height - element.clientHeight / 2;
      }, position);
      return row.count();
    })
    .toBe(1);
  return row;
}

/**
 * Whether an element lies wholly within the box of the element the grid scrolls in, and within
 * the window: the cells of the header and of the totals are what sticks to that box, their rows
 * keeping their place in the table — and a box whose edge is below the window hides them all
 * the same.
 *
 * The box, the element and the window are read at one moment, in one task of the page: read one
 * after the other, each could come from another layout. The grid of the planning lays out anew as it
 * hydrates — the legend of its Gantt, held until the Gantt measures its column, goes, and the grid
 * grows into its place —: under load, its box was read before and its totals after, each in place in
 * its own layout, out of place against each other (#1522).
 */
export async function withinBox(grid: Locator, element: Locator): Promise<boolean> {
  const frame = await scroller(grid).elementHandle();
  try {
    return await element.evaluate((target, box) => {
      const outer = box.getBoundingClientRect();
      const bounds = target.getBoundingClientRect();
      if (!box.isConnected || (bounds.width === 0 && bounds.height === 0)) {
        return false;
      }
      const top = Math.max(outer.top, 0);
      const bottom = Math.min(outer.bottom, window.innerHeight);
      return bounds.top >= top - 1 && bounds.bottom <= bottom + 1;
    }, frame);
  } finally {
    await frame.dispose();
  }
}
