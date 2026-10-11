// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The initials of an account, which its avatar shows when it has no image (WF-ADM-0080): in the
 * menu of the account, and on the screen of its avatar. An anonymised account has no name, and no
 * initials (WF-ADM-0060).
 */
import type { components } from "@/api/generated/schema";

/** What the initials are made of: the name of the account. */
export type NamedAccount = Pick<components["schemas"]["User"], "first_name" | "last_name">;

/** The initials of a name, in the case of the language: a letter of each part; none without one. */
export function initials(account: NamedAccount, locale: string): string {
  const first = (text: string | null) => Array.from(text?.trim() ?? "")[0] ?? "";
  return `${first(account.first_name)}${first(account.last_name)}`.toLocaleUpperCase(locale);
}
