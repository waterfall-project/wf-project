// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * When the page of a project proposes to start its planning (WF-PRJ-0030, #1058), which the page and
 * the encart read: the revision in progress lists the generation of the skeleton — the caller may
 * modify the planning — and does not lack `main_structure_without_tasks`, the condition the server
 * names while the main structure bears no task. The front deduces nothing else: not the tasks, not
 * the permission. The import of the schedule is offered as the project lists it. A module without
 * directive: the server page and the encart in the browser both read it.
 */
import { type CommandOffer, findOffer } from "@/components/commands/offer";
import type { Revision } from "@/components/context/read-only";
import type { Project } from "@/components/context/reading";
import { IMPORT_COMMAND } from "@/components/exchanges/offers";

/** What the encart offers: the skeleton, as the revision lists it, and the import, as the project. */
export interface StartOffers {
  readonly skeleton: CommandOffer;
  readonly planningImport: CommandOffer | undefined;
}

/**
 * What the start of the project offers, or nothing: no revision in progress, a revision that does not
 * list the skeleton, or a main structure that bears a task.
 */
export function startOffers(
  project: Project,
  revision: Revision | undefined,
): StartOffers | undefined {
  const skeleton =
    revision === undefined
      ? undefined
      : findOffer(revision.available_commands, "generate_skeleton");
  if (
    skeleton === undefined ||
    skeleton.missing_conditions.includes("main_structure_without_tasks")
  ) {
    return undefined;
  }
  return {
    skeleton,
    planningImport: findOffer(project.available_commands, IMPORT_COMMAND.ms_project_schedule),
  };
}

/** The key of the session storage that keeps an encart folded, for a project. */
export function foldedKey(projectId: string): string {
  return `waterfall.project-start.${projectId}`;
}
