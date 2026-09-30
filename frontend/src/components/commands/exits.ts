// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The exits of the lifecycle of a project — the three commanded transitions (WF-CYC-0060) —
 * and the state each leads to. Data, read on the server by the list of the commands of a
 * project and in the browser by the confirmation of an exit: it lives outside the client module,
 * whose functions the server may not call.
 *
 * The table is exhaustive both ways, as the typing checks: each exit is a command of the
 * contract that leads to a state of `ProjectExit`, and each such state is led to by an exit.
 */
import type { components } from "@/api/generated/schema";

type ExitState = components["schemas"]["ProjectExit"]["to_state"];

/** A command of a project that takes it out of its lifecycle. */
export type ExitCommandName = Extract<
  components["schemas"]["ProjectCommand"],
  "complete" | "lose" | "abandon"
>;

/** The state each exit of the lifecycle leads to. */
export const EXIT_STATES = {
  complete: "completed",
  lose: "lost",
  abandon: "abandoned",
} as const satisfies Readonly<Record<ExitCommandName, ExitState>>;

/** A state of `ProjectExit` no exit leads to: none, or the typing says which. */
type Unreached = Exclude<ExitState, (typeof EXIT_STATES)[ExitCommandName]>;

/**
 * That every state an exit may lead to is led to by one of the exits: `true`, or a type error
 * naming the state the contract added without its exit.
 */
export const EVERY_EXIT_STATE_REACHED: [Unreached] extends [never] ? true : Unreached = true;

/** Whether a command of a project is an exit of its lifecycle. */
export function isExit(command: string): command is ExitCommandName {
  return Object.hasOwn(EXIT_STATES, command);
}
