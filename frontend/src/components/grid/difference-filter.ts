// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter « Écarts seulement » of a grid of a differential and of the comparison of two
 * revisions (US-0700, WF-REV-0100, WF-REV-0080), as the address carries it: `difference`, under the
 * name of the contract, a list of the differences to retain — `added`, `removed`, `modified` —,
 * written in one parameter, the values separated by commas (`explode: false`). « Écarts seulement »
 * names all three. The server retains the nodes whose difference is one of them, their ancestors
 * with them, so that the tree stays a tree (`listNodes`, `compareRevisions`); the front selects
 * nothing, and passes the parameter on.
 *
 * The filter is offered on the grid of a differential and on the comparison, where each node bears
 * a difference; never on the main structure nor on the own estimate of a risk, which bear none and
 * for which the server leaves the parameter without effect: the address's is then not read, nor said.
 *
 * Pure, and neither server nor client: the page reads the address, the filter writes it.
 */
import type { components } from "@/api/generated/schema";
import type { SearchParameters } from "@/navigation/context";

import { filterHref, readValues } from "./filters";

/** The parameter of `listNodes` and of `compareRevisions` that retains the differences named. */
export const DIFFERENCE_PARAMETER = "difference" as const;

/** A difference the filter retains: the schema of the contract, `NodeDifferenceFilter`. */
export type DifferenceValue = components["parameters"]["NodeDifferenceFilter"][number];

/** The differences of the contract, in its order: « Écarts seulement » names all of them. */
export const DIFFERENCE_VALUES = [
  "added",
  "removed",
  "modified",
] as const satisfies readonly DifferenceValue[];

/**
 * The differences the address retains, in the order of the contract; none when it names none or
 * only values the contract does not know — the server then reads no filter, which would refuse them.
 */
export function readDifferenceFilter(
  search: SearchParameters,
): readonly DifferenceValue[] | undefined {
  const values = readValues(search, DIFFERENCE_PARAMETER, DIFFERENCE_VALUES);
  return values.length === 0 ? undefined : values;
}

/** Whether the filter retains every difference: « Écarts seulement », as the grid offers it. */
export function isDifferencesOnly(filter: readonly DifferenceValue[] | undefined): boolean {
  return filter?.length === DIFFERENCE_VALUES.length;
}

/** What a reading asks of the server for the filter: its one parameter, or nothing. */
export function differenceQuery(filter: readonly DifferenceValue[] | undefined): {
  readonly difference?: DifferenceValue[];
} {
  return filter === undefined ? {} : { difference: [...filter] };
}

/**
 * The address of the same screen with « Écarts seulement » set — every difference named — or
 * lifted, the rest of its query kept.
 */
export function differencesOnlyHref(
  pathname: string,
  query: URLSearchParams,
  only: boolean,
): string {
  return filterHref(pathname, query, DIFFERENCE_PARAMETER, only ? DIFFERENCE_VALUES.join(",") : "");
}
