// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configurations of the dense grids of the natures and the categories of cost (FBS-3.1.1,
 * #510), which share the settings of the costs with the grid of the hourly rates. Each has the key
 * of its settings in the account (WF-ADM-0040) and its own names in the address (`prefixedAddress`:
 * `type_`, `category_`), under which its page asks the API by the names of the contract — the grid of
 * the rates keeps those of the contract. Both are flat tables whose every column the server sorts
 * (WF-IHM-0060), searched, filtered and paged by it (WF-IHM-0130):
 *
 * - the natures, by their code, their name, their type and their state (WF-REF-0030), filtered by
 *   type (`kinds`) and by state;
 * - the categories, by their code, their name, their nature — named as the server resolves it,
 *   active or not (WF-REF-0150) —, their accounting code, documentary, and their state
 *   (WF-REF-0040), filtered by nature (`cost_type_id`) and by state; the accounting code has no
 *   filter of its own, the search reading it.
 *
 * Neither server nor client: the page reads the keys, the names and the columns sorted; the grids,
 * in the browser, the rest — the functions that read a row never cross to the server.
 */
import { useTranslations } from "next-intl";

import type { components, operations } from "@/api/generated/schema";
import { type GridConfig, sortColumns } from "@/components/grid/columns";
import { prefixedAddress } from "@/components/grid/query";

import { stateColumn } from "./resource-grids";

/** A nature of cost, as the contract gives it. */
export type CostType = components["schemas"]["CostType"];

/** A category of cost, as the contract gives it. */
export type CostCategory = components["schemas"]["CostCategory"];

/** The type of a nature of cost, as the contract names it. */
export type CostTypeKind = components["schemas"]["CostTypeKind"];

/** The column of the contract the server sorts the natures by. */
export type CostTypeSort = NonNullable<
  NonNullable<operations["listCostTypes"]["parameters"]["query"]>["sort_by"]
>;

/** The column of the contract the server sorts the categories by. */
export type CostCategorySort = NonNullable<
  NonNullable<operations["listCostCategories"]["parameters"]["query"]>["sort_by"]
>;

/** The keys of the settings of the two grids in the account: stable. */
export const COST_TYPE_GRID_KEY = "cost_types";
export const COST_CATEGORY_GRID_KEY = "cost_categories";

/** The names of each grid in the address: those of the contract, after its prefix. */
export const COST_TYPE_ADDRESS = prefixedAddress("type_");
export const COST_CATEGORY_ADDRESS = prefixedAddress("category_");

/** The filters of each grid in the address: those of the contract, after its prefix. */
export const COST_TYPE_KINDS = "type_kinds";
export const COST_TYPE_STATE = "type_is_active";
export const CATEGORY_COST_TYPE = "category_cost_type_id";
export const CATEGORY_STATE = "category_is_active";

/**
 * Every type of nature of the contract, in the order of its enumeration: one the contract adds
 * fails the type check until it is here.
 */
const EVERY_KIND: Readonly<Record<CostTypeKind, number>> = { labor: 0, non_labor: 1, provision: 2 };

/** The types a nature may have, in the order of the contract. */
export const COST_TYPE_KIND_VALUES = Object.keys(EVERY_KIND) as readonly CostTypeKind[];

/** The type of a nature, in words. */
function Kind({ type }: { readonly type: CostType }) {
  const t = useTranslations("enums.CostTypeKind");
  return t(type.kind);
}

/** The natures of cost: each by its code, its name, its type and its state. */
export function costTypeGrid(): GridConfig<CostType, CostTypeSort, null> {
  return {
    key: COST_TYPE_GRID_KEY,
    name: "costTypes",
    address: COST_TYPE_ADDRESS,
    searched: true,
    rowKey: (type) => type.cost_type_id,
    columns: [
      {
        key: "code",
        label: "code",
        format: "text",
        width: 80,
        pinned: true,
        contract: "code",
        value: (type) => type.code,
      },
      {
        key: "label",
        label: "label",
        format: "text",
        width: 180,
        contract: "label",
        value: (type) => type.label,
      },
      {
        key: "kind",
        label: "costTypeKind",
        format: "text",
        width: 140,
        contract: "kind",
        value: (type) => type.kind,
        render: (type) => <Kind type={type} />,
      },
      stateColumn<CostType, CostTypeSort>(
        (type) => ({
          active: type.is_active,
          target: { kind: "cost_type", id: type.cost_type_id, lockVersion: type.lock_version },
          name: type.label,
          commands: type.available_commands,
        }),
        "is_active",
      ),
    ],
  };
}

/**
 * The categories of cost: each by its code, its name, its nature — named as the server resolves
 * it —, its accounting code and its state.
 */
export function costCategoryGrid(): GridConfig<CostCategory, CostCategorySort, null> {
  return {
    key: COST_CATEGORY_GRID_KEY,
    name: "costCategories",
    address: COST_CATEGORY_ADDRESS,
    searched: true,
    rowKey: (category) => category.cost_category_id,
    columns: [
      {
        key: "code",
        label: "code",
        format: "text",
        width: 90,
        pinned: true,
        contract: "code",
        value: (category) => category.code,
      },
      {
        key: "label",
        label: "label",
        format: "text",
        width: 200,
        contract: "label",
        value: (category) => category.label,
      },
      {
        key: "cost_type",
        label: "costType",
        format: "text",
        width: 140,
        contract: "cost_type",
        value: (category) => category.cost_type_label,
      },
      {
        key: "accounting_code",
        label: "accountingCode",
        format: "text",
        width: 120,
        contract: "accounting_code",
        value: (category) => category.accounting_code,
      },
      stateColumn<CostCategory, CostCategorySort>(
        (category) => ({
          active: category.is_active,
          target: {
            kind: "cost_category",
            id: category.cost_category_id,
            lockVersion: category.lock_version,
          },
          name: category.label,
          commands: category.available_commands,
        }),
        "is_active",
      ),
    ],
  };
}

/** The columns of the contract the server sorts the natures and the categories by. */
export const COST_TYPE_SORTS = sortColumns(costTypeGrid());
export const COST_CATEGORY_SORTS = sortColumns(costCategoryGrid());
