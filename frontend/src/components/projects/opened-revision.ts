// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The revision a project opens on (US-0720): the screen of a project leads to the revision the
 * user works on, not to a sheet. The server decides it from what the API gives, nothing more.
 */
import type { components } from "@/api/generated/schema";

type Project = components["schemas"]["Project"];
type Revision = components["schemas"]["Revision"];

/**
 * The revision a project opens on: the one in progress, else the reference, else the last one
 * marked — the first of the list that is, the API listing the most recent first. `undefined` for
 * a project that lists no revision: it keeps its screen.
 */
export function openedRevision(
  project: Pick<Project, "current_revision_id" | "reference_revision_id">,
  revisions: readonly Pick<Revision, "revision_id" | "marked_at">[],
): string | undefined {
  if (revisions.length === 0) {
    return undefined;
  }
  return (
    project.current_revision_id ??
    project.reference_revision_id ??
    revisions.find((revision) => revision.marked_at !== null)?.revision_id
  );
}

/**
 * Whether an import is the one that creates the first revision of the project: its application
 * writes in no revision yet (`revision_id` null) and its kind writes in one — the actual costs
 * write in none. Its report stays on the screen of the project, which has no revision to show it in.
 */
export function createsFirstRevision(
  entry: Pick<components["schemas"]["Import"], "kind" | "revision_id">,
): boolean {
  return entry.revision_id === null && entry.kind !== "actual_costs";
}
