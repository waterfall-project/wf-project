// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the grids, the commands and the form of the natures and the categories of cost share
 * (FBS-3.1.1): the objects as the contract gives them, the types a nature may have, and the natures a
 * category is filtered on or attached to.
 *
 * Neither server nor client: the page and the components of the browser read it alike.
 */
import type { CostObject } from "@/api/actions/reference";
import type { components } from "@/api/generated/schema";

export type { CostObject } from "@/api/actions/reference";

/** A nature of cost, as the contract gives it. */
export type CostType = components["schemas"]["CostType"];

/** A category of cost, as the contract gives it. */
export type CostCategory = components["schemas"]["CostCategory"];

/** The type of a nature of cost, as the contract names it. */
export type CostTypeKind = components["schemas"]["CostTypeKind"];

/**
 * Every type of nature of the contract, in the order of its enumeration: one the contract adds
 * fails the type check until it is here.
 */
const EVERY_KIND: Readonly<Record<CostTypeKind, number>> = { labor: 0, non_labor: 1, provision: 2 };

/** The types a nature may have, in the order of the contract. */
export const COST_TYPE_KIND_VALUES = Object.keys(EVERY_KIND) as readonly CostTypeKind[];

/** Whether a value is one of the types of nature of the contract. */
export function isCostTypeKind(value: string): value is CostTypeKind {
  return Object.hasOwn(EVERY_KIND, value);
}

/**
 * A nature the categories may be filtered on, or attached to — among the active ones alone, a
 * deactivated one being no longer offered to an entry (WF-REF-0010).
 */
export interface NatureChoice {
  readonly id: string;
  readonly code: string;
  readonly label: string;
  readonly active: boolean;
}

/** The identifier of a nature or a category. */
export function idOf(object: CostObject): string {
  return "cost_category_id" in object ? object.cost_category_id : object.cost_type_id;
}
