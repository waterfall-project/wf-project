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
import { useCallback } from "react";

import type { GridConfig } from "@/components/grid/columns";
import type { ListPage } from "@/navigation/pages";

import {
  type CostCategory,
  type CostCategorySort,
  costCategoryGrid,
  type CostType,
  type CostTypeSort,
  costTypeGrid,
} from "./cost-grids";
import { useAnswered } from "./cost-commands";
import type { CostObject } from "./cost-kinds";
import { ReferenceGrid, type ReferenceGridProps } from "./resource-grid";

/** The two grids of the natures and the categories of cost, by their kind. */
export type CostGridProps = {
  readonly page: ListPage;
  /** Whether the session may modify the cost settings (`platformOffer`). */
  readonly editable: boolean;
} & (
  | ({ readonly kind: "costTypes" } & ReferenceGridProps<CostType, CostTypeSort>)
  | ({ readonly kind: "costCategories" } & ReferenceGridProps<CostCategory, CostCategorySort>)
);

/**
 * A grid of its configuration for the session, its rows as the server last answered them, its totals
 * row the number the server retained.
 */
function AnsweredGrid<Row extends CostObject, Sort extends string>({
  make,
  count,
  editable,
  rows,
  ...props
}: ReferenceGridProps<Row, Sort> & {
  readonly page: ListPage;
  readonly editable: boolean;
  readonly make: (editable: boolean) => GridConfig<Row, Sort, null>;
  readonly count: (rows: number) => string;
}) {
  const configured = useCallback(() => make(editable), [make, editable]);
  const answered = useAnswered(rows);
  return <ReferenceGrid {...props} rows={answered} make={configured} count={count} />;
}

/** Render a grid of the natures or the categories of cost, by its kind. */
export function CostGrid(props: CostGridProps) {
  const t = useTranslations("reference");
  return props.kind === "costTypes" ? (
    <AnsweredGrid
      {...props}
      make={costTypeGrid}
      count={(count) => t("costTypes.count", { count })}
    />
  ) : (
    <AnsweredGrid
      {...props}
      make={costCategoryGrid}
      count={(count) => t("costCategories.count", { count })}
    />
  );
}
