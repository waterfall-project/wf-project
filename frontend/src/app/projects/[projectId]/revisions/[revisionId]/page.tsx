// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A revision itself, which is no function of the navigation: the server leads to the grid of
 * its estimate (`…/estimate`), the reading context of the address carried on. The grid of the
 * planning comes with #105: whether a revision then opens on it is decided there.
 */
import { notFound, redirect } from "next/navigation";

import { type PageSearchParams, pageSearch, readContext } from "@/navigation/context";

/** The route parameters of a revision. */
export interface RevisionParams {
  readonly projectId: string;
  readonly revisionId: string;
}

/** The query of an address, as Next hands it to a page: a repeated parameter keeps each value. */
function queryOf(search: PageSearchParams): string {
  const query = new URLSearchParams();
  for (const [name, value] of Object.entries(search)) {
    for (const each of typeof value === "string" ? [value] : (value ?? [])) {
      query.append(name, each);
    }
  }
  const text = query.toString();
  return text === "" ? "" : `?${text}`;
}

/** Lead from a revision to the grid of its estimate, or to « not found » for no revision. */
export default async function RevisionPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const pathname = `/projects/${revision.projectId}/revisions/${revision.revisionId}`;
  if (readContext(pathname, pageSearch(search)) === undefined) {
    notFound();
  }
  redirect(`${pathname}/estimate${queryOf(search)}`);
}
