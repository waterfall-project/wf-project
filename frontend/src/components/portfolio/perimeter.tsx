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
import { type SubmitEvent, useId, useState } from "react";

import { usePendingAddress } from "@/components/grid/pending-address";
import { ProjectStateBadge } from "@/components/projects/project-state-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { treeLabel } from "@/components/reference/org-tree";
import { NativeSelect } from "@/components/ui/native-select";
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
 * The filter by state: a button for each state of a portfolio, pressed as retained, the state by
 * its badge (#523), as the filter of the home shows it.
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
  const shown = asked.length === 0 ? retained : asked;
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
              change((query) => {
                const last = readStates(query);
                const from = last.length === 0 ? retained : last;
                const next = from.includes(state)
                  ? from.filter((each) => each !== state)
                  : [...from, state];
                return { [STATES]: statesValue(next) };
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

/** The bounds of the period, if the view takes one, and the date of calculation, sent together. */
function DatesForm({
  perimeter,
  fields,
}: {
  readonly perimeter: Perimeter;
  readonly fields: (typeof DATES)[keyof typeof DATES];
}) {
  const t = useTranslations("portfolio.perimeter");
  const ids = { from: useId(), to: useId(), asOf: useId() };
  const [dates, setDates] = useState({
    from: perimeter.from ?? "",
    to: perimeter.to ?? "",
    asOf: perimeter.asOf ?? "",
  });
  const change = useParameters();
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
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
              setDates({ ...dates, [field]: event.target.value });
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

/** A choice of a select: the value the address writes, and its name. */
interface Choice {
  readonly value: string;
  readonly label: string;
}

/** A parameter of a view chosen among the values offered, or left to the server (`none`). */
function ViewChoice({
  name,
  label,
  none,
  value,
  offered,
  write,
}: {
  readonly name: string;
  readonly label: string;
  readonly none: string;
  readonly value: string | undefined;
  readonly offered: readonly Choice[];
  readonly write: (value: string | undefined) => void;
}) {
  const id = useId();
  // A value the address names that is not offered stays chosen, under its value as written.
  const unknown = value !== undefined && !offered.some((each) => each.value === value);
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor={id}>{label}</Label>
      <NativeSelect
        id={id}
        name={name}
        value={value ?? ""}
        onChange={(event) => {
          write(event.target.value === "" ? undefined : event.target.value);
        }}
        className="w-56"
      >
        <option value="">{none}</option>
        {offered.map((each) => (
          <option key={each.value} value={each.value}>
            {each.label}
          </option>
        ))}
        {unknown ? <option value={value}>{value}</option> : null}
      </NativeSelect>
    </div>
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
export interface NodeChoice {
  readonly id: string;
  readonly code: string;
  readonly label: string;
  readonly level: number;
}

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
  const named = useTranslations("reference.orgNodes");
  const locale = useLocale();
  const change = useParameters();
  return (
    <section aria-label={t("label")} className="flex flex-wrap items-center gap-x-6 gap-y-2">
      <StatesFilter asked={perimeter.states} retained={retained} />
      {/* Dates the address changed — back in the history — set the fields anew. */}
      <DatesForm
        key={`${perimeter.from ?? ""}/${perimeter.to ?? ""}/${perimeter.asOf ?? ""}`}
        perimeter={perimeter}
        fields={takes.period ? DATES.period : DATES.date}
      />
      {/* No node to choose — none in the reference, none the API lets one read —: none offered,
          unless the address already filters on one, which stays shown to be cleared. */}
      {takes.node && (nodes.length > 0 || perimeter.orgNode !== undefined) ? (
        <ViewChoice
          name={ORG_NODE}
          label={t("orgNode")}
          none={t("everyNode")}
          value={perimeter.orgNode}
          offered={nodes.map((node) => ({
            value: node.id,
            label: treeLabel(node.level, named("choice", { code: node.code, label: node.label })),
          }))}
          write={(value) => {
            change(() => ({ [ORG_NODE]: value }));
          }}
        />
      ) : null}
      {view !== undefined && "horizon" in view ? (
        <ViewChoice
          name={HORIZON}
          label={t("horizon")}
          none={t("byDefault")}
          value={view.horizon}
          offered={withChosen(HORIZONS, view.horizon).map((months) => ({
            value: months,
            label: t("months", { months }),
          }))}
          write={(value) => {
            change(() => ({ [HORIZON]: value }));
          }}
        />
      ) : null}
      {view !== undefined && "threshold" in view ? (
        <ViewChoice
          name={THRESHOLD}
          label={t("threshold")}
          none={t("byDefault")}
          value={view.threshold}
          offered={withChosen(THRESHOLDS, view.threshold).map((value) => ({
            value,
            label: formatPercent(value, locale),
          }))}
          write={(value) => {
            change(() => ({ [THRESHOLD]: value }));
          }}
        />
      ) : null}
    </section>
  );
}
