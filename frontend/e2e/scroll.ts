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
 * Scroll a grid until the row of a number is in the middle of its box, by the height of the
 * rows it renders — every row has the same.
 */
export async function scrollToRow(grid: Locator, rowNumber: number): Promise<void> {
  const row = grid.getByRole("row", { name: new RegExp(`^${rowNumber.toString()} `) });
  await expect
    .poll(async () => {
      await scroller(grid).evaluate((element, target) => {
        const rendered = element.querySelector("tbody tr[aria-rowindex]");
        const height = rendered?.getBoundingClientRect().height ?? 0;
        element.scrollTop = (target - 1) * height - element.clientHeight / 2;
      }, rowNumber);
      return row.count();
    })
    .toBe(1);
}

/**
 * Whether an element lies wholly within the box of the element the grid scrolls in: the cells
 * of the header and of the totals are what sticks, their rows keep their place in the table.
 */
export async function withinBox(grid: Locator, element: Locator): Promise<boolean> {
  const box = await scroller(grid).boundingBox();
  const bounds = await element.boundingBox();
  if (box === null || bounds === null) {
    return false;
  }
  return bounds.y >= box.y - 1 && bounds.y + bounds.height <= box.y + box.height + 1;
}
