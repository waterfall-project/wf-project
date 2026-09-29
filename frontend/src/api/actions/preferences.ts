// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the display preferences of the account (`updateMyPreferences`):
 * the browser asks the server of Next, which calls the API (§4.3.1), and gets back the
 * outcome the one decoder makes of its answer (`src/api/problem.ts`).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

type DisplayPreferences = components["schemas"]["DisplayPreferences"];

/**
 * Record a display preference of the account, and render the page again: the next render
 * reads the preferences anew, so the change applies without signing in again. The value is
 * the API's to judge — a server action is reachable by any request, and the contract refuses
 * what is not one of the values of the field.
 */
async function update(preferences: DisplayPreferences): Promise<Outcome<DisplayPreferences>> {
  const outcome = await decode(() =>
    serverClient().PATCH("/me/preferences", { body: preferences }),
  );
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/** Record the language of the interface: `default`, `fr` or `en` (WF-INTF-0160). */
export async function updateLanguage(
  language: NonNullable<DisplayPreferences["language"]>,
): Promise<Outcome<DisplayPreferences>> {
  return update({ language });
}

/**
 * Record the language and the mode together, as the screen of the account submits them: the
 * same fields the menu of the account writes one at a time.
 */
export async function updateDisplay(
  preferences: Required<Pick<DisplayPreferences, "language" | "theme">>,
): Promise<Outcome<DisplayPreferences>> {
  return update({ language: preferences.language, theme: preferences.theme });
}

/** Record the display mode: `default`, which follows the workstation, `light` or `dark`. */
export async function updateTheme(
  theme: NonNullable<DisplayPreferences["theme"]>,
): Promise<Outcome<DisplayPreferences>> {
  return update({ theme });
}
