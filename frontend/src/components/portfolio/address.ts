// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the portfolio read of their address (WF-PTF-0010): the perimeter every view
 * is computed on, under the names of the contract — the states retained, `states`, its values
 * separated by commas (`explode: false`); the period of the projects completed and of the
 * statistics of a period, `from` and `to`; the date of calculation, `as_of`; the node of
 * organisation whose roles the labour lines are restricted to, `org_node_id` — and the parameters
 * of a view: its horizon, `horizon_months`, and the threshold of under-load the user chooses,
 * `under_load_threshold` (WF-PTF-0060), which the workload keeps with its node from one consultation
 * to the next (`kept-workload-address.ts`) —; and, for the list of the projects alone, the zones of
 * their indices it retains, `zones` (WF-PTF-0040, WF-IHM-0130). A choice only changes the address,
 * and the page reads anew: the server computes, sorts and filters, the front nothing (WF-ARC-0020).
 *
 * Pure, and neither server nor client: the page reads, the screen writes.
 */
import type { components, operations } from "@/api/generated/schema";
import { type Bounds, boundNames, readBounds, readValues } from "@/components/grid/filters";
import { type Period, type PeriodNames, readPeriod } from "@/components/grid/period";
import {
  CONTRACT_ADDRESS,
  type GridQuery,
  limited,
  OFFSET,
  pagedList,
} from "@/components/grid/query";
import { identifierOf, textOf } from "@/components/reference/address";
import { isPlanningDate } from "@/i18n/format";
import type { SearchParameters } from "@/navigation/context";
import type { ProjectState } from "@/navigation/home";
import type { PagedList } from "@/navigation/pages";

/** The state of a project, as the contract names it: the one declaration of the home. */
export type { ProjectState };

/** The zone of an index, as the contract names it. */
export type AlertZone = components["schemas"]["AlertZone"];

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
export const ZONES = "zones";

/**
 * The zones the list of the projects is filtered on, in the order of the contract: a project is
 * retained when its cost index or its schedule index is in one of them — the projects in alert
 * first (WF-PTF-0040).
 */
export const INDEX_ZONES: readonly AlertZone[] = ["nominal", "watch", "alert"];

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

/** The column of the code, which the text of `code` is searched in. */
export const CODE = "code";

/** The longest code text the contract takes. */
export const CODE_LENGTH = 50;

/**
 * The columns of amounts the list bounds, as the contract names them: their bounds are
 * `<column>_min` and `<column>_max` (`boundNames`), both included. A project whose column is null —
 * an offer has no reference budget — is retained by no bound of it.
 */
export const AMOUNT_COLUMNS = [
  "reference_budget",
  "current_estimate",
  "project_manager_projection",
  "delta_to_reference",
] as const;

/** A column of amounts of the list. */
export type AmountColumn = (typeof AMOUNT_COLUMNS)[number];

/** The column of the win probability, a share (`0.4` for 40 %), bounded as the contract says. */
export const WIN_PROBABILITY = "win_probability";

/** The columns of the value of an index the list bounds. */
export const INDEX_COLUMNS = ["cost_index", "schedule_index"] as const;

/** A column of the value of an index of the list. */
export type IndexColumn = (typeof INDEX_COLUMNS)[number];

/** The parameters of the period of the last marking, as the contract names them. */
export const MARKED_PERIOD: PeriodNames = {
  from: "last_marked_at_from",
  to: "last_marked_at_to",
};

/**
 * The list of the projects: its sort, its search, its perimeter and its filters — the zones, the
 * code, the bounds of the columns of figures and the period of the last marking.
 */
export const PROJECTS_LIST: PagedList = pagedList(
  CONTRACT_ADDRESS,
  STATES,
  FROM,
  TO,
  AS_OF,
  ORG_NODE,
  ZONES,
  CODE,
  ...[...AMOUNT_COLUMNS, WIN_PROBABILITY, ...INDEX_COLUMNS].flatMap((column) => {
    const { min, max } = boundNames(column);
    return [min, max];
  }),
  MARKED_PERIOD.from,
  MARKED_PERIOD.to,
);

/** The perimeter the address asks; what it does not name, the server chooses. */
export interface Perimeter {
  readonly states: readonly ProjectState[];
  readonly from: string | undefined;
  readonly to: string | undefined;
  readonly asOf: string | undefined;
  readonly orgNode: string | undefined;
}

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
  return readValues(search, STATES, PORTFOLIO_STATES);
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

/**
 * The zones the address retains, in the order of the contract, each once; none when it names
 * none — the list is not filtered on the zones. A value that is no zone is not asked.
 */
export function readZones(search: SearchParameters): readonly AlertZone[] {
  return readValues(search, ZONES, INDEX_ZONES);
}

/** What the list of the projects is filtered on besides its perimeter, as the address asks it. */
export interface ProjectFilters {
  readonly zones: readonly AlertZone[];
  /** The text the code contains; none, no filter. */
  readonly code: string | undefined;
  /** The bounds of each column of amounts, as the contract writes a `Money`. */
  readonly amounts: Readonly<Record<AmountColumn, Bounds>>;
  /** The bounds of the win probability, a share written as a decimal. */
  readonly winProbability: Bounds;
  /** The bounds of the value of each index, written as a decimal. */
  readonly indices: Readonly<Record<IndexColumn, Bounds>>;
  /** The period of the last marking: local days drawn as instants, the end excluded. */
  readonly marked: Period;
}

/** The filters of the list the address names; a value the contract would refuse is not asked. */
export function readProjectFilters(search: SearchParameters): ProjectFilters {
  return {
    zones: readZones(search),
    code: textOf(search, CODE, CODE_LENGTH),
    amounts: {
      reference_budget: readBounds(search, "reference_budget", "money"),
      current_estimate: readBounds(search, "current_estimate", "money"),
      project_manager_projection: readBounds(search, "project_manager_projection", "money"),
      delta_to_reference: readBounds(search, "delta_to_reference", "money"),
    },
    winProbability: readBounds(search, WIN_PROBABILITY, "decimal"),
    indices: {
      cost_index: readBounds(search, "cost_index", "decimal"),
      schedule_index: readBounds(search, "schedule_index", "decimal"),
    },
    marked: readPeriod(search, "day", MARKED_PERIOD),
  };
}

/** What the list of the projects asks `getPortfolioProjects`: the query of the contract. */
type ProjectsQuery = NonNullable<operations["getPortfolioProjects"]["parameters"]["query"]>;

/** The filters of the query of `getPortfolioProjects`. */
type FilterQuery = Pick<
  ProjectsQuery,
  | "zones"
  | "code"
  | "reference_budget_min"
  | "reference_budget_max"
  | "current_estimate_min"
  | "current_estimate_max"
  | "project_manager_projection_min"
  | "project_manager_projection_max"
  | "delta_to_reference_min"
  | "delta_to_reference_max"
  | "win_probability_min"
  | "win_probability_max"
  | "cost_index_min"
  | "cost_index_max"
  | "schedule_index_min"
  | "schedule_index_max"
  | "last_marked_at_from"
  | "last_marked_at_to"
>;

/** The bounds of the columns of amounts, as the query takes them: the sides asked alone. */
function amountsQuery(amounts: ProjectFilters["amounts"]) {
  return {
    ...(amounts.reference_budget.min === undefined
      ? {}
      : { reference_budget_min: amounts.reference_budget.min }),
    ...(amounts.reference_budget.max === undefined
      ? {}
      : { reference_budget_max: amounts.reference_budget.max }),
    ...(amounts.current_estimate.min === undefined
      ? {}
      : { current_estimate_min: amounts.current_estimate.min }),
    ...(amounts.current_estimate.max === undefined
      ? {}
      : { current_estimate_max: amounts.current_estimate.max }),
    ...(amounts.project_manager_projection.min === undefined
      ? {}
      : { project_manager_projection_min: amounts.project_manager_projection.min }),
    ...(amounts.project_manager_projection.max === undefined
      ? {}
      : { project_manager_projection_max: amounts.project_manager_projection.max }),
    ...(amounts.delta_to_reference.min === undefined
      ? {}
      : { delta_to_reference_min: amounts.delta_to_reference.min }),
    ...(amounts.delta_to_reference.max === undefined
      ? {}
      : { delta_to_reference_max: amounts.delta_to_reference.max }),
  };
}

/** The bounds of the win probability and of the indices, as the query takes them. */
function figuresQuery({ winProbability, indices }: ProjectFilters) {
  return {
    ...(winProbability.min === undefined ? {} : { win_probability_min: winProbability.min }),
    ...(winProbability.max === undefined ? {} : { win_probability_max: winProbability.max }),
    ...(indices.cost_index.min === undefined ? {} : { cost_index_min: indices.cost_index.min }),
    ...(indices.cost_index.max === undefined ? {} : { cost_index_max: indices.cost_index.max }),
    ...(indices.schedule_index.min === undefined
      ? {}
      : { schedule_index_min: indices.schedule_index.min }),
    ...(indices.schedule_index.max === undefined
      ? {}
      : { schedule_index_max: indices.schedule_index.max }),
  };
}

/** The filters of the list, as the query of `getPortfolioProjects` takes them: the sides asked alone. */
export function projectFilterQuery(filters: ProjectFilters): FilterQuery {
  const { zones, code, marked } = filters;
  return {
    ...(zones.length === 0 ? {} : { zones: [...zones] }),
    ...(code === undefined ? {} : { code }),
    ...amountsQuery(filters.amounts),
    ...figuresQuery(filters),
    ...(marked.from === undefined ? {} : { last_marked_at_from: marked.from }),
    ...(marked.to === undefined ? {} : { last_marked_at_to: marked.to }),
  };
}

/**
 * The query of the list of the projects of the portfolio, as the address asks it: its perimeter,
 * its filters, its page, its search and its sort — every parameter but the page read from
 * `PROJECTS_LIST`, which says when two addresses read the same list.
 */
export function portfolioProjectsQuery<Sort extends NonNullable<ProjectsQuery["sort_by"]>>(asked: {
  readonly perimeter: Perimeter;
  readonly filters: ProjectFilters;
  readonly offset: number;
  readonly query: GridQuery<Sort>;
}): ProjectsQuery {
  const { filters, offset, query } = asked;
  return {
    ...perimeterQuery(asked.perimeter),
    ...projectFilterQuery(filters),
    ...(offset === 0 ? {} : { offset }),
    ...(query.search === undefined ? {} : { search: query.search }),
    ...limited(query),
    ...(query.sort === undefined
      ? {}
      : { sort_by: query.sort.column, sort_order: query.sort.order }),
  };
}
