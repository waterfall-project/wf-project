// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the register of the risks on each of its columns (WF-IHM-0130, #1787), beside its
 * grid: the zone of the matrix, by values; the probability and the four columns of amounts —
 * severity, provision, cost at the occurrence, reestimated amount of the occurred risks —, by bounds
 * both included; the date of the last review, by a period, its end included. Each only changes the
 * address, under the names of the contract (`address.ts`), and the page reads the risks anew, which
 * the server filters, the totals with them: the front filters nothing (WF-ARC-0020). A side the
 * server refused (422) is said at its field.
 *
 * And the shortcut of the periodic review (WF-RIS-0020): « Non réexaminés depuis le dernier
 * marquage » ends the period of the last review at the day of the last marking of the project, as the
 * server lists it, so that the register shows the risks whose probability has not been reviewed
 * since; the server filters.
 *
 * The bar is folded by default, as the matrix is, so that the grid keeps its totals in a window 768
 * high (WF-IHM-0100, #1252); its command and the shortcut stand in the line of the filter by
 * state, which gains no height. It unfolds of itself while a filter of a column is active in the
 * address or a side is refused, so that the user always sees what filters.
 */
"use client";

import { ChevronDown, ChevronUp, ClipboardCheck } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { type ReactNode, useState } from "react";

import type { components } from "@/api/generated/schema";
import { type Bounds, filterHref, refusedBounds, refusedSides } from "@/components/grid/filters";
import { usePendingLink } from "@/components/grid/pending-address";
import { refusedPeriod } from "@/components/grid/period";
import { PeriodFilter } from "@/components/grid/period-filter";
import { OFFSET } from "@/components/grid/query";
import { RangeFilter } from "@/components/grid/range-filter";
import { ValuesFilter } from "@/components/grid/values-filter";
import { Button, buttonVariants } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

import {
  AMOUNT_COLUMNS,
  type AmountColumn,
  PROBABILITY,
  REVIEW_PERIOD,
  RISK_ZONES,
  type RiskFilters,
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
function UnreviewedSince({ day }: { readonly day: string }) {
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

/** Whether the address filters a column, or the server refused a side of a filter. */
function isFiltering(
  { zones, probability, amounts, review }: RiskFilters,
  fields: readonly components["schemas"]["FieldProblem"][],
): boolean {
  const bounded = (bounds: Bounds) => bounds.min !== undefined || bounds.max !== undefined;
  return (
    fields.length > 0 ||
    zones.length > 0 ||
    bounded(probability) ||
    AMOUNT_COLUMNS.some((name) => bounded(amounts[name])) ||
    review.from !== undefined ||
    review.to !== undefined
  );
}

/** The filters themselves, once the bar is unfolded. */
function Bar({
  filters,
  fields,
}: {
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
    <div className="flex flex-wrap items-start gap-x-6 gap-y-2">
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
    </div>
  );
}

/**
 * Render the filters of the register on its columns: what the address asks, the refusals of the
 * server (`fields` of its 422) and, for the shortcut of the review, the day of the last marking of
 * the project — none while it has marked no revision, the shortcut then not offered. The command of
 * the bar, the shortcut and the `children` (the filter by state) make one group that lays out in
 * the line of its parent; the bar opens under that line.
 */
export function RiskColumnFilters({
  filters,
  fields,
  lastMarkedOn,
  children,
}: {
  readonly filters: RiskFilters;
  readonly fields: readonly components["schemas"]["FieldProblem"][];
  readonly lastMarkedOn: string | undefined;
  readonly children?: ReactNode;
}) {
  const t = useTranslations("risks.filters");
  const filtering = isFiltering(filters, fields);
  // What the user chose holds until the address starts or stops filtering: then the bar follows it.
  const [seen, setSeen] = useState(filtering);
  const [chosen, setChosen] = useState<boolean | undefined>(undefined);
  if (seen !== filtering) {
    setSeen(filtering);
    setChosen(undefined);
  }
  const open = chosen ?? filtering;
  return (
    <Collapsible open={open} onOpenChange={setChosen} className="contents">
      <div className="flex flex-wrap items-end justify-end gap-x-3 gap-y-2">
        {children}
        <CollapsibleTrigger asChild>
          <Button type="button" variant="outline" size="sm">
            {open ? <ChevronUp aria-hidden="true" /> : <ChevronDown aria-hidden="true" />}
            {t("toggle")}
          </Button>
        </CollapsibleTrigger>
        {lastMarkedOn === undefined ? null : <UnreviewedSince day={lastMarkedOn} />}
      </div>
      <CollapsibleContent className="w-full basis-full">
        <Bar filters={filters} fields={fields} />
      </CollapsibleContent>
    </Collapsible>
  );
}
