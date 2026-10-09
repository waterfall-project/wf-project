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
 * For a session that may modify the cost settings, each row offers its modification in a column of
 * its own, and its state the command that changes it as the object lists it (EP-02/L43a,
 * `cost-commands.tsx`); for another, the state alone, and the reactivation the server lists — none.
 *
 * Neither server nor client: the page reads the keys, the names and the columns sorted; the grids,
 * in the browser, the rest — the functions that read a row never cross to the server.
 */
import { useTranslations } from "next-intl";

import type { operations } from "@/api/generated/schema";
import { type GridColumn, type GridConfig, sortColumns } from "@/components/grid/columns";
import { prefixedAddress } from "@/components/grid/query";

import { CostStateCell, ModifyCostCommand } from "./cost-commands";
import type { CostCategory, CostObject, CostType } from "./cost-kinds";

export {
  COST_TYPE_KIND_VALUES,
  type CostCategory,
  type CostType,
  type CostTypeKind,
} from "./cost-kinds";

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

/** The widths of the column of the state and its command, and of that of the modification. */
const STATE_WIDTH = 190;
const MODIFY_WIDTH = 110;

/**
 * The state of a row and the command that changes it, and, for a session that may modify the cost
 * settings, the column of its modification.
 */
function commandColumns<Row extends CostObject, Sort extends string>(
  editable: boolean,
  stateSort: Sort,
): GridColumn<Row, Sort, null>[] {
  const state: GridColumn<Row, Sort, null> = {
    key: "state",
    label: "state",
    format: "text",
    width: STATE_WIDTH,
    contract: stateSort,
    value: (row) => (row.is_active ? "active" : "inactive"),
    render: (row) => <CostStateCell row={row} />,
  };
  const modify: GridColumn<Row, Sort, null> = {
    key: "modify",
    label: "modify",
    format: "text",
    width: MODIFY_WIDTH,
    value: () => null,
    render: (row) => <ModifyCostCommand row={row} />,
  };
  return editable ? [state, modify] : [state];
}

/** The type of a nature, in words. */
function Kind({ type }: { readonly type: CostType }) {
  const t = useTranslations("enums.CostTypeKind");
  return t(type.kind);
}

/**
 * The natures of cost: each by its code, its name, its type and its state, and its modification for
 * a session that may modify the cost settings.
 */
export function costTypeGrid(editable = false): GridConfig<CostType, CostTypeSort, null> {
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
      ...commandColumns<CostType, CostTypeSort>(editable, "is_active"),
    ],
  };
}

/**
 * The categories of cost: each by its code, its name, its nature — named as the server resolves
 * it —, its accounting code and its state, and its modification for a session that may modify the
 * cost settings.
 */
export function costCategoryGrid(
  editable = false,
): GridConfig<CostCategory, CostCategorySort, null> {
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
      ...commandColumns<CostCategory, CostCategorySort>(editable, "is_active"),
    ],
  };
}

/** The columns of the contract the server sorts the natures and the categories by. */
export const COST_TYPE_SORTS = sortColumns(costTypeGrid());
export const COST_CATEGORY_SORTS = sortColumns(costCategoryGrid());
