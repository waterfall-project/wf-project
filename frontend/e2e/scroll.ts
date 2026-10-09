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
 */
export async function withinBox(grid: Locator, element: Locator): Promise<boolean> {
  const box = await scroller(grid).boundingBox();
  const bounds = await element.boundingBox();
  const viewport = element.page().viewportSize();
  if (box === null || bounds === null || viewport === null) {
    return false;
  }
  const top = Math.max(box.y, 0);
  const bottom = Math.min(box.y + box.height, viewport.height);
  return bounds.y >= top - 1 && bounds.y + bounds.height <= bottom + 1;
}
