// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reference data the grid of the estimate names its categories and roles by, for the unit
 * tests: read from the examples of the contract the fake back serves — the categories of the
 * volumes (`listCostCategories`), the roles of the witness project (`listResourceRoles`) —, as
 * the page of the estimate hands them to its grid.
 */
import type { components } from "@/api/generated/schema";
import type { EstimateReference } from "@/components/grid/estimate";

import { example } from "./fixtures";

type CostCategory = components["schemas"]["CostCategory"];
type ResourceRole = components["schemas"]["ResourceRole"];

/** The categories and the roles of the examples, as the page hands them to the grid. */
export function estimateReference(): EstimateReference {
  const categories = example("volume/cost_categories") as CostCategory[];
  const roles = example("resource_roles") as ResourceRole[];
  return {
    categories: categories.map((category) => ({
      id: category.cost_category_id,
      label: category.label,
    })),
    roles: roles.map((role) => ({ id: role.resource_role_id, label: role.label })),
  };
}
