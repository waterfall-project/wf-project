// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A page opened by its address, and the gestures that need React on it. The server renders the
 * page whole, and the browser shows it before React has hydrated it: a link followed then loads
 * its screen as a whole document, but a click on a button, a key typed in a cell, are lost — the
 * block of the navigation stays folded, the sort is never asked, and the journey waits for what
 * will never come until its end (#471). A journey opens a page here before any such gesture.
 */
import { type Locator, type Page, expect } from "@playwright/test";

/**
 * The bound of a screen of grid, in milliseconds: a dense grid — of the estimate, the planning,
 * the remaining, the risks, the actual costs, the portfolio, the reference data — or a screen that
 * reads the structure of a thousand tasks (`listNodes`) — the Kanban, the tree, the timelines —,
 * to show, to hydrate, or to read anew after a click. A bound of its working under load, not a
 * measure (#315); the risks and the actual costs, read anew, overran five seconds under load:
 * measures in #500, which is still to be decided. The settings of the costs, read anew for a
 * nature chosen, took from two to seven seconds under six workers on four processors — the read of
 * the server and the commit of the page up to four each (EP-02/L41g). Any other screen keeps the
 * five seconds of an assertion; the helpers below give a page that long to hydrate.
 */
export const WORKING = 15_000;

/** The cookie the shell keeps the last project context in, from an effect alone. */
const WITNESS = "wf_last_project";

/**
 * Open a screen of a project by its address, and wait until the shell has hydrated: the shell
 * writes the context it shows in its cookie from an effect, so after hydration alone. The cookie
 * of an earlier page is forgotten first, so that it cannot answer for this one; the context of a
 * project is the path of its screen, whatever it was sorted or searched by.
 */
export async function openHydrated(page: Page, address: string): Promise<void> {
  await page.context().clearCookies({ name: WITNESS });
  await page.goto(address);
  const shown = new URL(page.url()).pathname;
  await expect
    .poll(
      async () => {
        const cookies = await page.context().cookies();
        const witness = cookies.find(({ name }) => name === WITNESS)?.value;
        return witness === undefined ? undefined : decodeURIComponent(witness).split("?")[0];
      },
      { message: `the shell hydrated on ${shown}`, timeout: WORKING },
    )
    .toBe(shown);
}

/**
 * Open or close what a button discloses — a block of the navigation, a menu, the side bar — on a
 * page that may not be hydrated yet: no project is opened there, and nothing witnesses its
 * hydration. The button is pressed only while it does not say the state asked, so a press that
 * React answered is never undone, and pressed again until it says it.
 */
export async function setExpanded(button: Locator, expanded: boolean): Promise<void> {
  const state = String(expanded);
  await expect(async () => {
    if ((await button.getAttribute("aria-expanded")) !== state) {
      await button.click();
    }
    await expect(button).toHaveAttribute("aria-expanded", state, { timeout: 1_000 });
  }).toPass({ timeout: WORKING });
}

/**
 * Open a menu on a page that may not be hydrated yet, by the button that opens it: pressed only
 * while the menu is not shown, and again until it is. A menu hides the rest of the page from the
 * tree of accessibility while it is open, its button with it: it is the menu that says it opened.
 */
export async function openMenu(button: Locator, menu: Locator): Promise<void> {
  await expect(async () => {
    if (!(await menu.isVisible())) {
      await button.click();
    }
    await expect(menu).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
}

/**
 * Sort a dense grid by a column, ascending, on a page that may not be hydrated yet, with nothing
 * to witness it, and wait for the address of the sort. The button of the header is pressed only
 * while the header does not say it is sorted so — the grid shows a sort asked at once, before the
 * server answers — nor the grid busy reading, and again until the address says it. A sort is never
 * pressed blind: a press React answered and pressed again would turn it to descending.
 */
export async function sortUntilAddress(
  header: Locator,
  grid: Locator,
  address: string,
): Promise<void> {
  const page = header.page();
  await expect(async () => {
    const [sorted, busy] = await Promise.all([
      header.getAttribute("aria-sort"),
      grid.getAttribute("aria-busy"),
    ]);
    if (sorted !== "ascending" && busy !== "true") {
      await header.getByRole("button").click();
    }
    await expect(page).toHaveURL(address, { timeout: 1_000 });
    // The time to hydrate, then to read the grid anew: two bounds.
  }).toPass({ timeout: 2 * WORKING });
}
