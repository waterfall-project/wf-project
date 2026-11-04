// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the risks reads of its address, besides the sort and the search of its grid
 * (`query.ts`): the states it filters on, under the name and in the form of the contract —
 * `states` and `zones`, their values separated by commas (`explode: false`, `filters.ts`) —, the
 * bounds of each column of figures, `<column>_min` and `<column>_max`, and the period of the last
 * review, `last_review_on_from` and `last_review_on_to` (WF-IHM-0130), which the server filters by;
 * and the risk whose detail it shows, `risk`. A header clicked, a state chosen, a risk
 * opened only change the address, and the page reads anew: the front filters nothing (WF-ARC-0020).
 *
 * Pure, and neither server nor client: the page reads, the screen writes.
 */
import type { components, operations } from "@/api/generated/schema";
import { type Bounds, boundNames, readBounds } from "@/components/grid/filters";
import { type Period, type PeriodNames, readPeriod } from "@/components/grid/period";
import { CONTRACT_ADDRESS, pagedList } from "@/components/grid/query";
import type { SearchParameters } from "@/navigation/context";
import type { PagedList } from "@/navigation/pages";

/** The state of a risk, as the contract names it. */
export type RiskState = components["schemas"]["RiskState"];

/** The parameter of the address the states filtered on go by, as the contract names it. */
export const STATES = "states";

/** The parameter of the address the zones of the matrix filtered on go by, as the contract names it. */
export const ZONES = "zones";

/** The column of the probability, which `probability_min` and `probability_max` bound. */
export const PROBABILITY = "probability";

/**
 * The columns of amounts the register bounds, as the contract names them: their bounds are
 * `<column>_min` and `<column>_max` (`boundNames`). A risk that is not occurred bears neither a cost
 * at the occurrence nor a reestimated amount, and no bound of these two retains it.
 */
export const AMOUNT_COLUMNS = [
  "severity",
  "provision_amount",
  "occurrence_cost",
  "occurred_reestimated_amount",
] as const;

/** A column of amounts of the register. */
export type AmountColumn = (typeof AMOUNT_COLUMNS)[number];

/** The parameters of the period of the last review, as the contract names them. */
export const REVIEW_PERIOD: PeriodNames = { from: "last_review_on_from", to: "last_review_on_to" };

/**
 * The list of the risks: its search, its sort, its page and the size of its pages, and the filters
 * it reads (`readingOf` tells two addresses that read it alike).
 */
export const RISKS_LIST: PagedList = pagedList(
  CONTRACT_ADDRESS,
  STATES,
  ZONES,
  ...[PROBABILITY, ...AMOUNT_COLUMNS].flatMap((column) => {
    const { min, max } = boundNames(column);
    return [min, max];
  }),
  REVIEW_PERIOD.from,
  REVIEW_PERIOD.to,
);

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

/** The zone of a cell of the matrix, as the contract names it. */
export type RiskZone = components["schemas"]["AlertZone"];

const EVERY_ZONE: Readonly<Record<RiskZone, number>> = { nominal: 0, watch: 1, alert: 2 };

/** The zones of the matrix, in the order of the contract. */
export const RISK_ZONES = Object.keys(EVERY_ZONE) as readonly RiskZone[];

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

/** What the register is filtered on besides its states, as the address asks it. */
export interface RiskFilters {
  readonly zones: readonly RiskZone[];
  /** The bounds of the probability, a rate of the contract written as a decimal. */
  readonly probability: Bounds;
  /** The bounds of each column of amounts. */
  readonly amounts: Readonly<Record<AmountColumn, Bounds>>;
  /** The period of the last review, both days included. */
  readonly review: Period;
}

/** The filters of the register the address names; a value the contract would refuse is not asked. */
export function readRiskFilters(search: SearchParameters, zones: readonly RiskZone[]): RiskFilters {
  return {
    zones,
    probability: readBounds(search, PROBABILITY, "decimal"),
    amounts: {
      severity: readBounds(search, "severity", "money"),
      provision_amount: readBounds(search, "provision_amount", "money"),
      occurrence_cost: readBounds(search, "occurrence_cost", "money"),
      occurred_reestimated_amount: readBounds(search, "occurred_reestimated_amount", "money"),
    },
    review: readPeriod(search, "date", REVIEW_PERIOD),
  };
}

/** The filters of the query of `listRisks`. */
type FilterQuery = Pick<
  NonNullable<operations["listRisks"]["parameters"]["query"]>,
  | "zones"
  | "probability_min"
  | "probability_max"
  | "severity_min"
  | "severity_max"
  | "provision_amount_min"
  | "provision_amount_max"
  | "occurrence_cost_min"
  | "occurrence_cost_max"
  | "occurred_reestimated_amount_min"
  | "occurred_reestimated_amount_max"
  | "last_review_on_from"
  | "last_review_on_to"
>;

/** The filters of the register, as the query of `listRisks` takes them: the sides asked alone. */
export function riskFilterQuery({ zones, probability, amounts, review }: RiskFilters): FilterQuery {
  const { severity, provision_amount, occurrence_cost, occurred_reestimated_amount } = amounts;
  return {
    ...(zones.length === 0 ? {} : { zones: [...zones] }),
    ...(probability.min === undefined ? {} : { probability_min: probability.min }),
    ...(probability.max === undefined ? {} : { probability_max: probability.max }),
    ...(severity.min === undefined ? {} : { severity_min: severity.min }),
    ...(severity.max === undefined ? {} : { severity_max: severity.max }),
    ...(provision_amount.min === undefined ? {} : { provision_amount_min: provision_amount.min }),
    ...(provision_amount.max === undefined ? {} : { provision_amount_max: provision_amount.max }),
    ...(occurrence_cost.min === undefined ? {} : { occurrence_cost_min: occurrence_cost.min }),
    ...(occurrence_cost.max === undefined ? {} : { occurrence_cost_max: occurrence_cost.max }),
    ...(occurred_reestimated_amount.min === undefined
      ? {}
      : { occurred_reestimated_amount_min: occurred_reestimated_amount.min }),
    ...(occurred_reestimated_amount.max === undefined
      ? {}
      : { occurred_reestimated_amount_max: occurred_reestimated_amount.max }),
    ...(review.from === undefined ? {} : { last_review_on_from: review.from }),
    ...(review.to === undefined ? {} : { last_review_on_to: review.to }),
  };
}
