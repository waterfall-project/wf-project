// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The revisions of a project the banner of the reading context offers to read instead of the one
 * the screen reads (US-2330, WF-IHM-0020): every revision of the project, in the order the server
 * lists them — the most recent first —, named by its version name, the revision under way by what
 * it is. The revision chosen opens on the same screen, the sub-project filtered and the date of
 * calculation kept (WF-IHM-0010): in the path for a function of a revision, as the parameter
 * `revision_id` for a function of the project itself. The base of a comparison is kept too, unless
 * the revision chosen is the base itself, which lifts the comparison (decision of the author of
 * 2026-11-15). Nothing else of the address is kept: a sort, a search, a structure, a risk shown name
 * what the revision left holds, which the one chosen may not.
 *
 * On the three grids that compare, read on the main structure, the banner offers for base the marked
 * revisions of the project but the one read (`baseOptions`, #3176): the revision the one read is a
 * copy of first, then the reference, then the others in the order the server lists them, the most
 * recent first (decision of the author of 2026-11-14, #3178).
 *
 * Pure, and neither server nor client: the page reads the revisions, the choice writes the address.
 */
import type { components } from "@/api/generated/schema";
import { filterHref } from "@/components/grid/filters";
import { BASE_PARAMETER, contextQuery, readContext } from "@/navigation/context";

/** A revision of the project, as the banner names it and offers it, and nothing more of it. */
export interface ListedRevision {
  readonly revision_id: string;
  /** Its version name; `null` for the revision under way, which has none. */
  readonly version_name: string | null;
  /** Whether it is marked, which a base must be (WF-REV-0080), or the draft under way. */
  readonly status: components["schemas"]["RevisionStatus"];
  readonly is_reference: boolean;
}

/** The base a grid is compared to, as the address names it, and the bases the banner offers. */
export interface BaseChoices {
  /** The base the address names; none when the grid compares nothing. */
  readonly chosen: string | undefined;
  /** The bases offered, in their order (`baseOptions`). */
  readonly offered: readonly ListedRevision[];
}

/** What the banner names of a revision, and what crosses to the browser of it: nothing more. */
export function listedRevision({
  revision_id,
  version_name,
  status,
  is_reference,
}: Pick<
  components["schemas"]["Revision"],
  "revision_id" | "version_name" | "status" | "is_reference"
>): ListedRevision {
  return { revision_id, version_name, status, is_reference };
}

/**
 * The address of the same screen on another revision, from the address a change goes on from —
 * its path, and the query last asked —: the revision in the path when the path names one, as
 * `revision_id` otherwise; the sub-project and the date of calculation kept, nothing else.
 * The path itself when it is no screen of a project, which offers no revision to choose.
 */
export function revisionHref(pathname: string, query: URLSearchParams, revisionId: string): string {
  const context = readContext(pathname, query);
  if (context === undefined) {
    return pathname;
  }
  // The base chosen for revision read lifts the comparison: a revision compared to itself.
  const chosen = {
    ...context,
    revisionId,
    base: context.base === revisionId ? undefined : context.base,
  };
  if (!context.revisionInPath || context.revisionId === undefined) {
    return pathname + contextQuery(chosen, true);
  }
  // A function of a revision, as `readContext` reads it: `/projects/{project}/revisions/{revision}`,
  // then the screen if any, which is kept.
  const revisionPath = (id: string) => `/projects/${context.projectId}/revisions/${id}`;
  const screen = pathname.slice(revisionPath(context.revisionId).length);
  return revisionPath(revisionId) + screen + contextQuery(chosen, false, false, true);
}

/**
 * The address of the same screen compared to a base, or no longer compared (`undefined`), the rest
 * of its query kept — the filters, the sort, the search.
 */
export function baseHref(
  pathname: string,
  query: URLSearchParams,
  baseId: string | undefined,
): string {
  return filterHref(pathname, query, BASE_PARAMETER, baseId);
}

/**
 * The bases the banner offers to the revision read, among the revisions of the project as the server
 * lists them: the marked ones but the revision read — the revision it is a copy of
 * (`source_revision_id`) first, then the reference, then the others in the order of the server.
 */
export function baseOptions(
  revisions: readonly ListedRevision[],
  read: { readonly revision_id: string; readonly source_revision_id: string | null },
): ListedRevision[] {
  const marked = revisions.filter(
    (revision) => revision.status === "marked" && revision.revision_id !== read.revision_id,
  );
  const rank = (revision: ListedRevision) => {
    if (revision.revision_id === read.source_revision_id) {
      return 0;
    }
    return revision.is_reference ? 1 : 2;
  };
  // A stable sort: the revisions of one rank keep the order of the server.
  return marked.toSorted((one, other) => rank(one) - rank(other));
}
