// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The perimeter of a view of the portfolio, as the user chooses it (WF-PTF-0010): the states it
 * retains — the projects in progress, to which the offers in pricing may be added, and the projects
 * completed —, the period and the date of calculation, the node of organisation whose roles — its
 * own and those of its descendants — the labour lines are restricted to, offered as the tree the
 * server orders —, and the horizon
 * and the threshold of under-load (WF-PTF-0060), for the views that take them. A choice only
 * changes the address, under the names of the contract, and the page reads anew what the server
 * computes on it. A state shows pressed as the address asks it, or, when the address asks none, as
 * the server retained it by default (`scope.states`): the front assumes no default of its own; the
 * last state pressed cannot be released, a perimeter retaining at least one. A change goes on from
 * the address last asked (`usePendingAddress`).
 */
"use client";

import { CalendarRange, Circle, CircleCheck } from "lucide-react";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type SubmitEvent, useId, useOptimistic, useTransition } from "react";

import { ChoiceFilter } from "@/components/grid/choice-filter";
import { useDatedEntry } from "@/components/grid/dated-entry";
import { PendingAddress, usePendingAddress } from "@/components/grid/pending-address";
import { OFFSET } from "@/components/grid/query";
import { ProjectStateBadge } from "@/components/projects/project-state-badge";
import { type NodeChoice, OrgNodeFilter } from "@/components/reference/reference-filters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatPercent } from "@/i18n/format";

import {
  AS_OF,
  FROM,
  HORIZON,
  HORIZONS,
  ORG_NODE,
  type Perimeter,
  PORTFOLIO_STATES,
  type ProjectState,
  parametersHref,
  readStates,
  STATES,
  statesValue,
  type Takes,
  THRESHOLD,
  THRESHOLDS,
  TO,
  WHOLE,
} from "./address";

/** Change parameters of the address last asked, from what it asks. */
function useParameters() {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  return (change: (query: URLSearchParams) => Readonly<Record<string, string | undefined>>) => {
    request((query) => parametersHref(pathname, query, change(query)));
  };
}

/**
 * The filter by state: a button for each state of a portfolio, pressed as retained — or as last
 * asked, until the server answers —, the state by its badge (#523), as the filter of the home shows
 * it.
 */
function StatesFilter({
  asked,
  retained,
}: {
  readonly asked: readonly ProjectState[];
  readonly retained: readonly ProjectState[];
}) {
  const t = useTranslations();
  const change = useParameters();
  // The states asked, pressed until the server answers for them: the buttons would otherwise show
  // the address until the navigation arrives, and again the address should another navigation
  // replace it (défaut n° 21 de `typescript.md`).
  const [last, show] = useOptimistic(asked);
  const [, startTransition] = useTransition();
  const shown = last.length === 0 ? retained : last;
  return (
    <div
      role="group"
      aria-label={t("portfolio.perimeter.states")}
      className="flex flex-wrap items-center gap-1.5"
    >
      {PORTFOLIO_STATES.map((state) => {
        const pressed = shown.includes(state);
        // The last state retained stays: releasing it would leave a perimeter of nothing.
        const kept = pressed && shown.length === 1;
        const Icon = pressed ? CircleCheck : Circle;
        return (
          <Button
            key={state}
            size="sm"
            variant={pressed ? "default" : "outline"}
            aria-pressed={pressed}
            aria-disabled={kept ? true : undefined}
            onClick={() => {
              if (kept) {
                return;
              }
              startTransition(() => {
                change((query) => {
                  const before = readStates(query);
                  const from = before.length === 0 ? retained : before;
                  const next = from.includes(state)
                    ? from.filter((each) => each !== state)
                    : [...from, state];
                  show(next);
                  return { [STATES]: statesValue(next) };
                });
              });
            }}
          >
            <Icon aria-hidden="true" className="size-4" />
            <ProjectStateBadge state={state} />
          </Button>
        );
      })}
    </div>
  );
}

/** The dates a view takes: the bounds of its period, if it has one, and the date of calculation. */
const DATES = { period: ["from", "to", "asOf"], date: ["asOf"] } as const;

/**
 * The bounds of the period, if the view takes one, and the date of calculation, sent together. An
 * entry is dated by the dates of the address (`useDatedEntry`): dates the address changes — back in
 * the history — show anew, and the form keeps the focus.
 */
function DatesForm({
  perimeter,
  fields,
}: {
  readonly perimeter: Perimeter;
  readonly fields: (typeof DATES)[keyof typeof DATES];
}) {
  const t = useTranslations("portfolio.perimeter");
  const ids = { from: useId(), to: useId(), asOf: useId() };
  const { entered, enter, sent } = useDatedEntry<"from" | "to" | "asOf">(
    `${perimeter.from ?? ""}/${perimeter.to ?? ""}/${perimeter.asOf ?? ""}`,
  );
  const dates = {
    from: entered.from ?? perimeter.from ?? "",
    to: entered.to ?? perimeter.to ?? "",
    asOf: entered.asOf ?? perimeter.asOf ?? "",
  };
  const change = useParameters();
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    // Sent, the dates arrive as the address writes them: only what is typed after them stays.
    sent();
    change(() => ({
      [AS_OF]: dates.asOf,
      ...(fields.length === 1 ? {} : { [FROM]: dates.from, [TO]: dates.to }),
    }));
  };
  return (
    <form aria-label={t("period")} onSubmit={submit} className="flex flex-wrap items-center gap-2">
      {fields.map((field) => (
        <div key={field} className="flex items-center gap-2">
          <Label htmlFor={ids[field]}>{t(field)}</Label>
          <Input
            id={ids[field]}
            type="date"
            value={dates[field]}
            // A period is never asked backwards: its start no later than its end (WF-PTF-0010).
            max={field === "from" && dates.to !== "" ? dates.to : undefined}
            min={field === "to" && dates.from !== "" ? dates.from : undefined}
            onChange={(event) => {
              enter(field, event.target.value);
            }}
            className="h-8 w-40"
          />
        </div>
      ))}
      <Button type="submit" size="sm" variant="outline">
        <CalendarRange aria-hidden="true" className="size-4" />
        {t("apply")}
      </Button>
    </form>
  );
}

/**
 * The values a parameter of a view proposes, and the one chosen when it is none of them: a value
 * the address asks, or the one the server retained, shows chosen under its own name.
 */
function withChosen(proposed: readonly string[], chosen: string | undefined): readonly string[] {
  return chosen === undefined || proposed.includes(chosen) ? proposed : [...proposed, chosen];
}

/** A node of organisation the labour may be restricted to, with its depth in the tree. */
export type { NodeChoice };

/**
 * The parameters of a view: its horizon, its threshold — as the address asks them, or, for the
 * threshold the address does not name, as the server retained it —; a key absent, not offered.
 */
export interface ViewParameters {
  readonly horizon?: string | undefined;
  readonly threshold?: string | undefined;
}

/**
 * What the perimeter shows: what the address asks, what the server retained, what the view takes.
 */
export interface PerimeterBarProps {
  readonly perimeter: Perimeter;
  readonly retained: readonly ProjectState[];
  /** What of the perimeter the view takes besides its states and its date: a period, a node. */
  readonly takes?: Takes;
  /** The nodes of organisation, when the view takes one. */
  readonly nodes?: readonly NodeChoice[];
  /** The parameters the view takes, and their value; none, and none is offered. */
  readonly view?: ViewParameters;
}

/** Render the perimeter of a view of the portfolio, as the address asks it. */
export function PerimeterBar({
  perimeter,
  retained,
  takes = WHOLE,
  nodes = [],
  view,
}: PerimeterBarProps) {
  const t = useTranslations("portfolio.perimeter");
  const locale = useLocale();
  // The parameters share the address last asked with the screen, or among themselves: what is
  // typed while dates sent are on their way survives their arrival, a state chosen meanwhile too.
  return (
    <PendingAddress>
      <section aria-label={t("label")} className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <StatesFilter asked={perimeter.states} retained={retained} />
        <DatesForm perimeter={perimeter} fields={takes.period ? DATES.period : DATES.date} />
        {/* No node to choose — none in the reference, none the API lets one read —: none offered,
          unless the address already filters on one, which stays shown to be cleared. */}
        {takes.node && (nodes.length > 0 || perimeter.orgNode !== undefined) ? (
          <OrgNodeFilter
            name={ORG_NODE}
            label={t("orgNode")}
            every={t("everyNode")}
            nodes={nodes}
            chosen={perimeter.orgNode}
            page={OFFSET}
          />
        ) : null}
        {view !== undefined && "horizon" in view ? (
          <ChoiceFilter
            name={HORIZON}
            label={t("horizon")}
            every={t("byDefault")}
            choices={withChosen(HORIZONS, view.horizon).map((months) => ({
              value: months,
              text: t("months", { months }),
            }))}
            chosen={view.horizon}
            page={OFFSET}
          />
        ) : null}
        {view !== undefined && "threshold" in view ? (
          <ChoiceFilter
            name={THRESHOLD}
            label={t("threshold")}
            every={t("byDefault")}
            choices={withChosen(THRESHOLDS, view.threshold).map((value) => ({
              value,
              text: formatPercent(value, locale),
            }))}
            chosen={view.threshold}
            page={OFFSET}
          />
        ) : null}
      </section>
    </PendingAddress>
  );
}
