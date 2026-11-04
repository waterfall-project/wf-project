// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a grid of the structure on the nodes a risk occurred merged — the planning, the
 * estimate (WF-RIS-0060, WF-IHM-0130) —, as the address carries it, under the names of the
 * contract: `is_from_risk` for the tasks and the lines that came of any risk, `origin_risk_ids` for
 * those that came of one risk occurred, one at a time. The server retains the nodes, their ancestors
 * with them (`listNodes`); the front selects nothing, and passes the parameter on. The risks it is
 * chosen among are those the project lists as occurred (`listRisks`), never a list written here.
 *
 * Pure, and neither server nor client: the page reads the address, the filter writes it.
 */
import { isUuid, type SearchParameters } from "@/navigation/context";

import type { NodeFilters } from "./nodes";

/** The parameter of `listNodes` that retains the nodes of any risk occurred. */
export const ORIGIN_ANY_PARAMETER = "is_from_risk" as const;

/** The parameter of `listNodes` that retains the nodes of a risk occurred. */
export const ORIGIN_RISK_PARAMETER = "origin_risk_ids" as const;

/** The value of `is_from_risk` that retains the nodes that came of a risk. */
export const ORIGIN_ANY_VALUE = "true" as const;

/** What the address retains: the nodes of any risk occurred, or those of one. */
export type OriginFilter =
  { readonly kind: "any" } | { readonly kind: "risk"; readonly risk: string };

/**
 * The filter the address names: one risk when it names one (`origin_risk_ids`), the nodes of any
 * risk when `is_from_risk` is `true`; none otherwise. One alone is read — the filter offers one at
 * a time, and lifts the other when it writes —: what the grid sends is what its filter shows. A
 * value that is no identifier of the contract (`Uuid`) is not read, as if the address named
 * nothing: the API would refuse it. `is_from_risk=false` is not offered, nor read.
 */
export function readOriginFilter(search: SearchParameters): OriginFilter | undefined {
  const risk = (search.get(ORIGIN_RISK_PARAMETER) ?? "").split(",").find(isUuid);
  if (risk !== undefined) {
    return { kind: "risk", risk };
  }
  return search.get(ORIGIN_ANY_PARAMETER) === ORIGIN_ANY_VALUE ? { kind: "any" } : undefined;
}

/** What a reading of the nodes asks of the server for the filter: its one parameter, or nothing. */
export function originQuery(
  filter: OriginFilter | undefined,
): Pick<NodeFilters, typeof ORIGIN_ANY_PARAMETER | typeof ORIGIN_RISK_PARAMETER> {
  if (filter === undefined) {
    return {};
  }
  return filter.kind === "any" ? { is_from_risk: true } : { origin_risk_ids: [filter.risk] };
}

/** A risk occurred, by its identifier and its label. */
export interface OriginRisk {
  readonly id: string;
  readonly label: string;
}

/** The risks occurred a grid is filtered by, and the filter the address names. */
export interface OriginChoices {
  /** The risks the project lists as occurred, in the order of the API. */
  readonly risks: readonly OriginRisk[];
  readonly filter: OriginFilter | undefined;
}

/** The labels of the risks occurred by their identifier, which the mark of a row names its risk by. */
export function originNames(
  choices: OriginChoices | undefined,
): Readonly<Record<string, string>> | undefined {
  return choices === undefined
    ? undefined
    : Object.fromEntries(choices.risks.map(({ id, label }) => [id, label]));
}
