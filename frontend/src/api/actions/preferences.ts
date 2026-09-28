// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the display preferences of the account (`updateMyPreferences`):
 * the browser asks the server of Next, which calls the API (§4.3.1).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { serverClient } from "@/api/server";

type DisplayPreferences = components["schemas"]["DisplayPreferences"];
type Problem = components["schemas"]["Problem"];

/** What an action gives back: the answer of the API, or its refusal, never both. */
export type Outcome<T> =
  | { readonly data: T; readonly problem?: never }
  | { readonly problem: Problem; readonly data?: never };

/**
 * Record a display preference of the account, and render the page again: the next render
 * reads the preferences anew, so the change applies without signing in again. The value is
 * the API's to judge — a server action is reachable by any request, and the contract refuses
 * what is not one of the values of the field.
 */
async function update(preferences: DisplayPreferences): Promise<Outcome<DisplayPreferences>> {
  const { data, error } = await serverClient().PATCH("/me/preferences", { body: preferences });
  if (error !== undefined) {
    return { problem: error };
  }
  refresh();
  return { data };
}

/** Record the language of the interface: `default`, `fr` or `en` (WF-INTF-0160). */
export async function updateLanguage(
  language: NonNullable<DisplayPreferences["language"]>,
): Promise<Outcome<DisplayPreferences>> {
  return update({ language });
}

/** Record the display mode: `default`, which follows the workstation, `light` or `dark`. */
export async function updateTheme(
  theme: NonNullable<DisplayPreferences["theme"]>,
): Promise<Outcome<DisplayPreferences>> {
  return update({ theme });
}
