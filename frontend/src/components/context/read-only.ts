// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Whether a revision is read only (WF-IHM-0020): the API says it is marked, or none of its
 * commands of modification is available to the caller. The screen reads `status` and
 * `available_commands`, and deduces nothing else — which permission guards which command is
 * the server's to know.
 */
import type { components } from "@/api/generated/schema";

/** A revision of a project, as the API reads it. */
export type Revision = components["schemas"]["Revision"];

type RevisionStatus = components["schemas"]["RevisionStatus"];
type RevisionCommand = components["schemas"]["RevisionCommand"];

/** A command that modifies what a revision holds: its planning, its estimate, its remaining. */
export type EditCommand = Extract<RevisionCommand, `edit_${string}`>;

/**
 * Whether a status leaves a revision open to modification. Every status of the contract is
 * named: one added to the contract fails the type check until it is classified here.
 */
const OPEN_STATUS: Readonly<Record<RevisionStatus, boolean>> = {
  draft: true,
  marked: false,
};

/** Whether a command of a revision is one of modification. */
export function isEdit(command: RevisionCommand): command is EditCommand {
  return command.startsWith("edit_");
}

/** The commands of modification of a revision the caller may exercise now. */
export function availableEdits(revision: Revision): ReadonlySet<EditCommand> {
  const edits = revision.available_commands
    .filter((offered) => offered.is_available)
    .map((offered) => offered.command)
    .filter(isEdit);
  return new Set(OPEN_STATUS[revision.status] ? edits : []);
}

/**
 * Whether a revision is read only: marked, or without any command of modification available
 * — absent from its commands, or unavailable. A screen offers no command of modification on
 * it.
 */
export function isReadOnly(revision: Revision): boolean {
  return availableEdits(revision).size === 0;
}
