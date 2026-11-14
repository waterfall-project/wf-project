// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dense grids of the natures and the categories of cost in their page (FBS-3.1.1, #510), one
 * component that takes its configuration by its kind, as the grids of the settings of the resources
 * do (`ReferenceGrid`): the page hands each data only — the rows of a page of the list, where it
 * stands in the list, what the address asked and the settings the session read, and whether the
 * session may modify the cost settings. No cell is entered: a session that may modify them is offered
 * the modification of each row in a form, and the activation of an object follows the commands it
 * carries (EP-02/L43a); a row the server answered a write of shows the answer (`useAnswered`).
 *
 * The totals row says how many the server retained (`meta.total`), the search and the filters
 * applying to it (WF-IHM-0130), never a count of the page nor a sum.
 */
"use client";

import { useTranslations } from "next-intl";

import type { ListPage } from "@/navigation/pages";

import {
  type CostCategory,
  type CostTypeKind,
  type CostCategorySort,
  costCategoryGrid,
  type CostType,
  type CostTypeSort,
  costTypeGrid,
} from "./cost-grids";
import type { Choice } from "./kinds";
import { useCostCategoryChips, useCostTypeChips } from "./reference-chips";
import { ReferenceGrid, type ReferenceGridProps } from "./resource-grid";

/** What the grid of the natures adds: the types and the state it is filtered on, told as chips. */
interface CostTypeFiltered {
  readonly kinds?: readonly CostTypeKind[] | undefined;
  readonly state?: boolean | undefined;
}

/** What the grid of the categories adds: the nature and the state it is filtered on, told as chips. */
interface CostCategoryFiltered {
  readonly nature?: string | undefined;
  readonly natures?: readonly Choice[] | undefined;
  readonly state?: boolean | undefined;
}

/** The two grids of the natures and the categories of cost, by their kind. */
export type CostGridProps = { readonly page: ListPage } & (
  | ({ readonly kind: "costTypes" } & ReferenceGridProps<CostType, CostTypeSort> & CostTypeFiltered)
  | ({ readonly kind: "costCategories" } & ReferenceGridProps<CostCategory, CostCategorySort> &
      CostCategoryFiltered)
);

/** The grid of the natures, its filters told as chips. */
function CostTypeGrid(props: Extract<CostGridProps, { kind: "costTypes" }>) {
  const t = useTranslations("reference");
  const chips = useCostTypeChips(props.kinds, props.state);
  return (
    <ReferenceGrid
      {...props}
      chips={chips}
      make={costTypeGrid}
      count={(count) => t("costTypes.count", { count })}
    />
  );
}

/** The grid of the categories, its filters told as chips. */
function CostCategoryGrid(props: Extract<CostGridProps, { kind: "costCategories" }>) {
  const t = useTranslations("reference");
  const chips = useCostCategoryChips(props.nature, props.natures, props.state);
  return (
    <ReferenceGrid
      {...props}
      chips={chips}
      make={costCategoryGrid}
      count={(count) => t("costCategories.count", { count })}
    />
  );
}

/** Render a grid of the natures or the categories of cost, by its kind. */
export function CostGrid(props: CostGridProps) {
  return props.kind === "costTypes" ? <CostTypeGrid {...props} /> : <CostCategoryGrid {...props} />;
}
