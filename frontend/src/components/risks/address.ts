// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the risks reads of its address, besides the sort and the search of its grid
 * (`query.ts`): the states it filters on, under the name and in the form of the contract —
 * `states`, its values separated by commas (`explode: false`, `filters.ts`) —, which the server
 * filters by; and the risk whose detail it shows, `risk`. A header clicked, a state chosen, a risk
 * opened only change the address, and the page reads anew: the front filters nothing (WF-ARC-0020).
 *
 * Pure, and neither server nor client: the page reads, the screen writes.
 */
import type { components } from "@/api/generated/schema";
import type { SearchParameters } from "@/navigation/context";

/** The state of a risk, as the contract names it. */
export type RiskState = components["schemas"]["RiskState"];

/** The parameter of the address the states filtered on go by, as the contract names it. */
export const STATES = "states";

/** The parameter of the address that names the risk whose detail shows. */
export const RISK = "risk";

/**
 * Every state of the contract, in the order of its enumeration: one the contract adds fails the
 * type check until it is here.
 */
const EVERY_STATE: Readonly<Record<RiskState, number>> = {
  identified: 0,
  occurred: 1,
  dismissed: 2,
};

/** The states a risk may be in, in the order of the contract. */
export const RISK_STATES = Object.keys(EVERY_STATE) as readonly RiskState[];

/** An identifier the API may know: anything else names no risk, and is not asked. */
const IDENTIFIER = /^[\w-]+$/;

/** The risk whose detail the address asks for; none when it names none the API may know. */
export function readRisk(search: SearchParameters): string | undefined {
  const risk = search.get(RISK);
  return risk !== null && IDENTIFIER.test(risk) ? risk : undefined;
}

/** A path and its query. */
function address(pathname: string, query: URLSearchParams): string {
  const text = query.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}

/**
 * The address of the same screen with the detail of a risk — or without one —, the rest of its
 * query kept.
 */
export function riskHref(pathname: string, query: URLSearchParams, risk: string | undefined) {
  const next = new URLSearchParams(query);
  if (risk === undefined) {
    next.delete(RISK);
  } else {
    next.set(RISK, risk);
  }
  return address(pathname, next);
}
