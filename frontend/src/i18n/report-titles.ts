// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the title of a report begins with, kept in one place for the path that asserts no report is
 * shown (`frontend/e2e/exchanges.spec.ts`, `ANY_REPORT`) and the test that the titles of the
 * catalogue all open with it (`report-titles.test.ts`, #4299). No dependency: Playwright imports it.
 */

/** How many words of a title make what every report of the catalogue begins with. */
const WORDS = 2;

/** The first words of a title of a report: what any report of the catalogue begins with. */
export function firstWords(title: string): string {
  return title.split(" ", WORDS).join(" ");
}
