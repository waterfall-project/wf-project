// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the actual costs (WF-CRE-0040): by scope — every line, those tracked, those
 * excluded —, by sub-project — every one, those charged to the project alone, or one sub-project —,
 * and by the period of the documents. A filter chosen only changes the address, under the names of
 * the contract (`in_tracked_scope`, `subproject_id`, `from`, `to`), back to the first page; the
 * page reads anew the lines the server retains, with the totals of those (WF-IHM-0130). The front
 * filters nothing. A change goes on from the address last asked (`usePendingAddress`): a filter
 * chosen right after a sort keeps it.
 */
"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useOptimistic, useTransition } from "react";

import { CheckMenu } from "@/components/grid/check-menu";
import { ChoiceFilter } from "@/components/grid/choice-filter";
import { FilterFields } from "@/components/grid/filter-fields";
import { usePendingAddress } from "@/components/grid/pending-address";
import type { PeriodRefusals } from "@/components/grid/period";
import { PeriodFilter } from "@/components/grid/period-filter";
import { UNASSIGNED } from "@/navigation/context";

import {
  COSTS_PAGE,
  type CostFilters,
  filtersHref,
  readCostFilters,
  type Scope,
  SCOPES,
  SUBPROJECT,
} from "./address";

/** A sub-project to filter on: its identifier, its code and its label. */
export interface SubprojectChoice {
  readonly id: string;
  readonly code: string;
  readonly label: string;
}

/** What the filters show: those the address asks, and the sub-projects of the project. */
export interface CostFiltersProps {
  readonly filters: CostFilters;
  readonly subproject: string | undefined;
  readonly subprojects: readonly SubprojectChoice[];
  /** The sides of the period the API refused (422); none when it read the lines. */
  readonly refused?: PeriodRefusals | undefined;
}

/** The filters of the list and its sub-project, as an address asks them. */
type AskedFilters = CostFilters & { readonly subproject: string | undefined };

/** Filter on what a change makes of the filters last asked. */
function useFilter() {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  return (change: (asked: AskedFilters) => Partial<AskedFilters>) => {
    request((query) => {
      const asked = { ...readCostFilters(query), subproject: query.get(SUBPROJECT) ?? undefined };
      return filtersHref(pathname, query, { ...asked, ...change(asked) });
    });
  };
}

/**
 * The filter by scope, a menu of one choice: every line, the tracked ones, the excluded ones — as
 * last asked until the server answers, then as the address shows it.
 */
function ScopeFilter({ scope }: { readonly scope: Scope | undefined }) {
  const t = useTranslations("actualCosts.filters");
  const filter = useFilter();
  // The scope asked, shown until the server answers for it: the menu would otherwise show the
  // address until the navigation arrives, and again the address should another navigation replace
  // it (défaut n° 21 de `typescript.md`).
  const [shown, show] = useOptimistic(scope);
  const [, startTransition] = useTransition();
  return (
    <CheckMenu
      label={t("scope")}
      every={t("everyLine")}
      multiple={false}
      options={SCOPES.map((choice) => ({ value: choice, text: t(choice) }))}
      chosen={shown === undefined ? [] : [shown]}
      onChange={([value]) => {
        const choice = SCOPES.find((each) => each === value);
        startTransition(() => {
          show(choice);
          filter(() => ({ scope: choice }));
        });
      }}
    />
  );
}

/**
 * The filter by sub-project: every one, none, or one of the project. One the address names that the
 * project does not hold stays chosen, as the banner says it, rather than the choice showing another.
 */
function SubprojectFilter({
  subproject,
  subprojects,
}: Pick<CostFiltersProps, "subproject" | "subprojects">) {
  const t = useTranslations();
  return (
    <ChoiceFilter
      name={SUBPROJECT}
      label={t("actualCosts.filters.subproject")}
      every={t("actualCosts.filters.everySubproject")}
      choices={[
        { value: UNASSIGNED, text: t("enums.SubprojectFilter.unassigned") },
        ...subprojects.map((choice) => ({
          value: choice.id,
          text: t("actualCosts.filters.subprojectChoice", {
            code: choice.code,
            label: choice.label,
          }),
        })),
      ]}
      chosen={subproject}
      unknown={t("actualCosts.filters.unknownSubproject")}
      page={COSTS_PAGE}
    />
  );
}

/**
 * Render the filters of the actual costs, as the address asks them, in the panel of the bar of
 * their grid (#2916); the period of the documents two days of planning, both included
 * (`PeriodFilter`, `date`), an end the API refuses for preceding the start said at its field, the
 * start named.
 */
export function CostFilterPanel({ filters, subproject, subprojects, refused }: CostFiltersProps) {
  const t = useTranslations("actualCosts.filters");
  return (
    <FilterFields>
      <ScopeFilter scope={filters.scope} />
      <SubprojectFilter subproject={subproject} subprojects={subprojects} />
      <PeriodFilter
        label={t("period")}
        kind="date"
        period={{ from: filters.from, to: filters.to }}
        refused={refused}
        texts={{ from: t("from"), to: t("to") }}
        page={COSTS_PAGE}
      />
    </FilterFields>
  );
}
