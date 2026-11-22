// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the list of the projects of the portfolio, folded into the bar of its grid
 * (`filtering`, WF-IHM-0130-A): the zone of the indices, by values; the code, a text the code
 * contains; the bounds of the four columns of amounts, of the win probability and of the value of
 * the two indices, both included; the period of the last marking, local days. Each only changes the
 * address, under the names of the contract (`address.ts`), back to the first page, and the page
 * reads the projects anew, which the server filters, the totals with them: the front filters
 * nothing (WF-ARC-0020). A side the server refused (422) is said at its field.
 */
"use client";

import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { FilterFields } from "@/components/grid/filter-fields";
import { refusedBounds, refusedSides } from "@/components/grid/filters";
import { refusedPeriod } from "@/components/grid/period";
import { PeriodFilter } from "@/components/grid/period-filter";
import { OFFSET } from "@/components/grid/query";
import { RangeFilter } from "@/components/grid/range-filter";
import { TextFilter } from "@/components/grid/text-filter";

import {
  AMOUNT_COLUMNS,
  CODE,
  CODE_LENGTH,
  INDEX_COLUMNS,
  MARKED_PERIOD,
  type ProjectFilters,
  WIN_PROBABILITY,
} from "./address";
import { BOUNDED_HEADING, boundsOf, type BoundedColumn } from "./project-chips";
import { ZoneFilter } from "./zone-filter";

/**
 * The panel of the filters of the list: what the address asks, the refusals of the server (`fields`
 * of its 422).
 */
export function ProjectFilterPanel({
  filters,
  fields,
}: {
  readonly filters: ProjectFilters;
  readonly fields: readonly components["schemas"]["FieldProblem"][];
}) {
  const t = useTranslations("portfolio.projects");
  const columns = useTranslations("grid.columns");
  const refused = refusedBounds(fields);
  const column = (name: BoundedColumn) => ({
    column: name,
    label: columns(BOUNDED_HEADING[name]),
    bounds: boundsOf(filters, name),
    refused: refusedSides(refused, name),
  });
  return (
    <FilterFields hint={false}>
      <ZoneFilter zones={filters.zones} />
      <TextFilter
        name={CODE}
        label={t("codeFilter")}
        value={filters.code}
        length={CODE_LENGTH}
        page={OFFSET}
      />
      <RangeFilter
        label={t("amountBounds")}
        kind="money"
        columns={AMOUNT_COLUMNS.map(column)}
        page={OFFSET}
      />
      <RangeFilter
        label={t("probabilityBounds")}
        kind="decimal"
        columns={[column(WIN_PROBABILITY)]}
        page={OFFSET}
      />
      <RangeFilter
        label={t("indexBounds")}
        kind="decimal"
        columns={INDEX_COLUMNS.map(column)}
        page={OFFSET}
      />
      <PeriodFilter
        label={t("markedPeriod")}
        kind="day"
        period={filters.marked}
        names={MARKED_PERIOD}
        refused={refusedPeriod(fields, MARKED_PERIOD)}
        page={OFFSET}
      />
    </FilterFields>
  );
}
