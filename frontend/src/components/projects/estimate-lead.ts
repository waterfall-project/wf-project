// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Where the deletion of a sub-project that estimate lines of the revision in progress bear leads
 * (EP-14/L53): to the estimate of that revision, filtered on the sub-project, where the lines of its
 * main structure show, to be passed out of it (`subproject_without_estimate_lines`, WF-DAT-0080).
 * The page knows the revision and the session; the list, the conditions a deletion lacks. What both
 * read lives here, in a module without directive.
 */
import type { components } from "@/api/generated/schema";
import type { CommandCondition } from "@/components/commands/offer";
import type { Project } from "@/components/context/reading";

/** The session of the request: its effective permissions among the rest. */
type Session = components["schemas"]["Session"];

/**
 * The revision in progress whose estimate a deletion leads to, for a session that reads the
 * estimate; none for another session, or for a project without a revision in progress.
 */
export function estimatedRevision(
  project: Project,
  session: Session | undefined,
): string | undefined {
  return session?.permissions.includes("estimate.read") === true
    ? (project.current_revision_id ?? undefined)
    : undefined;
}

/**
 * Whether a deletion lacks, `project_not_terminal` aside, the passing of the estimate lines that bear
 * its sub-project alone — which the estimate lifts. A citation by a marked revision or actual costs,
 * which no line passed lifts, lead nowhere.
 */
export function leadsToEstimate(missing: readonly CommandCondition[]): boolean {
  const lifted = missing.filter((condition) => condition !== "project_not_terminal");
  return lifted.length === 1 && lifted[0] === "subproject_without_estimate_lines";
}
