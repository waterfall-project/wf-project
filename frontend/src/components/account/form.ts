// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the forms of the way in and of the account read of what the user typed: the text of a
 * field, sent as it is — the API judges it, the front checks none of its rules.
 */

/** The text of a field of a form submitted, empty when the form has none by that name. */
export function textOf(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === "string" ? value : "";
}
