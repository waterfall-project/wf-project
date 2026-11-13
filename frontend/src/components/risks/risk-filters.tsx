// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the register of the risks (WF-IHM-0130, #1787, #2916), folded into the bar of its
 * grid (`filtering`): the state and the zone of the matrix, by values; the probability and the four
 * columns of amounts — severity, provision, cost at the occurrence, reestimated amount of the
 * occurred risks —, by bounds both included; the date of the last review, by a period, its end
 * included. Each only changes the address, under the names of the contract (`address.ts`), and the
 * page reads the risks anew, which the server filters, the totals with them: the front filters
 * nothing (WF-ARC-0020). A side the server refused (422) is said at its field.
 *
 * And the shortcut of the periodic review (WF-RIS-0020): « Non réexaminés depuis le dernier
 * marquage » ends the period of the last review at the day of the last marking of the project, as the
 * server lists it, so that the register shows the risks whose probability has not been reviewed
 * since; the server filters.
 */
"use client";

import { ClipboardCheck } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { FilterFields } from "@/components/grid/filter-fields";
import { filterHref, refusedBounds, refusedSides } from "@/components/grid/filters";
import { usePendingLink } from "@/components/grid/pending-address";
import { refusedPeriod } from "@/components/grid/period";
import { PeriodFilter } from "@/components/grid/period-filter";
import { OFFSET } from "@/components/grid/query";
import { RangeFilter } from "@/components/grid/range-filter";
import { ValuesFilter } from "@/components/grid/values-filter";
import { buttonVariants } from "@/components/ui/button";

import {
  AMOUNT_COLUMNS,
  type AmountColumn,
  PROBABILITY,
  REVIEW_PERIOD,
  RISK_STATES,
  RISK_ZONES,
  type RiskFilters,
  type RiskState,
  STATES,
  ZONES,
} from "./address";

/** The key of the heading of each column in the catalogue of the columns of the grids. */
const HEADING = {
  probability: "probability",
  severity: "severity",
  provision_amount: "provisionAmount",
  occurrence_cost: "occurrenceCost",
  occurred_reestimated_amount: "occurredReestimatedAmount",
} as const satisfies Readonly<Record<AmountColumn | typeof PROBABILITY, string>>;

/** The shortcut of the periodic review: the register of the risks not reviewed since a day. */
export function UnreviewedSince({ day }: { readonly day: string }) {
  const t = useTranslations("risks.filters");
  const pathname = usePathname();
  const asked = useSearchParams().get(REVIEW_PERIOD.to) === day;
  const { href, onClick } = usePendingLink((query) =>
    filterHref(pathname, query, REVIEW_PERIOD.to, day, OFFSET),
  );
  return (
    <Link
      href={href}
      onClick={onClick}
      scroll={false}
      aria-current={asked ? "true" : undefined}
      className={buttonVariants({ variant: asked ? "default" : "outline", size: "sm" })}
    >
      <ClipboardCheck aria-hidden="true" className="size-4" />
      {t("unreviewed")}
    </Link>
  );
}

/**
 * The panel of the filters of the register: what the address asks, the refusals of the server
 * (`fields` of its 422). The shortcut of the review stands beside the bar (`UnreviewedSince`), within
 * reach with the panel closed.
 */
export function RiskFilterPanel({
  states,
  filters,
  fields,
}: {
  readonly states: readonly RiskState[];
  readonly filters: RiskFilters;
  readonly fields: readonly components["schemas"]["FieldProblem"][];
}) {
  const t = useTranslations();
  const columns = useTranslations("grid.columns");
  const refused = refusedBounds(fields);
  const column = (name: AmountColumn | typeof PROBABILITY) => ({
    column: name,
    label: columns(HEADING[name]),
    bounds: name === PROBABILITY ? filters.probability : filters.amounts[name],
    refused: refusedSides(refused, name),
  });
  return (
    <FilterFields>
      <ValuesFilter
        name={STATES}
        page={OFFSET}
        label={t("risks.filter")}
        every={t("risks.everyState")}
        values={RISK_STATES.map((state) => ({ value: state, text: t(`enums.RiskState.${state}`) }))}
        chosen={states}
      />
      <ValuesFilter
        name={ZONES}
        page={OFFSET}
        label={t("risks.filters.zone")}
        every={t("risks.filters.everyZone")}
        values={RISK_ZONES.map((zone) => ({ value: zone, text: t(`enums.AlertZone.${zone}`) }))}
        chosen={filters.zones}
      />
      <RangeFilter
        label={t("risks.filters.probabilityBounds")}
        kind="decimal"
        columns={[column(PROBABILITY)]}
        page={OFFSET}
      />
      <RangeFilter
        label={t("risks.filters.amountBounds")}
        kind="money"
        columns={AMOUNT_COLUMNS.map(column)}
        page={OFFSET}
      />
      <PeriodFilter
        label={t("risks.filters.review")}
        kind="date"
        period={filters.review}
        names={REVIEW_PERIOD}
        refused={refusedPeriod(fields, REVIEW_PERIOD)}
        page={OFFSET}
      />
    </FilterFields>
  );
}
