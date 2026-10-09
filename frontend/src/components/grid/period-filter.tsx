// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a list on a period of one of its columns of dates (WF-IHM-0130), beside its grid: a
 * start and an end, sent together, in the form of the period the contract takes (`period.ts`) — two
 * days of planning, both included (the documents of the actual costs); two local days, drawn as the
 * instants of the start of the first and of the start of the day after the last (the last
 * modification of the projects of the home, #522); two instants entered to the minute, the end
 * excluded (the journal of audit). Each field keeps the other side of the period: a start after the
 * end is not offered. A period only changes the address, under the names of the contract
 * (`periodHref`), back to the first page of a list the server pages; a side left empty is no bound,
 * and a side left untouched leaves as the address names it, never through its field.
 *
 * Only the browser knows its time zone: the fields of the instants show those of the address once
 * the page is hydrated, and the period is sent from then on — before, the browser would send the
 * form itself.
 *
 * The server filters, never the front, and decides alone whether the period holds: a side it
 * refuses (422) — a bound it does not take, an end before the start, which it names
 * (`params.minimum`) — is said at its field, the start named as the field shows it, which takes the
 * focus each time the list comes back refused, as the bounds of a column of figures are
 * (`range-filter.tsx`). A change goes on from the address last asked (`usePendingAddress`): a sort
 * under way is kept. What is entered is dated by the period of the address (`useDatedEntry`): a
 * period the address changes — sent and arrived, or back in the history — shows anew, and the form,
 * never remounted, keeps the focus where it was. A side typed while the other, sent, is on its way
 * survives the arrival; the send settles the entry (`sent`), what it sent arriving as the address
 * writes it. The address asked is shared with the bar of the filter (`PendingAddress`).
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { ListFilter } from "lucide-react";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useHydrated } from "@/components/use-hydrated";
import { formatPlanningDate, formatTimestamp, isPlanningDate } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

import { useDatedEntry } from "./dated-entry";
import { usePendingAddress } from "./pending-address";
import {
  addressOf,
  fieldOf,
  isInstant,
  localDay,
  PERIOD,
  PERIOD_SIDES,
  type Period,
  periodHref,
  type PeriodKind,
  type PeriodNames,
  type PeriodRefusal,
  type PeriodRefusals,
  type PeriodSide,
} from "./period";

/** The fields marked wrong, of which the first takes the focus when a list comes back refused. */
const WRONG = '[aria-invalid="true"]';

/** The texts of a filter of a period, translated: its two fields and its button. */
export interface PeriodTexts {
  readonly from: string;
  readonly to: string;
  readonly apply: string;
}

/** What a filter of a period shows. */
export interface PeriodFilterProps {
  /** The name of the form: the period of which column. */
  readonly label: string;
  /** The form of the period the contract takes. */
  readonly kind: PeriodKind;
  /** The period the address sets. */
  readonly period: Period;
  /** What the API refused of it (422); none when it refused nothing. */
  readonly refused?: PeriodRefusals | undefined;
  /** The texts of its fields and of its button; those of a period, « Du », « Au », by default. */
  readonly texts?: PeriodTexts | undefined;
  /** The parameters it writes; those of the contract, `from` and `to`, by default. */
  readonly names?: PeriodNames | undefined;
  /**
   * The parameter of the page of a list the server pages, which a period takes back to its first.
   */
  readonly page?: string | undefined;
}

/**
 * The start an end was refused against, as the field of the start shows it: a day of planning, the
 * local day of an instant drawn from days, or an instant in the local time; none while only the
 * browser could say it, before the hydration, or of a start the form of the period does not take.
 */
function startShown(
  kind: PeriodKind,
  minimum: string,
  locale: Locale,
  hydrated: boolean,
): string | undefined {
  if (kind === "date") {
    return isPlanningDate(minimum) ? formatPlanningDate(minimum, locale) : undefined;
  }
  if (!hydrated || !isInstant(minimum)) {
    return undefined;
  }
  return kind === "day"
    ? formatPlanningDate(localDay(minimum), locale)
    : formatTimestamp(minimum, locale);
}

/** The sentence that says why the API refused a side of the period. */
function useProblem(kind: PeriodKind): (refusal: PeriodRefusal) => string {
  const t = useTranslations("grid.period");
  const errors = useTranslations("errors");
  const locale = useLocale();
  const hydrated = useHydrated();
  return (refusal) => {
    if (refusal.code === "DATE_INVALID") {
      return errors("DATE_INVALID");
    }
    const start = startShown(kind, refusal.minimum, locale, hydrated);
    return start === undefined ? t("invertedUndated") : t("inverted", { minimum: start });
  };
}

/** Render the filter of a list on a period of a column of dates. */
export function PeriodFilter({
  label,
  kind,
  period,
  refused,
  texts,
  names = PERIOD,
  page,
}: PeriodFilterProps) {
  const t = useTranslations("grid.period");
  const shownTexts = texts ?? { from: t("from"), to: t("to"), apply: t("apply") };
  const problemOf = useProblem(kind);
  const id = useId();
  const hydrated = useHydrated();
  // A day of planning needs no time zone; an instant shows, and is sent, once in the browser.
  const ready = kind === "date" || hydrated;
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const form = useRef<HTMLFormElement>(null);
  // What the address filters on, the parameters of the form alone: a sort, another filter, leave
  // what is entered as it is.
  const over = `${period.from ?? ""}/${period.to ?? ""}`;
  const { entered, enter, sent: settle } = useDatedEntry<PeriodSide>(over);
  /** What the field of a side shows: its entry, or the bound of the address in its form. */
  const shown = (side: PeriodSide) => {
    const bound = period[side];
    return entered[side] ?? (ready && bound !== undefined ? fieldOf(kind, side, bound) : "");
  };
  const fields = { from: shown("from"), to: shown("to") };
  // The sides the API refused, by what they are and the address they came back for: a list refused
  // anew takes the focus to its field, even for the same side refused again.
  const refusal = refused === undefined ? undefined : JSON.stringify([over, refused]);
  useEffect(() => {
    if (refusal !== undefined) {
      form.current?.querySelector<HTMLElement>(WRONG)?.focus();
    }
  }, [refusal]);
  /**
   * What a side sends: its entry, in the form of the contract; untouched, the bound of the address.
   */
  const sent = (side: PeriodSide) => {
    const entry = entered[side];
    return entry === undefined ? period[side] : addressOf(kind, side, entry);
  };
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    const asked = { from: sent("from"), to: sent("to") };
    // Sent, the period arrives as the address writes it: only what is typed after it stays.
    settle();
    request((query) => periodHref(pathname, query, asked, { names, page }));
  };
  return (
    <form
      ref={form}
      aria-label={label}
      onSubmit={submit}
      className="flex flex-wrap items-start gap-x-4 gap-y-2"
    >
      {PERIOD_SIDES.map((side) => {
        const field = `${id}-${side}`;
        const problem = `${field}-problem`;
        const sideRefusal = refused?.[side];
        return (
          <div key={side} className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-sm">
              <Label htmlFor={field}>{shownTexts[side]}</Label>
              <Input
                id={field}
                type={kind === "instant" ? "datetime-local" : "date"}
                value={fields[side]}
                // Each side keeps the other: a start after the end is not offered.
                {...(side === "from"
                  ? { max: fields.to === "" ? undefined : fields.to }
                  : { min: fields.from === "" ? undefined : fields.from })}
                aria-invalid={sideRefusal === undefined ? undefined : true}
                aria-describedby={sideRefusal === undefined ? undefined : problem}
                onChange={(event) => {
                  enter(side, event.target.value);
                }}
                className={kind === "instant" ? "h-8 w-52" : "h-8 w-40"}
              />
            </div>
            {sideRefusal === undefined ? null : (
              <p id={problem} className="text-xs text-destructive">
                {problemOf(sideRefusal)}
              </p>
            )}
          </div>
        );
      })}
      {/* Sent by React alone: before the hydration, the browser would send the form itself. */}
      <Button type="submit" size="sm" variant="outline" disabled={!ready}>
        <ListFilter aria-hidden="true" className="size-4" />
        {shownTexts.apply}
      </Button>
    </form>
  );
}
