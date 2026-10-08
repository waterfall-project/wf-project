// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a list on the bounds of its columns of figures (WF-IHM-0130, #545), beside its
 * grid: for each column, the least and the most it retains, both included — the hours and the
 * headcount of the roles, the hours of each day of the calendars, the depth of the nodes, the rate
 * of a year of the grid of the rates, the amounts of the lists to come. One form for the columns of
 * a list, sent together: each bound entered as the language writes a number (`parseDecimal`), and
 * written in the address as the contract writes it, under `<column>_min` and `<column>_max`
 * (`filters.ts`), back to the first page of a list the server pages; a side left empty is no bound.
 * A bound that is not a number of the language — or an amount of more than two decimals — is said at
 * its field, which takes the focus, and nothing is asked. The server filters, never the front, and
 * decides alone whether the bounds hold: a bound it refuses (422) — not a number of its type, an
 * upper bound below the lower one, which it names, the year of the rate missing — is said at its
 * field, which takes the focus when the list comes back refused. A filter may go with one more
 * choice — the year whose rate is bounded (`scope`) —, written while a bound is, lifted with the
 * last. A change goes on from the address last asked (`usePendingAddress`): a sort under way is
 * kept.
 *
 * Each field is named by its column and its side, both written beside it (« Heures par mois »,
 * « min. »), so that its name holds what the eye reads (WCAG 2.5.3).
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { ListFilter, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { editableDecimal, formatDecimal, parseDecimal } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

import {
  type BoundRefusal,
  type Bounds,
  bounded,
  boundsHref,
  FIGURES,
  type FigureKind,
} from "./filters";
import { usePendingAddress } from "./pending-address";

/** The sides of a column, from the least. */
const SIDES = ["min", "max"] as const;

/** A side of a column: its least or its most. */
type Side = (typeof SIDES)[number];

/** The refusals of the API on the bounds of one column, by side. */
export type SideRefusals = Readonly<Partial<Record<Side, BoundRefusal>>>;

/** A column of figures a list may be bounded on. */
export interface RangeColumn {
  /** The column as the address names it: its bounds are `<column>_min` and `<column>_max`. */
  readonly column: string;
  /** What the column holds, as its header says it. */
  readonly label: string;
  /** The bounds the address sets on it. */
  readonly bounds: Bounds;
  /** What the API refused of its bounds (422); none when it refused none. */
  readonly refused?: SideRefusals | undefined;
}

/** A choice a filter of bounds goes with: the year whose rate is bounded. */
export interface RangeScope {
  /** The parameter of the address it writes. */
  readonly name: string;
  readonly label: string;
  /** The values offered, each with its text, in their order. */
  readonly choices: readonly { readonly value: string; readonly text: string }[];
  /** The value chosen, the first offered when the address names none. */
  readonly chosen: string | undefined;
  /** What the API refused of it (422); none when it refused nothing. */
  readonly refused?: BoundRefusal | undefined;
}

/** What a filter of bounds shows. */
export interface RangeFilterProps {
  /** The name of the form: the bounds of which list. */
  readonly label: string;
  readonly columns: readonly RangeColumn[];
  /** The figure each bound is: an exact decimal, an amount, or a depth. */
  readonly kind: FigureKind;
  readonly scope?: RangeScope | undefined;
  /** The parameter of the page of a list the server pages, which a filter takes back to its first. */
  readonly page?: string | undefined;
}

/** The texts the fields hold, by column and side, as the language writes them. */
type Texts = Readonly<Record<string, Readonly<Record<Side, string>>>>;

/** Why a text entered is not sent: no number of the language, or an amount of too many decimals. */
type Fault = "number" | "money";

/** The faults of the texts entered, by `<column>.<side>`. */
type Faults = ReadonlyMap<string, Fault>;

/** The fields the form marks wrong, of which the first takes the focus. */
const WRONG = '[aria-invalid="true"]';

/**
 * Render the filter of a list on the bounds of its columns of figures. The bounds the address
 * changed — back in the history, or refused anew — set the fields anew.
 */
export function RangeFilter(props: RangeFilterProps) {
  const key = JSON.stringify([
    props.columns.map(({ bounds, refused }) => [bounds.min, bounds.max, refused]),
    props.scope?.chosen,
    props.scope?.refused,
  ]);
  return <RangeForm key={key} {...props} />;
}

/** What a text entered gives: the figure of the contract, or none; or why it is not one. */
type Read = { readonly figure: string | undefined } | { readonly fault: Fault };

/** A bound the language writes as the figure of the contract, or why it is not one. */
function readText(text: string, kind: FigureKind, locale: Locale): Read {
  const trimmed = text.trim();
  if (trimmed === "") {
    return { figure: undefined };
  }
  const figure = parseDecimal(trimmed, locale);
  if (figure === undefined || (kind === "level" && !FIGURES.level.test(figure))) {
    return { fault: "number" };
  }
  return kind === "money" && !FIGURES.money.test(figure) ? { fault: "money" } : { figure };
}

/** The figure a text gave, none when it gave a fault. */
function figureOf(read: Read): string | undefined {
  return "figure" in read ? read.figure : undefined;
}

/** The sentence that says why a field is wrong: a fault of what was typed, or a refusal of the API. */
function useProblem(): (fault: Fault | undefined, refusal: BoundRefusal | undefined) => string {
  const t = useTranslations("grid.range");
  const errors = useTranslations("errors");
  const locale = useLocale();
  return (fault, refusal) => {
    if (fault === "money") {
      return t("money");
    }
    if (fault === "number" || refusal?.code === "NUMBER_INVALID") {
      return errors("NUMBER_INVALID");
    }
    if (refusal?.code === "VALUE_OUT_OF_RANGE") {
      return t("inverted", { minimum: formatDecimal(refusal.minimum, locale) });
    }
    return errors("VALUE_REQUIRED");
  };
}

/** The two fields of a column, each named by the column and its side, and what is wrong with them. */
function ColumnFields({
  column,
  texts,
  faults,
  onText,
}: {
  readonly column: RangeColumn;
  readonly texts: Readonly<Record<Side, string>>;
  readonly faults: Faults;
  readonly onText: (side: Side, text: string) => void;
}) {
  const t = useTranslations("grid.range");
  const problemOf = useProblem();
  const problem = `${useId()}-problem`;
  const { label, refused } = column;
  // What was typed wrong says more than what the API refused of the bounds sent before.
  const typed = SIDES.filter((side) => faults.has(`${column.column}.${side}`));
  const wrong = typed.length > 0 ? typed : SIDES.filter((side) => refused?.[side] !== undefined);
  const [first] = wrong;
  const said =
    first === undefined
      ? undefined
      : problemOf(faults.get(`${column.column}.${first}`), refused?.[first]);
  return (
    <div role="group" aria-label={label} className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-sm">
        <span aria-hidden="true">{label}</span>
        {SIDES.map((side) => (
          <label key={side} className="flex items-center gap-1 text-xs text-muted-foreground">
            <span aria-hidden="true">{t(`${side}Short`)}</span>
            <Input
              inputMode="decimal"
              aria-label={t(side, { column: label })}
              value={texts[side]}
              aria-invalid={wrong.includes(side) ? true : undefined}
              aria-describedby={wrong.includes(side) ? problem : undefined}
              onChange={(event) => {
                onText(side, event.target.value);
              }}
              className="h-7 w-20 text-xs text-foreground tabular-nums"
            />
          </label>
        ))}
      </div>
      {said === undefined ? null : (
        <p id={problem} className="text-xs text-destructive">
          {said}
        </p>
      )}
    </div>
  );
}

/** The choice the bounds go with — the year whose rate is bounded —, and its refusal. */
function ScopeField({
  scope,
  chosen,
  onChoose,
}: {
  readonly scope: RangeScope;
  readonly chosen: string;
  readonly onChoose: (value: string) => void;
}) {
  const id = useId();
  const problemOf = useProblem();
  const problem = `${id}-problem`;
  const refused = scope.refused !== undefined;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2 text-sm">
        <Label htmlFor={id}>{scope.label}</Label>
        <NativeSelect
          id={id}
          value={chosen}
          aria-invalid={refused ? true : undefined}
          aria-describedby={refused ? problem : undefined}
          onChange={(event) => {
            onChoose(event.target.value);
          }}
          className="w-24"
        >
          {scope.choices.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.text}
            </option>
          ))}
        </NativeSelect>
      </div>
      {refused ? (
        <p id={problem} className="text-xs text-destructive">
          {problemOf(undefined, scope.refused)}
        </p>
      ) : null}
    </div>
  );
}

/** The texts of the fields, from the bounds of the address, as the language writes them. */
function initialTexts(columns: readonly RangeColumn[], locale: Locale): Texts {
  const written = (value: string | undefined) =>
    value === undefined ? "" : editableDecimal(value, locale);
  return Object.fromEntries(
    columns.map(({ column, bounds }) => [
      column,
      { min: written(bounds.min), max: written(bounds.max) },
    ]),
  );
}

/** The form of a filter of bounds, from the bounds the address held when it was drawn. */
function RangeForm({ label, columns, kind, scope, page }: RangeFilterProps) {
  const t = useTranslations("grid.range");
  const locale = useLocale();
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const form = useRef<HTMLFormElement>(null);
  const [texts, setTexts] = useState<Texts>(() => initialTexts(columns, locale));
  const [chosen, setChosen] = useState(scope?.chosen ?? scope?.choices[0]?.value ?? "");
  const [faults, setFaults] = useState<Faults>(() => new Map());
  // Each send refused in the form; the bounds the API refused, the form drawn anew for them.
  const [attempts, setAttempts] = useState(0);
  const refused = columns.some((column) => column.refused !== undefined) || scope?.refused;
  useEffect(() => {
    if (attempts > 0 || refused !== undefined) {
      form.current?.querySelector<HTMLElement>(WRONG)?.focus();
    }
  }, [attempts, refused]);
  const send = (written: Texts) => {
    const read = columns.map(({ column }) => ({
      column,
      min: readText(written[column]?.min ?? "", kind, locale),
      max: readText(written[column]?.max ?? "", kind, locale),
    }));
    const found = new Map<string, Fault>();
    for (const entry of read) {
      for (const side of SIDES) {
        const value = entry[side];
        if ("fault" in value) {
          found.set(`${entry.column}.${side}`, value.fault);
        }
      }
    }
    setFaults(found);
    if (found.size > 0) {
      setAttempts((before) => before + 1);
      return;
    }
    // No fault left: each side a figure of the contract, or none.
    const asked = read.map(({ column, min, max }) => ({
      column,
      bounds: { min: figureOf(min), max: figureOf(max) },
    }));
    request((query) =>
      boundsHref(pathname, query, asked, {
        scope: scope === undefined ? undefined : { name: scope.name, value: chosen },
        page,
      }),
    );
  };
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    send(texts);
  };
  const lifted = Object.fromEntries(columns.map(({ column }) => [column, { min: "", max: "" }]));
  return (
    <form
      ref={form}
      aria-label={label}
      onSubmit={submit}
      className="flex flex-wrap items-start gap-x-4 gap-y-2"
    >
      {scope === undefined ? null : (
        <ScopeField scope={scope} chosen={chosen} onChoose={setChosen} />
      )}
      {columns.map((column) => (
        <ColumnFields
          key={column.column}
          column={column}
          texts={texts[column.column] ?? { min: "", max: "" }}
          faults={faults}
          onText={(side, text) => {
            setTexts((before) => ({
              ...before,
              [column.column]: { min: "", max: "", ...before[column.column], [side]: text },
            }));
          }}
        />
      ))}
      <div className="flex items-center gap-1.5">
        <Button type="submit" size="sm" variant="outline">
          <ListFilter aria-hidden="true" className="size-4" />
          {t("apply")}
        </Button>
        {columns.some(({ bounds }) => bounded(bounds)) ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => {
              setTexts(lifted);
              send(lifted);
            }}
          >
            <X aria-hidden="true" className="size-4" />
            {t("lift")}
          </Button>
        ) : null}
      </div>
    </form>
  );
}
