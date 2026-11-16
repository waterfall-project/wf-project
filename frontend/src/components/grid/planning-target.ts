// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The task a link leads to in the planning grid (WF-DEV-0090, US-2040/L3): the parameter `task` of
 * the address of the planning names a node of the structure read by its identifier (`node_id`),
 * and the grid, once hydrated, unfolds the rows above it and sets its active cell on it, the focus
 * with it (`useFoldCommands`). A parameter of the screen, as `structure`, `timeline` or `depth` are,
 * never sent to the API: the planning reads the whole tree, and the grid finds the row in it. An
 * identifier that is not one is ignored, as is a task the reading does not hold — a search or a
 * filter left it out —: the grid opens as it would without it.
 *
 * Neither server nor client: the page of the workload writes the link, the page of the planning
 * reads it.
 */
import { isUuid, type SearchParameters } from "@/navigation/context";

/** The parameter of the address of the planning that names the task to show and aim at. */
export const TASK_PARAMETER = "task";

/** The task the address names, if it names one by a well-formed identifier. */
export function targetTask(address: SearchParameters): string | undefined {
  const value = address.get(TASK_PARAMETER);
  return value !== null && isUuid(value) ? value : undefined;
}

/** The address of the planning, the parameter of a task added to the context it carries. */
export function onTask(href: string, node: string): string {
  const query = new URLSearchParams({ [TASK_PARAMETER]: node });
  return `${href}${href.includes("?") ? "&" : "?"}${query.toString()}`;
}
