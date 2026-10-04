// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The perimeter of a view of the portfolio, as the user chooses it (WF-PTF-0010): the states it
 * retains — the projects in progress, to which the offers in pricing may be added, and the projects
 * completed —, the period and the date of calculation; and, for the views that take them, the
 * horizon and the threshold of under-load (WF-PTF-0060). A choice only changes the address, under
 * the names of the contract, and the page reads anew what the server computes on it. A state shows
 * pressed as the address asks it, or, when the address asks none, as the server retained it by
 * default (`scope.states`): the front assumes no default of its own. A change goes on from the
 * address last asked (`usePendingAddress`).
 */
"use client";

import { CalendarRange, Circle, CircleCheck } from "lucide-react";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState } from "react";

import { usePendingAddress } from "@/components/grid/pending-address";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { formatPercent } from "@/i18n/format";

import {
  AS_OF,
  FROM,
  HORIZON,
  HORIZONS,
  type Perimeter,
  PORTFOLIO_STATES,
  type ProjectState,
  parametersHref,
  readStates,
  STATES,
  statesValue,
  THRESHOLD,
  THRESHOLDS,
  TO,
} from "./address";

/** Change parameters of the address last asked, from what it asks. */
function useParameters() {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  return (change: (query: URLSearchParams) => Readonly<Record<string, string | undefined>>) => {
    request((query) => parametersHref(pathname, query, change(query)));
  };
}

/** The filter by state: a button for each state of a portfolio, pressed as retained. */
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
        const Icon = pressed ? CircleCheck : Circle;
        return (
          <Button
            key={state}
            size="sm"
            variant={pressed ? "default" : "outline"}
            aria-pressed={pressed}
            onClick={() => {
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
            {t(`enums.ProjectState.${state}`)}
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

/** A parameter of a view chosen among the values it offers, or left to the server. */
function ViewChoice({
  name,
  label,
  value,
  offered,
  write,
}: {
  readonly name: string;
  readonly label: string;
  readonly value: string | undefined;
  readonly offered: readonly { readonly value: string; readonly label: string }[];
  readonly write: (value: string | undefined) => void;
}) {
  const t = useTranslations("portfolio.perimeter");
  const id = useId();
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
        className="w-40"
      >
        <option value="">{t("byDefault")}</option>
        {offered.map((each) => (
          <option key={each.value} value={each.value}>
            {each.label}
          </option>
        ))}
      </NativeSelect>
    </div>
  );
}

/** The parameters of a view the address asks: its horizon, its threshold; none, not offered. */
export interface ViewParameters {
  readonly horizon?: string | undefined;
  readonly threshold?: string | undefined;
}

/** What the perimeter shows: what the address asks, what the server retained, what the view takes. */
export interface PerimeterBarProps {
  readonly perimeter: Perimeter;
  readonly retained: readonly ProjectState[];
  /**
   * Whether the view takes a period; the aggregated workload, the cost structure, the cash-out and
   * the health of the steering take the date of calculation alone.
   */
  readonly period?: boolean;
  /** The parameters the view takes, and their value; none, and none is offered. */
  readonly view?: ViewParameters;
}

/** Render the perimeter of a view of the portfolio, as the address asks it. */
export function PerimeterBar({ perimeter, retained, period = true, view }: PerimeterBarProps) {
  const t = useTranslations("portfolio.perimeter");
  const locale = useLocale();
  const change = useParameters();
  return (
    <section aria-label={t("label")} className="flex flex-wrap items-center gap-x-6 gap-y-2">
      <StatesFilter asked={perimeter.states} retained={retained} />
      {/* Dates the address changed — back in the history — set the fields anew. */}
      <DatesForm
        key={`${perimeter.from ?? ""}/${perimeter.to ?? ""}/${perimeter.asOf ?? ""}`}
        perimeter={perimeter}
        fields={period ? DATES.period : DATES.date}
      />
      {view !== undefined && "horizon" in view ? (
        <ViewChoice
          name={HORIZON}
          label={t("horizon")}
          value={view.horizon}
          offered={HORIZONS.map((months) => ({ value: months, label: t("months", { months }) }))}
          write={(value) => {
            change(() => ({ [HORIZON]: value }));
          }}
        />
      ) : null}
      {view !== undefined && "threshold" in view ? (
        <ViewChoice
          name={THRESHOLD}
          label={t("threshold")}
          value={view.threshold}
          offered={THRESHOLDS.map((value) => ({ value, label: formatPercent(value, locale) }))}
          write={(value) => {
            change(() => ({ [THRESHOLD]: value }));
          }}
        />
      ) : null}
    </section>
  );
}
