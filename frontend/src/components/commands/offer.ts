// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a screen offers of a command (WF-IHM-0090): nothing when the user may not exercise it,
 * the command available, or the command unavailable with the conditions it lacks.
 *
 * On a project and a revision, the server says it: `available_commands` lists only the
 * commands the caller has the permission to exercise, each with the conditions it lacks — the
 * front does not know which permission guards which command, and deduces none of it
 * (WF-ARC-0020). One exception, decided by the user on 2026-10-05: without a current revision,
 * an import the caller may exercise but whose revision they may not create is listed
 * unavailable, lacking `may_create_revision`. Elsewhere — accounts, roles, reference data,
 * backups — the commands of a function follow its permission of modification in the session, the
 * restoration its own, `platform_restore`, and the creation of a project its own, `project_create`,
 * which no project lists, there being none yet: the rule of the catalogue itself (WF-ADM-0100),
 * with no condition to name; save those an object lists itself, as a project does — the
 * reactivation of an object of the reference data, the deactivation, the reactivation and the
 * attribution of the roles of an account (`available_commands`).
 *
 * Greying a command out is a convenience of reading, not a protection: the server judges the
 * command anyway, and its refusal is rendered (`OutcomeNotice`).
 */
import type { components } from "@/api/generated/schema";
import type { PlatformFunction, WritableFunction } from "@/navigation/functions";
import type { Permission } from "@/session/request";

/** A condition a command requires, named by the server when it lacks. */
export type CommandCondition = components["schemas"]["CommandCondition"];

/** Whether a command can be exercised now, and what it lacks when it cannot. */
export interface CommandOffer {
  readonly is_available: boolean;
  /** Empty when the command is available. */
  readonly missing_conditions: readonly CommandCondition[];
}

/** A command an object of the contract lists: a project's, a revision's. */
export interface ListedCommand<C extends string> extends CommandOffer {
  readonly command: C;
}

/**
 * The offer of a command an object lists, or `undefined` when it does not list it: the
 * caller lacks the permission to exercise it, and the command is not presented.
 */
export function findOffer<C extends string>(
  listed: readonly ListedCommand<C>[],
  command: C,
): ListedCommand<C> | undefined {
  return listed.find((offer) => offer.command === command);
}

/** The look of a command unavailable: greyed out, its cursor saying it does nothing. */
export const UNAVAILABLE = "aria-disabled:cursor-not-allowed aria-disabled:opacity-50";

/**
 * The identifier of the text that names what an offer lacks, from that of its command; none when
 * the command is available, or lacks nothing the server names.
 */
export function unmetId(offer: CommandOffer, id: string): string | undefined {
  return offer.is_available || offer.missing_conditions.length === 0 ? undefined : `${id}-unmet`;
}

/** A command a function outside any project offers: available, with nothing lacking. */
const GRANTED: CommandOffer = { is_available: true, missing_conditions: [] };

/**
 * The offer of a command of a function outside any project: available when the session holds
 * the permission of modification of the function — `users.write` for `users` —, `platform_restore`
 * for the restoration, or `project_create` for the creation of a project; `undefined` otherwise,
 * and the command is not presented. A function in reading alone — the journal of audit — has no
 * command to offer.
 */
export function platformOffer(
  permissions: readonly Permission[] | undefined,
  guard: (PlatformFunction & WritableFunction) | "platform_restore" | "project_create",
): CommandOffer | undefined {
  const needed =
    guard === "platform_restore" || guard === "project_create" ? guard : `${guard}.write`;
  return new Set<string>(permissions).has(needed) ? GRANTED : undefined;
}
