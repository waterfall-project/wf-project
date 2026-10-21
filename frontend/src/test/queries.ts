// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The query of a call a page made to the fake back, as the tests of the pages read it: its
 * parameters by name, the size of the pages left aside when it is the default one, fifty — every
 * reading of a flat table sends it (WF-IHM-0060), and `page-size.test.tsx` and the test of each
 * screen's page size say so; the many tests of the other parameters need not repeat it. A size that
 * is not the default stays in the query, as does the larger one of the readings of every page.
 */
import { DEFAULT_PAGE_SIZE } from "@/components/grid/query";

/** The parameters of a call, the default size of the pages left aside. */
export function queryOfCall(entries: Iterable<readonly [string, string]>): Record<string, string> {
  const { limit, ...rest } = Object.fromEntries(entries);
  return limit === String(DEFAULT_PAGE_SIZE) || limit === undefined ? rest : { limit, ...rest };
}
