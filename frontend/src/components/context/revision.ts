// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The revisions of a project the banner of the reading context offers to read instead of the one
 * the screen reads (US-2330, WF-IHM-0020): every revision of the project, in the order the server
 * lists them — the most recent first —, named by its version name, the revision under way by what
 * it is. The revision chosen opens on the same screen, the sub-project filtered and the date of
 * calculation kept (WF-IHM-0010): in the path for a function of a revision, as the parameter
 * `revision_id` for a function of the project itself. Nothing else of the address is kept: a sort,
 * a search, a structure, a risk shown name what the revision left holds, which the one chosen may
 * not.
 *
 * Pure, and neither server nor client: the page reads the revisions, the choice writes the address.
 */
import type { components } from "@/api/generated/schema";
import { contextQuery, readContext } from "@/navigation/context";

/** A revision of the project, as the banner names it and offers it, and nothing more of it. */
export interface ListedRevision {
  readonly revision_id: string;
  /** Its version name; `null` for the revision under way, which has none. */
  readonly version_name: string | null;
  readonly is_reference: boolean;
}

/** What the banner names of a revision, and what crosses to the browser of it: nothing more. */
export function listedRevision({
  revision_id,
  version_name,
  is_reference,
}: Pick<
  components["schemas"]["Revision"],
  "revision_id" | "version_name" | "is_reference"
>): ListedRevision {
  return { revision_id, version_name, is_reference };
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
  const chosen = { ...context, revisionId };
  if (!context.revisionInPath || context.revisionId === undefined) {
    return pathname + contextQuery(chosen, true);
  }
  // A function of a revision, as `readContext` reads it: `/projects/{project}/revisions/{revision}`,
  // then the screen if any, which is kept.
  const revisionPath = (id: string) => `/projects/${context.projectId}/revisions/${id}`;
  const screen = pathname.slice(revisionPath(context.revisionId).length);
  return revisionPath(revisionId) + screen + contextQuery(chosen, false);
}
