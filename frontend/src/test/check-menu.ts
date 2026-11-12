// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * How a test drives the menu of a filter (`CheckMenu`, #2916): its button is named by its label and
 * by what it says (« État Tous les états »), and a value is a box to check — a radio, for a menu of
 * one choice — in the list the button opens, which stays open until Escape.
 */
import { screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";

/** Escape a text for a regular expression. */
function escaped(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** The button of the menu of a label. */
export function menuButton(label: string): HTMLElement {
  // Not the header of a column of the same name: only the button that opens a list.
  const [button, ...others] = screen
    .getAllByRole("button", { name: new RegExp(`^${escaped(label)}( |$)`) })
    .filter((each) => each.getAttribute("aria-haspopup") === "dialog");
  if (button === undefined || others.length > 0) {
    throw new Error(`no single menu named ${label}`);
  }
  return button;
}

/** What the button of the menu of a label says of what is chosen. */
export function menuSummary(label: string): string {
  return menuButton(label).textContent.trim();
}

/** Open the menu of a label, if it is not open; its list. */
export async function openMenu(label: string): Promise<HTMLElement> {
  const button = menuButton(label);
  if (button.getAttribute("aria-expanded") !== "true") {
    await userEvent.click(button);
  }
  return screen.findByRole("dialog");
}

/**
 * Check, or uncheck, a value in the menu of a label, and close the menu: the list is a modal
 * dialog, which hides the rest of the page from a test as from a reader until it is closed.
 */
export async function pick(
  label: string,
  value: string | RegExp,
  role: "checkbox" | "radio" = "checkbox",
): Promise<void> {
  const list = await openMenu(label);
  await userEvent.click(within(list).getByRole(role, { name: value }));
  await closeMenu();
}

/** Close the menu that is open, the focus back to its button. */
export async function closeMenu(): Promise<void> {
  await userEvent.keyboard("{Escape}");
}

/** Open the section of the filters of audit of a panel, folded until opened (#2916). */
export async function openAudit(): Promise<void> {
  const button = screen.getByRole("button", {
    name: "Filtres d’audit — création et modification",
  });
  if (button.getAttribute("aria-expanded") !== "true") {
    await userEvent.click(button);
  }
}
