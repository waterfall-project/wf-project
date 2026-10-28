// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pages of the online help still to write (US-0580), by the lot that writes each: the reading
 * of the files (`read.ts`) tells a page to come, which the panel says as such, from a page that
 * should exist and whose file is missing, a failure — a file the build did not carry, for one.
 * The lots that write them take their codes out of these lists; a test holds that no code named
 * here has its file, nor lacks a place in the table.
 */

/** The codes whose page is still to write, by the lot that writes it. */
export const SCREENS_TO_COME: Readonly<Record<string, string>> = Object.fromEntries([
  ...[
    "FBS-3.1",
    "FBS-3.1.1",
    "FBS-3.1.2",
    "FBS-3.1.3",
    "FBS-3.2",
    "FBS-3.2.1",
    "FBS-3.2.2",
    "FBS-3.2.3",
    "FBS-3.3",
    "FBS-3.4",
  ].map((code) => [code, "US-0670/L3, #1451"] as const),
  ...[
    "FBS-4",
    "FBS-4.2",
    "FBS-4.2.1",
    "FBS-4.2.2",
    "FBS-4.2.3",
    "FBS-4.2.4",
    "FBS-4.2.5",
    "FBS-4.3.1",
    "FBS-4.3.4",
    "FBS-4.3.5",
    "FBS-4.4.4",
    "FBS-4.5.3",
    "FBS-4.7",
    "FBS-4.8",
    "FBS-4.8.1",
    "FBS-4.8.2",
    "FBS-4.8.3",
    "FBS-4.8.4",
    "FBS-4.8.5",
    "FBS-4.8.6",
    "FBS-4.8.7",
    "FBS-4.8.8",
    "FBS-4.9",
  ].map((code) => [code, "US-0670/L4, #1140"] as const),
]);

/** The notions still to write, by the lot that writes them, which the pages may link to already. */
export const NOTIONS_TO_COME: Readonly<Record<string, string>> = {
  "reste-a-engager": "US-0670/L3, #1451",
  "provision-et-reserve": "US-0670/L3, #1451",
  "avenant-et-differentiel": "US-0670/L3, #1451",
  lotissement: "US-0670/L3, #1451",
  "chemin-critique": "US-0670/L3, #1451",
};
