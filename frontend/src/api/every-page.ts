// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A list the server pages, read whole: what a screen offers as a choice — the marked revisions a
 * workload or a comparison is computed on, the revisions of a project — must hold every item the
 * server has, not the first page of them (#303).
 *
 * Decision: every page is read, by the largest page the contract takes (`limit`, 500), one after
 * the other until the total the server says is reached — rather than one page of the largest size
 * with a notice past it: a choice that says "and more" offers no way to the rest, and a project
 * seldom has a second page of revisions. Each page is a read the screen cannot do without
 * (`readOrFail`). Server only: a list is read where the screen is rendered.
 */
import "server-only";

import type { components } from "./generated/schema";
import { type Answer, readOrFail } from "./problem";

/** The largest page the contract takes: `PaginationMeta.limit`, and the parameter `limit`. */
export const PAGE_LIMIT = 500;

/** The page a call is to ask: its size, and where it starts. */
export interface PageAsked {
  readonly limit: number;
  readonly offset: number;
}

/** A page of a list the server pages, as the contract shapes them. */
export interface PageAnswered<T> {
  readonly items: readonly T[];
  readonly meta: components["schemas"]["PaginationMeta"];
}

/**
 * Read every item of a list the server pages: `call` asks one page at the offset and size given,
 * and the pages are read until the total is reached. A page that comes empty before the total ends
 * the read: a server that paged otherwise than it said is not followed for ever.
 */
export async function readEveryPage<T>(
  operation: string,
  call: (page: PageAsked) => Promise<Answer<PageAnswered<T>>>,
): Promise<readonly T[]> {
  const items: T[] = [];
  for (;;) {
    const offset = items.length;
    const page = await readOrFail(operation, () => call({ limit: PAGE_LIMIT, offset }));
    items.push(...page.items);
    if (page.items.length === 0 || items.length >= page.meta.total) {
      return items;
    }
  }
}
