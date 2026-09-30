// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The exits of the lifecycle of a project — the three commanded transitions (WF-CYC-0060) —
 * and the state each leads to. Data, read on the server by the list of the commands of a
 * project and in the browser by the confirmation of an exit: it lives outside the client module,
 * whose functions the server may not call.
 */
import type { components } from "@/api/generated/schema";

type ExitState = components["schemas"]["ProjectExit"]["to_state"];

/** The state each exit of the lifecycle leads to. */
export const EXIT_STATES = {
  complete: "completed",
  lose: "lost",
  abandon: "abandoned",
} as const satisfies Readonly<Record<string, ExitState>>;

/** A command of a project that takes it out of its lifecycle. */
export type ExitCommandName = keyof typeof EXIT_STATES;

/** Whether a command of a project is an exit of its lifecycle. */
export function isExit(command: string): command is ExitCommandName {
  return Object.hasOwn(EXIT_STATES, command);
}
