// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pages of the online help still to write (US-0580), by the lot that writes each: the reading
 * of the files (`read.ts`) tells a page to come, which the panel says as such, from a page that
 * should exist and whose file is missing, a failure — a file the build did not carry, for one.
 * The lots that write them take their codes out of these lists; a test holds that no code named
 * here has its file, nor lacks a place in the table.
 */

/**
 * The codes whose page is still to write, by the lot that writes it: none since US-0670/L5 (#1452)
 * wrote the last nine, those of the indicators of a project. A code the table of the functions
 * gains is listed here with the lot that writes its page, or the test of completeness fails.
 */
export const SCREENS_TO_COME: Readonly<Record<string, string>> = {};

/**
 * The notions still to write, by the lot that writes them, which the pages may link to already: none
 * since US-0670/L3 (#1451) wrote the last five.
 */
export const NOTIONS_TO_COME: Readonly<Record<string, string>> = {};
