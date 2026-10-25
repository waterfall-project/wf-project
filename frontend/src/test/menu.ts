// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The text of an item of a menu as a screen reader reads it, for the tests that list what a menu
 * offers: the keys the item shows at its end (`Keys`, US-0580), hidden from a screen reader, which
 * reads them from `aria-keyshortcuts`, left out.
 */

/** The text of an item, without what it hides from a screen reader. */
export function spokenText(item: Element): string {
  return [...item.childNodes]
    .filter((node) => !(node instanceof Element && node.getAttribute("aria-hidden") === "true"))
    .map((node) => node.textContent)
    .join("");
}
