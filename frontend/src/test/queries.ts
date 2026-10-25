// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The query of a call a page made to the fake back, as the tests of the pages read it: its
 * parameters by name, the size of the pages left aside only when it is present and the default one,
 * fifty — every reading of a flat table sends it (WF-IHM-0060), and the test of each screen's page
 * size ("the size of the pages") says so, on the raw calls; the many tests of the other parameters
 * need not repeat it. A size that is not the default stays in the query, as does the larger one of
 * the readings of every page.
 */
import { DEFAULT_PAGE_SIZE } from "@/components/grid/query";

/** The parameters of a call, the default size of the pages left aside. */
export function queryOfCall(entries: Iterable<readonly [string, string]>): Record<string, string> {
  const query = Object.fromEntries(entries);
  if (query.limit === String(DEFAULT_PAGE_SIZE)) {
    delete query.limit;
  }
  return query;
}
