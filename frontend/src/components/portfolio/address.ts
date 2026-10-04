// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the portfolio read of their address (WF-PTF-0010): the perimeter every view
 * is computed on, under the names of the contract — the states retained, `states`, its values
 * separated by commas (`explode: false`); the period of the projects completed and of the
 * statistics of a period, `from` and `to`; the date of calculation, `as_of`; the node of
 * organisation whose roles the labour lines are restricted to, `org_node_id` — and the parameters
 * of a view: its horizon, `horizon_months`, and the threshold of under-load the user chooses at the
 * consultation, `under_load_threshold` (WF-PTF-0060), neither kept from one consultation to the
 * next. A choice only changes the address, and the page reads anew: the server computes, sorts and
 * filters, the front nothing (WF-ARC-0020).
 *
 * Pure, and neither server nor client: the page reads, the screen writes.
 */
import type { components } from "@/api/generated/schema";
import { OFFSET } from "@/components/grid/query";
import { isPlanningDate } from "@/i18n/format";
import type { SearchParameters } from "@/navigation/context";

/** The state of a project, as the contract names it. */
export type ProjectState = components["schemas"]["ProjectState"];

/** The perimeter a view of the portfolio is computed on, as the server retained it. */
export type PortfolioScope = components["schemas"]["PortfolioScope"];

/** The parameters of the address, as the contract names them. */
export const STATES = "states";
export const FROM = "from";
export const TO = "to";
export const AS_OF = "as_of";
export const ORG_NODE = "org_node_id";
export const HORIZON = "horizon_months";
export const THRESHOLD = "under_load_threshold";

/**
 * The states a portfolio retains (WF-PTF-0010): the projects in progress, the offers in pricing
 * the user may add, and the projects completed over a period. Every other state is out of any
 * portfolio.
 */
export const PORTFOLIO_STATES: readonly ProjectState[] = ["in_progress", "pricing", "completed"];

/**
 * The horizons a view proposes, in months: half a year, a year, two years. Proposals only: any
 * horizon the contract takes, from 1 to 240 months, is asked when the address names it.
 */
export const HORIZONS = ["6", "12", "24"] as const;

/** The longest horizon the contract takes, in months. */
const LONGEST_HORIZON = 240;

/**
 * The thresholds of under-load the aggregated workload proposes, as the contract writes them.
 * Proposals only: any threshold the contract takes is asked when the address names it.
 */
export const THRESHOLDS = ["0.3", "0.5", "0.7"] as const;

/** A decimal as the contract writes a `Percent`. */
const DECIMAL = /^-?\d+(\.\d+)?$/;

/** The perimeter the address asks; what it does not name, the server chooses. */
export interface Perimeter {
  readonly states: readonly ProjectState[];
  readonly from: string | undefined;
  readonly to: string | undefined;
  readonly asOf: string | undefined;
  readonly orgNode: string | undefined;
}

/** An identifier the API may know: anything else names no node, and is not asked. */
const IDENTIFIER = /^[\w-]+$/;

/** A date of the address the API may take; none otherwise — 30 February is not asked. */
function dateOf(search: SearchParameters, name: string): string | undefined {
  const value = search.get(name);
  return value !== null && isPlanningDate(value) ? value : undefined;
}

/**
 * The states the address retains, in the order of the portfolio, each once; none when it names
 * none — those the server retains by default. A value that is no state of a portfolio is not asked.
 */
export function readStates(search: SearchParameters): readonly ProjectState[] {
  const asked = new Set((search.get(STATES) ?? "").split(","));
  return PORTFOLIO_STATES.filter((state) => asked.has(state));
}

/** An identifier of the address the API may know; none otherwise. */
function identifierOf(search: SearchParameters, name: string): string | undefined {
  const value = search.get(name);
  return value !== null && IDENTIFIER.test(value) ? value : undefined;
}

/** Read the perimeter the address asks; a value the contract would refuse is not asked. */
export function readPerimeter(search: SearchParameters): Perimeter {
  return {
    states: readStates(search),
    from: dateOf(search, FROM),
    to: dateOf(search, TO),
    asOf: dateOf(search, AS_OF),
    orgNode: identifierOf(search, ORG_NODE),
  };
}

/** The horizon the address asks, a whole number of months the contract takes; none otherwise. */
export function readHorizon(search: SearchParameters): string | undefined {
  const value = search.get(HORIZON);
  return value !== null && /^[1-9]\d{0,2}$/.test(value) && Number(value) <= LONGEST_HORIZON
    ? value
    : undefined;
}

/** The threshold of under-load the address asks, a `Percent` of the contract; none otherwise. */
export function readThreshold(search: SearchParameters): string | undefined {
  const value = search.get(THRESHOLD);
  return value !== null && DECIMAL.test(value) ? value : undefined;
}

/**
 * What of the perimeter a view takes, besides its states and its date of calculation: a period,
 * a node of organisation. Every view takes both but those the contract gives neither or one.
 */
export interface Takes {
  readonly period: boolean;
  readonly node: boolean;
}

/** A view that takes the whole perimeter. */
export const WHOLE: Takes = { period: true, node: true };

/**
 * The query of the perimeter, as the client of the contract sends it: what is asked alone, and of
 * that, what the view takes.
 */
export function perimeterQuery(perimeter: Perimeter, takes: Takes = WHOLE) {
  const { from, to, orgNode } = perimeter;
  return {
    ...(perimeter.states.length === 0 ? {} : { states: [...perimeter.states] }),
    ...(!takes.period || from === undefined ? {} : { from }),
    ...(!takes.period || to === undefined ? {} : { to }),
    ...(perimeter.asOf === undefined ? {} : { as_of: perimeter.asOf }),
    ...(!takes.node || orgNode === undefined ? {} : { org_node_id: orgNode }),
  };
}

/** A path and its query. */
function address(pathname: string, query: URLSearchParams): string {
  const text = query.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}

/** Set a parameter of a query, or remove it when it has no value. */
function put(query: URLSearchParams, name: string, value: string | undefined) {
  if (value === undefined || value === "") {
    query.delete(name);
  } else {
    query.set(name, value);
  }
}

/**
 * The address of the same screen with other parameters — none removing one —, back to the first
 * page of its list, the rest of its query kept: the sort, the search, the other parameters.
 */
export function parametersHref(
  pathname: string,
  query: URLSearchParams,
  values: Readonly<Record<string, string | undefined>>,
): string {
  const next = new URLSearchParams(query);
  for (const [name, value] of Object.entries(values)) {
    put(next, name, value);
  }
  next.delete(OFFSET);
  return address(pathname, next);
}

/** The value of `states` for states retained, in the order of the portfolio; none for none. */
export function statesValue(states: readonly ProjectState[]): string | undefined {
  const kept = PORTFOLIO_STATES.filter((state) => states.includes(state));
  return kept.length === 0 ? undefined : kept.join(",");
}
