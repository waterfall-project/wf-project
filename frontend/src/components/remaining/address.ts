// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the remaining to commit reads of its address, besides the sort and the search
 * of its grid (`query.ts`): the states of the tasks whose lines it shows, under the name and in the
 * form of the contract — `progress`, its values separated by commas (`explode: false`) —, which the
 * server filters by. The grid shows the lines of the tasks started alone, unless the address asks
 * more: the user makes the tasks not started appear to re-estimate them (WF-RAE-0040). A link
 * changes the address, and the page reads anew: the front filters nothing (WF-ARC-0020).
 *
 * Pure, and neither server nor client.
 */
import type { components } from "@/api/generated/schema";
import type { SearchParameters } from "@/navigation/context";

/** The state of a task, as the contract names it. */
export type TaskProgress = components["schemas"]["TaskProgress"];

/** The parameter of the address the states of the tasks go by, as the contract names it. */
export const PROGRESS = "progress";

/**
 * Every state of the contract, in the order of its enumeration: one the contract adds fails the
 * type check until it is here.
 */
const EVERY_STATE: Readonly<Record<TaskProgress, number>> = {
  not_started: 0,
  started: 1,
  completed: 2,
};

/** The states of a task, in the order of the contract. */
const STATES = Object.keys(EVERY_STATE) as readonly TaskProgress[];

/** What the grid shows when the address asks nothing: the lines of the tasks started. */
const STARTED: readonly TaskProgress[] = ["started"];

/** What the grid shows once the tasks not started are asked for too. */
const STARTED_AND_NOT: readonly TaskProgress[] = ["not_started", "started"];

/**
 * The states of the tasks the address asks the lines of, in the order of the contract, each once;
 * the tasks started when it asks none the contract knows — a value the API would refuse is not
 * asked.
 */
export function readProgress(search: SearchParameters): readonly TaskProgress[] {
  const asked = new Set((search.get(PROGRESS) ?? "").split(","));
  const states = STATES.filter((state) => asked.has(state));
  return states.length === 0 ? STARTED : states;
}

/**
 * The address of the same screen showing the tasks not started too, or the tasks started alone,
 * the rest of its query kept: the reading context, the sort, the search.
 */
export function progressHref(pathname: string, query: URLSearchParams, notStarted: boolean) {
  const next = new URLSearchParams(query);
  if (notStarted) {
    next.set(PROGRESS, STARTED_AND_NOT.join(","));
  } else {
    next.delete(PROGRESS);
  }
  const text = next.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}
