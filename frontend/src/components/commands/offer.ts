// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a screen offers of a command (WF-IHM-0090): nothing when the user may not exercise it,
 * the command available, or the command unavailable with the conditions it lacks.
 *
 * On a project and a revision, the server says it: `available_commands` lists only the
 * commands the caller has the permission to exercise, each with the conditions it lacks — the
 * front does not know which permission guards which command, and deduces none of it
 * (WF-ARC-0020). Elsewhere — accounts, roles, reference data, backups — the commands of a
 * function follow its permission of modification in the session, and the restoration its own,
 * `platform_restore`: the rule of the catalogue itself (WF-ADM-0100), with no condition to
 * name.
 *
 * Greying a command out is a convenience of reading, not a protection: the server judges the
 * command anyway, and its refusal is rendered (`OutcomeNotice`).
 */
import type { components } from "@/api/generated/schema";
import type { PlatformFunction } from "@/navigation/functions";
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

/** A command a function outside any project offers: available, with nothing lacking. */
const GRANTED: CommandOffer = { is_available: true, missing_conditions: [] };

/**
 * The offer of a command of a function outside any project: available when the session holds
 * the permission of modification of the function — `users.write` for `users` —, or
 * `platform_restore` for the restoration; `undefined` otherwise, and the command is not
 * presented.
 */
export function platformOffer(
  permissions: readonly Permission[] | undefined,
  guard: PlatformFunction | "platform_restore",
): CommandOffer | undefined {
  const needed = guard === "platform_restore" ? guard : `${guard}.write`;
  return new Set<string>(permissions).has(needed) ? GRANTED : undefined;
}
