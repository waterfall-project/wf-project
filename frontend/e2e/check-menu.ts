// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The menu of a list of values of a filter in a journey (`CheckMenu`, #2916): its button is named
 * by its label and what it says (« État Tous les états »), and opens a list of boxes to check — of
 * radios, for a menu of one choice — that stays open until Escape or a click away.
 */
import { expect, type Locator, type Page } from "@playwright/test";

/** The button of the menu of a label, not the header of a column of the same name. */
export function menuButton(page: Page, label: string): Locator {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return page
    .getByRole("button", { name: new RegExp(`^${escaped}( |$)`) })
    .and(page.locator('[aria-haspopup="dialog"]'));
}

/** Open the menu of a label, if it is not open; its list. */
export async function openMenu(page: Page, label: string): Promise<Locator> {
  const button = menuButton(page, label);
  if ((await button.getAttribute("aria-expanded")) !== "true") {
    await button.click();
  }
  const list = page.getByRole("dialog");
  await expect(list).toBeVisible();
  return list;
}

/**
 * Check, or uncheck, a value in the menu of a label, and close the menu: its list is a modal
 * dialog, which hides the rest of the page until it is closed. What is chosen is read on the button.
 */
export async function pick(
  page: Page,
  label: string,
  value: string,
  role: "checkbox" | "radio" = "checkbox",
): Promise<void> {
  const list = await openMenu(page, label);
  await list.getByRole(role, { name: value, exact: true }).click();
  await closeMenu(page);
}

/** Open the section of the filters of audit of a panel, folded until opened. */
export async function openAudit(page: Page): Promise<void> {
  const button = page.getByRole("button", { name: "Filtres d’audit — création et modification" });
  if ((await button.getAttribute("aria-expanded")) !== "true") {
    await button.click();
  }
}

/** Close the menu that is open. */
export async function closeMenu(page: Page): Promise<void> {
  if ((await page.getByRole("dialog").count()) > 0) {
    await page.keyboard.press("Escape");
  }
  await expect(page.getByRole("dialog")).toBeHidden();
}
