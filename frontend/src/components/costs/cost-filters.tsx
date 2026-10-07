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

import { Circle, CircleCheck, ListFilter } from "lucide-react";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState } from "react";

import { usePendingAddress } from "@/components/grid/pending-address";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { UNASSIGNED } from "@/navigation/context";

import {
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

/** The filter by scope: a button for each, pressed as the address shows it. */
function ScopeFilter({ scope }: { readonly scope: Scope | undefined }) {
  const t = useTranslations("actualCosts.filters");
  const filter = useFilter();
  const choices: readonly (Scope | undefined)[] = [undefined, ...SCOPES];
  return (
    <div role="group" aria-label={t("scope")} className="flex flex-wrap items-center gap-1.5">
      {choices.map((choice) => {
        const pressed = choice === scope;
        const Icon = choice === undefined ? ListFilter : pressed ? CircleCheck : Circle;
        return (
          <Button
            key={choice ?? "every"}
            size="sm"
            variant={pressed ? "default" : "outline"}
            aria-pressed={pressed}
            onClick={() => {
              filter(() => ({ scope: choice }));
            }}
          >
            <Icon aria-hidden="true" className="size-4" />
            {t(choice ?? "everyLine")}
          </Button>
        );
      })}
    </div>
  );
}

/** The filter by sub-project: every one, none, or one of the project. */
function SubprojectFilter({
  subproject,
  subprojects,
}: Pick<CostFiltersProps, "subproject" | "subprojects">) {
  const t = useTranslations();
  const id = useId();
  const filter = useFilter();
  // A sub-project the address names that the project does not hold stays chosen, under its value
  // as the address writes it — as the banner says it —, rather than the choice showing another.
  const unknown =
    subproject !== undefined &&
    subproject !== UNASSIGNED &&
    !subprojects.some((choice) => choice.id === subproject);
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor={id}>{t("actualCosts.filters.subproject")}</Label>
      <NativeSelect
        id={id}
        value={subproject ?? ""}
        onChange={(event) => {
          const value = event.target.value;
          filter(() => ({ subproject: value === "" ? undefined : value }));
        }}
        className="w-56"
      >
        <option value="">{t("actualCosts.filters.everySubproject")}</option>
        <option value={UNASSIGNED}>{t("enums.SubprojectFilter.unassigned")}</option>
        {subprojects.map((choice) => (
          <option key={choice.id} value={choice.id}>
            {t("actualCosts.filters.subprojectChoice", { code: choice.code, label: choice.label })}
          </option>
        ))}
        {unknown ? (
          <option value={subproject}>{t("actualCosts.filters.unknownSubproject")}</option>
        ) : null}
      </NativeSelect>
    </div>
  );
}

/** The filter by period of the documents: two dates, sent together. */
function PeriodFilter({ from, to }: Pick<CostFilters, "from" | "to">) {
  const t = useTranslations("actualCosts.filters");
  const ids = { from: useId(), to: useId() };
  const [period, setPeriod] = useState({ from: from ?? "", to: to ?? "" });
  const filter = useFilter();
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    filter(() => ({
      from: period.from === "" ? undefined : period.from,
      to: period.to === "" ? undefined : period.to,
    }));
  };
  return (
    <form aria-label={t("period")} onSubmit={submit} className="flex flex-wrap items-center gap-2">
      {(["from", "to"] as const).map((bound) => (
        <div key={bound} className="flex items-center gap-2">
          <Label htmlFor={ids[bound]}>{t(bound)}</Label>
          <Input
            id={ids[bound]}
            type="date"
            value={period[bound]}
            // Each bound keeps the other side of the period: a start after the end is not offered.
            {...(bound === "from"
              ? { max: period.to === "" ? undefined : period.to }
              : { min: period.from === "" ? undefined : period.from })}
            onChange={(event) => {
              setPeriod({ ...period, [bound]: event.target.value });
            }}
            className="h-8 w-40"
          />
        </div>
      ))}
      <Button type="submit" size="sm" variant="outline">
        <ListFilter aria-hidden="true" className="size-4" />
        {t("apply")}
      </Button>
    </form>
  );
}

/** Render the filters of the actual costs, as the address asks them. */
export function CostFilterBar({ filters, subproject, subprojects }: CostFiltersProps) {
  const t = useTranslations("actualCosts.filters");
  return (
    <section aria-label={t("label")} className="flex flex-wrap items-center gap-x-6 gap-y-2">
      <ScopeFilter scope={filters.scope} />
      <SubprojectFilter subproject={subproject} subprojects={subprojects} />
      {/* A period the address changed — back in the history — sets the fields anew. */}
      <PeriodFilter
        key={`${filters.from ?? ""}/${filters.to ?? ""}`}
        from={filters.from}
        to={filters.to}
      />
    </section>
  );
}
