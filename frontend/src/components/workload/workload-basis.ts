// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The basis a link to the workload of a project opens on (WF-DEV-0070, #1069): the estimate leads
 * to the reference budget once the project is under way or completed and has a reference revision —
 * the plan it committed to —, and to the remaining of the revision under way while it is priced;
 * the remaining to commit leads to the remaining of the revision under way, which it re-estimates.
 * The basis is a parameter of the address (`basis`), which the workload screen reads and sends to
 * the API; the front chooses a starting point, it computes nothing.
 */
import type { components } from "@/api/generated/schema";

type Project = components["schemas"]["Project"];

/** The basis of a workload, as the contract names it. */
type Basis = components["schemas"]["WorkloadPlan"]["basis"];

/** The address of the workload, opened on a basis: the parameter added to the context it carries. */
export function onBasis(href: string | undefined, basis: Basis): string | undefined {
  return href === undefined ? undefined : `${href}${href.includes("?") ? "&" : "?"}basis=${basis}`;
}

/**
 * The basis the estimate opens the workload on: the reference budget of a project in progress or
 * completed that has a reference revision — a basis the API refuses without one (409) —, the
 * remaining of the revision under way otherwise, in pricing in particular.
 */
export function estimateBasis(project: Pick<Project, "state" | "reference_revision_id">): Basis {
  const executed = project.state === "in_progress" || project.state === "completed";
  return executed && typeof project.reference_revision_id === "string"
    ? "reference_budget"
    : "current_remaining";
}
