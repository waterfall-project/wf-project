// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the forms of the way in and of the account share: the text of a field, sent as it is —
 * the API judges it, the front checks none of its rules —, and the look of a button that waits.
 */

/**
 * The classes of a button that cannot act for now — a request under way, a field still empty —:
 * marked `aria-disabled` rather than disabled, it keeps the focus the user gave it, and its
 * handler does nothing.
 */
export const WAITING = "aria-disabled:cursor-not-allowed aria-disabled:opacity-50";

/** The text of a field of a form submitted, empty when the form has none by that name. */
export function textOf(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === "string" ? value : "";
}
