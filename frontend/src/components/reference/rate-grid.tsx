// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the hourly rates (WF-REF-0050, US-0250): one row for each category of labour, one
 * column for each year the server gives — a hundred and fifty categories over fifteen years
 * (§4.6.2) —, on the dense grid, given its configuration here, on the side of the browser. The
 * page hands it data only: the grid as the server answers it, the currency of the installation,
 * whether the session may modify the cost settings, what the address asked and the settings the
 * session read.
 *
 * Each cell entered is written alone (`setHourlyRate`): the first rate of a year without a
 * version, a correction with the version of the rate read; the rate the server answers takes the
 * place of the cell, and a refusal is told as every grid tells one. A year without a rate is an
 * empty cell; no column appears of itself (WF-REF-0060). The server orders the rows, searches them
 * (`search`) and pages them (`offset`), as the address asks under the names of the contract: each
 * column sorts (#509, WF-IHM-0060) — the code, the label, the state, and the rate of each year
 * (`rate.<year>`) —, the years being those of the whole grid on every page. Its totals row says how
 * many categories the server retained and the currency of the rates, never a sum; its pages lead
 * to the others (`ReferencePages`). The page filters it, beside it, on the state of the categories
 * and on the bounds of the rate of a year (`RateFilterBar`, #545). The state of each category says the deactivated ones, which the
 * page reads when the address asks for them (WF-REF-0150); the list of the categories reactivates
 * them.
 *
 * A session that may enter the rates adds the column of a year the grid has none for (WF-REF-0060):
 * the contract has no operation for it — a year comes into the grid with the first rate entered in
 * it (`getHourlyRateGrid`) —, so the column is the grid's own, empty, in the order of the years,
 * until its first cell entered writes that rate as any first rate, without a version. A year the
 * grid already has, or that the contract does not take (`Year`, 2000 to 2100), is refused at once;
 * the rates of the other years are left as they are. A column added whose cells hold no rate yet is
 * taken away as it came — not while its first rate is being written —; once a rate is entered, it
 * is the server's. A reading anew — a search, a sort, a page, a reload — that holds the year shows
 * it as the server gives it; the column of a year added sorts as the others, the server leaving the
 * order of the code for a year without a rate.
 */
"use client";

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useCallback, useId, useMemo, useState } from "react";

import { setHourlyRate } from "@/api/actions/reference";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import type { GridColumn, GridConfig, RowsWritten } from "@/components/grid/columns";
import { DenseGrid } from "@/components/grid/dense-grid";
import { boundNames } from "@/components/grid/filters";
import { CONTRACT_ADDRESS, type GridQuery, OFFSET } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { listReads } from "./address";
import {
  FIRST_YEAR,
  LAST_YEAR,
  RATE_COLUMN,
  RATE_GRID_KEY,
  RATE_STATE,
  RATE_YEAR,
  type RateSort,
  rateSort,
} from "./rate-columns";
import { ReferencePages } from "./reference-pages";
import { ActiveState } from "./section";

/** The grid of the hourly rates, as the server answers it. */
export type HourlyRateGrid = components["schemas"]["HourlyRateGrid"];

/** A category of labour and its rate for each year of the grid. */
type RateRow = components["schemas"]["HourlyRateRow"];

/** The hourly rate of a category for a year. */
type HourlyRate = components["schemas"]["HourlyRate"];

/** The parameters of the address the grid of the rates reads, under the names of the contract. */
const RATE_READS = listReads(
  CONTRACT_ADDRESS,
  RATE_STATE,
  RATE_YEAR,
  ...Object.values(boundNames(RATE_COLUMN)),
);

/** A column of the grid of the rates: no totals but the caption. */
type RateColumn = GridColumn<RateRow, RateSort, null>;

/**
 * The row with the rate the server answered in the cell written; none when the server answered
 * the rate of another category or another year — a failure of the service, told as such.
 */
function written(
  row: RateRow,
  year: number,
  index: number,
  rate: HourlyRate,
  order: number,
): RowsWritten<RateRow, null> {
  const same = rate.cost_category_id === row.cost_category_id && rate.year === year;
  // The column of a year the grid added stands past the cells of the answer: the row grows to it.
  const cells = Array.from({ length: Math.max(row.cells.length, index + 1) }, (_, at) =>
    at === index ? rate : (row.cells[at] ?? null),
  );
  return {
    rows: same ? [{ ...row, cells }] : [],
    changed: [],
    parts: [],
    totals: undefined,
    order,
  };
}

/**
 * The column of a year: its heading the year itself, each cell the rate of its category as an
 * amount — `index` its place among the cells of a row, past those of the answer for a year the
 * grid added —; entered where the session may modify the cost settings, from the version read.
 */
function yearColumn(
  year: number,
  index: number,
  editable: boolean,
  answered: () => number,
  track: YearTracker,
): RateColumn {
  const rate = (row: RateRow) => row.cells[index]?.amount;
  return {
    key: `year_${year.toString()}`,
    label: "hourlyRate",
    heading: year.toString(),
    format: "money",
    width: 76,
    contract: rateSort(year),
    value: rate,
    entry: editable
      ? {
          kind: { type: "money", nullable: false },
          in: () => true,
          value: rate,
          write: async (row, value): Promise<Outcome<RowsWritten<RateRow, null>>> => {
            if (value === null) {
              // The entry of an amount required never validates an empty cell (`cell-values.ts`):
              // a defect of the front, which the grid tells as the unexpected error, never as the
              // API out of reach (`rejected`, #304).
              throw new Error("an hourly rate is never emptied");
            }
            const read = row.cells[index];
            // A column whose rate is being written is not taken away meanwhile.
            track(year, "writing");
            const outcome = await setHourlyRate(row.cost_category_id, year, {
              amount: value,
              ...(read === null || read === undefined ? {} : { lock_version: read.lock_version }),
            }).finally(() => {
              track(year, "written");
            });
            if (outcome.kind !== "done") {
              return outcome;
            }
            track(year, "rated");
            return { kind: "done", data: written(row, year, index, outcome.data, answered()) };
          },
        }
      : undefined,
  };
}

/**
 * What the grid learns of the writes of a column: one leaves, one is answered, a rate is the
 * server's — the column of a year added is then no longer taken away.
 */
type YearTracker = (year: number, phase: "writing" | "written" | "rated") => void;

/**
 * The place of each answer among the writes of a grid: the cells of a row leave one after the
 * other, and each answer counts one more than the one before it, whatever reading it belongs to.
 */
function counter(): () => number {
  let answered = 0;
  return () => {
    answered += 1;
    return answered;
  };
}

/** A year of the grid, and the place of its rate among the cells of a row. */
interface YearCell {
  readonly year: number;
  readonly index: number;
}

/**
 * A year the grid added, and its slot past the cells of the answer: given once, never reused, so
 * that a column taken away moves no other one.
 */
export interface AddedYear {
  readonly year: number;
  readonly slot: number;
}

/**
 * The years of the grid in their order: those of the answer, each at its place among the cells,
 * and those the grid added that the answer does not hold, past them, at their slot.
 */
export function gridYears(answered: readonly number[], added: readonly AddedYear[]): YearCell[] {
  const extra = added.filter(({ year }) => !answered.includes(year));
  return [
    ...answered.map((year, index) => ({ year, index })),
    ...extra.map(({ year, slot }) => ({ year, index: answered.length + slot })),
  ].toSorted((a, b) => a.year - b.year);
}

/** The width of the column of the state of a category. */
const STATE_WIDTH = 100;

/** The grid of the rates, a column for each year of the answer and each the grid added. */
function rateGrid(
  years: readonly YearCell[],
  editable: boolean,
  answered: () => number,
  track: YearTracker,
): GridConfig<RateRow, RateSort, null> {
  return {
    key: RATE_GRID_KEY,
    name: "hourlyRates",
    searched: true,
    rowKey: (row) => row.cost_category_id,
    columns: [
      {
        key: "code",
        label: "code",
        format: "text",
        width: 80,
        pinned: true,
        contract: "code",
        value: (row) => row.code,
      },
      {
        key: "label",
        label: "label",
        format: "text",
        width: 240,
        pinned: true,
        contract: "label",
        value: (row) => row.label,
      },
      {
        key: "state",
        label: "state",
        format: "text",
        width: STATE_WIDTH,
        contract: "is_active",
        value: (row) => (row.is_active ? "active" : "inactive"),
        render: (row) => <ActiveState active={row.is_active} />,
      },
      ...years.map(({ year, index }) => yearColumn(year, index, editable, answered, track)),
    ],
  };
}

/** What the grid of the rates shows. */
export interface RateGridProps {
  readonly grid: HourlyRateGrid;
  /** The currency of the installation, in which every rate is expressed (WF-REF-0140). */
  readonly currency: string;
  /** Whether the session may modify the cost settings (`platformOffer`). */
  readonly editable: boolean;
  readonly query: GridQuery<RateSort>;
  readonly preferences: GridPreferences | undefined;
}

/** What the form of a year says of the last year asked: added, already there, or not a year. */
type YearNotice =
  { readonly kind: "added" | "present"; readonly year: number } | { readonly kind: "outOfRange" };

/**
 * The form that adds the column of a year: the year typed, refused when the grid already has it or
 * the contract does not take it, added otherwise — what it says of it announced.
 */
function AddYear({
  years,
  onAdd,
  removable,
  onRemove,
}: {
  readonly years: readonly number[];
  readonly onAdd: (year: number) => void;
  /** The years added whose column holds no rate yet, which may be taken away. */
  readonly removable: readonly number[];
  readonly onRemove: (year: number) => void;
}) {
  const t = useTranslations("reference.rates.addYear");
  const field = useId();
  const problem = useId();
  const [text, setText] = useState("");
  const [notice, setNotice] = useState<YearNotice>();
  const refused = notice !== undefined && notice.kind !== "added";
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    const year = /^\d{4}$/.test(text.trim()) ? Number.parseInt(text.trim(), 10) : Number.NaN;
    if (!(year >= FIRST_YEAR && year <= LAST_YEAR)) {
      setNotice({ kind: "outOfRange" });
    } else if (years.includes(year)) {
      setNotice({ kind: "present", year });
    } else {
      onAdd(year);
      setText("");
      setNotice({ kind: "added", year });
    }
  };
  return (
    <form aria-label={t("label")} onSubmit={submit} className="flex flex-wrap items-center gap-2">
      <Label htmlFor={field} className="text-xs">
        {t("year")}
      </Label>
      <Input
        id={field}
        inputMode="numeric"
        value={text}
        maxLength={4}
        aria-invalid={refused ? true : undefined}
        aria-describedby={refused ? problem : undefined}
        onChange={(event) => {
          setText(event.target.value);
        }}
        className="h-7 w-20 text-xs"
      />
      <Button type="submit" variant="outline" size="sm" className="h-7 text-xs">
        {t("submit")}
      </Button>
      {removable.map((year) => (
        <Button
          key={year}
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs"
          onClick={() => {
            onRemove(year);
            setNotice(undefined);
          }}
        >
          <X aria-hidden="true" />
          {t("remove", { year: year.toString() })}
        </Button>
      ))}
      <p role="status" className="text-xs text-muted-foreground">
        {notice?.kind === "added" ? t("added", { year: notice.year.toString() }) : null}
      </p>
      {notice === undefined || notice.kind === "added" ? null : (
        <p id={problem} role="alert" className="text-xs text-destructive">
          {notice.kind === "present"
            ? t("present", { year: notice.year.toString() })
            : t("outOfRange", { min: FIRST_YEAR.toString(), max: LAST_YEAR.toString() })}
        </p>
      )}
    </form>
  );
}

/** Render the grid of the hourly rates, its totals row the currency they are expressed in. */
export function RateGrid({ grid, currency, editable, query, preferences }: RateGridProps) {
  const t = useTranslations("reference.rates");
  const names = useTranslations("grid.names");
  // One count of the answers for the life of the grid, never taken back by a new configuration:
  // kept by the state, which a configuration remade reads as it is.
  const [answered] = useState(counter);
  // The years the grid added, each at its slot: their columns, until the answer has them; those
  // whose column was entered, which stay — their rate is the server's —; the next slot.
  const [added, setAdded] = useState<readonly AddedYear[]>([]);
  const [rated, setRated] = useState<ReadonlySet<number>>(() => new Set());
  // The writes under way, by year: a column added is not taken away while its rate is written.
  const [writing, setWriting] = useState<ReadonlyMap<number, number>>(() => new Map());
  const [slots, setSlots] = useState(0);
  const track = useCallback<YearTracker>((year, phase) => {
    if (phase === "rated") {
      setRated((before) => new Set(before).add(year));
      return;
    }
    setWriting((before) => {
      const count = (before.get(year) ?? 0) + (phase === "writing" ? 1 : -1);
      const next = new Map(before);
      if (count > 0) {
        next.set(year, count);
      } else {
        next.delete(year);
      }
      return next;
    });
  }, []);
  const years = useMemo(() => gridYears(grid.years, added), [grid.years, added]);
  const config = useMemo(
    () => rateGrid(years, editable, answered, track),
    [years, editable, answered, track],
  );
  return (
    <div className="flex min-h-0 flex-col gap-2">
      {editable ? (
        <AddYear
          years={years.map(({ year }) => year)}
          onAdd={(year) => {
            setAdded((before) => [...before, { year, slot: slots }]);
            setSlots(slots + 1);
          }}
          removable={added
            .map(({ year }) => year)
            .filter((year) => !grid.years.includes(year) && !rated.has(year) && !writing.has(year))}
          onRemove={(year) => {
            setAdded((before) => before.filter((each) => each.year !== year));
          }}
        />
      ) : null}
      <DenseGrid
        config={config}
        rows={grid.rows}
        totals={null}
        totalsCaption={() => t("caption", { count: grid.meta.total, currency })}
        query={query}
        preferences={preferences}
      />
      <ReferencePages
        list={{ page: OFFSET, reads: RATE_READS }}
        title={names("hourlyRates")}
        page={grid.meta}
        shown={grid.rows.length}
      />
    </div>
  );
}
