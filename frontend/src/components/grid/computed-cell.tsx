// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A cell of a dense grid whose value the server computes (WF-IHM-0030): shaded by its row, marked
 * by Σ — the one mark of a computed value, which its header bears for a column computed whole —,
 * named « computed » to whoever does not see it, and never entered. Clicked, or pressed from the
 * keyboard, it refuses the entry beside it and names what its value depends on, as the server
 * says it once asked (`getComputedValueDependencies`): the rules that compute it, and the rows it
 * is drawn from — their number and their label —, all of them, whatever the search or the filters
 * of the grid retained. Until the server answers, the refusal says it is reading; a refusal of the
 * server, or the API out of reach, it tells as every screen does (`OutcomeNotice`).
 *
 * The cell is one of the grid, which the keyboard reaches as any other (`useGridEntry`): an entry
 * tried on it from the keyboard, or a click, opens its refusal, which the grid holds. Its popover
 * mounts on the first try only: a root of Radix in each computed cell would cost the hydration of
 * the first screen as many contexts, and the second of §4.6.2 counts it. The server is asked while
 * the refusal is open only, once for each question — the reading of the page, the row, the
 * field —: a page read anew asks nothing of a closed refusal, and asks afresh once it opens again,
 * the rows the answer named may have moved; a failure is asked again at the next opening. The
 * refusal reads out, in one live region, that it is reading, then what the server said.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import { Sigma } from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode, useEffect, useId, useState } from "react";

import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover";

import type {
  ComputedCells,
  ComputedDependencies,
  ComputedValueField,
  DependencyReader,
  GridColumn,
} from "./columns";

/** A column some of whose cells the server computes. */
export type ComputedColumn<Row, Sort extends string, Totals> = GridColumn<Row, Sort, Totals> & {
  readonly computed: ComputedCells<Row>;
};

/** The content of the cell: the whole of it, the mark at its start and the value at its end. */
const MARKED = "flex w-full min-w-0 items-center justify-between gap-0.5";

/** The API out of reach: the server action itself did not answer — the network is down. */
const UNREACHABLE: Outcome<ComputedDependencies> = { kind: "unreachable" };

/**
 * Ask the server what the value of a field of a row depends on, while the refusal is open and
 * has no answer to show: `undefined` until it answers. What the server said is kept for the
 * question it answers — the reading of the page, the row, the field —, and shown again as the
 * refusal opens again, a new reading asking afresh, since the rows it names may have moved. A
 * refusal or the API out of reach is shown for the opening it answered only: the next opening
 * asks again. An answer that comes once the question has changed, or the cell has gone, is
 * dropped.
 */
function useDependencies<Row>(
  dependencies: DependencyReader<Row> | undefined,
  row: Row,
  field: ComputedValueField,
  opening: number,
  open: boolean,
) {
  const reading = dependencies?.reading;
  const id = dependencies?.id(row);
  const [answer, setAnswer] = useState<{
    readonly reading: () => readonly Row[];
    readonly id: string;
    readonly field: ComputedValueField;
    readonly opening: number;
    readonly outcome: Outcome<ComputedDependencies>;
  }>();
  const kept =
    answer !== undefined &&
    answer.reading === reading &&
    answer.id === id &&
    answer.field === field &&
    (answer.outcome.kind === "done" || answer.opening === opening);
  const shown = kept ? answer.outcome : undefined;
  const asking = open && dependencies !== undefined && shown === undefined;
  const reader = asking ? dependencies : undefined;
  useEffect(() => {
    if (reader === undefined || id === undefined) {
      return undefined;
    }
    let live = true;
    const answered = (outcome: Outcome<ComputedDependencies>) => {
      if (live) {
        setAnswer({ reading: reader.reading, id, field, opening, outcome });
      }
    };
    void reader.read(id, field).then(answered, () => {
      answered(UNREACHABLE);
    });
    return () => {
      live = false;
    };
  }, [reader, id, field, opening]);
  return { answer: shown, reading: asking };
}

/**
 * Nothing to forget of a read: an answer stale (412) does not come of a read, and the screen,
 * read anew, asks again.
 */
function keep() {
  return undefined;
}

/** What the server said a value depends on: its rules, and the rows it is drawn from. */
function Dependencies({ dependencies }: { readonly dependencies: ComputedDependencies }) {
  const t = useTranslations();
  const listed = useId();
  return (
    <>
      {dependencies.depends_on.map((code) => (
        <p key={code} className="text-muted-foreground">
          {t(`enums.ComputedDependency.${code}`)}
        </p>
      ))}
      {dependencies.rows.length === 0 ? null : (
        <>
          <p id={listed} className="font-medium">
            {t("computedValue.dependsOn")}
          </p>
          <ul
            aria-labelledby={listed}
            tabIndex={0}
            className="max-h-48 space-y-0.5 overflow-y-auto"
          >
            {dependencies.rows.map((row) => (
              <li key={row.node_id} className="flex min-w-0 items-center gap-1.5">
                <span className="w-8 shrink-0 text-right text-muted-foreground tabular-nums">
                  {row.row_number}
                </span>
                <span className="truncate">{row.label}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}

/** What the refusal of an entry on a computed value reads. */
export interface ComputedRefusalProps<Row, Sort extends string, Totals> {
  readonly column: ComputedColumn<Row, Sort, Totals>;
  /** The row whose value was tried. */
  readonly row: Row;
  /** How to ask the server what the value depends on; none, and the refusal says no more. */
  readonly dependencies: DependencyReader<Row> | undefined;
  /** Whether the refusal shows: the server is asked while it does, and only then. */
  readonly open: boolean;
  /** How many times the refusal has opened: a failure is shown for its opening alone. */
  readonly opening: number;
}

/**
 * Render the refusal of an entry on a computed value, in its popover: the value is computed, and
 * what it depends on, once the server has said it. A dialog, named by its title.
 */
export function ComputedRefusal<Row, Sort extends string, Totals>({
  column,
  row,
  dependencies,
  open,
  opening,
}: ComputedRefusalProps<Row, Sort, Totals>) {
  const t = useTranslations("computedValue");
  const columns = useTranslations("grid.columns");
  const title = useId();
  const field = column.computed.field(row);
  const { answer, reading } = useDependencies(dependencies, row, field, opening, open);
  return (
    <PopoverContent aria-labelledby={title} className="w-80 space-y-1.5 text-xs">
      <p id={title} className="flex items-center gap-1.5 text-sm font-medium">
        <Sigma aria-hidden="true" className="size-3.5 shrink-0" />
        {t("title")}
      </p>
      <p>{t("refused", { column: columns(column.label) })}</p>
      {/* One region, in place as the refusal opens: what it reads, then what the server said. */}
      <div role="status" aria-live="polite" aria-busy={reading} className="space-y-1.5">
        {reading ? <p className="text-muted-foreground">{t("pending")}</p> : null}
        {answer?.kind === "done" ? <Dependencies dependencies={answer.data} /> : null}
        <OutcomeNotice outcome={answer} onClear={keep} />
      </div>
    </PopoverContent>
  );
}

/** What a computed cell shows, how it asks what its value depends on, and its refusal. */
export interface ComputedCellProps<Row, Sort extends string, Totals> {
  readonly column: ComputedColumn<Row, Sort, Totals>;
  /** The row of the cell. */
  readonly row: Row;
  /** How to ask the server what the value depends on, once an entry is tried. */
  readonly dependencies: DependencyReader<Row> | undefined;
  /** Whether its refusal shows: the grid opens it at a try, and closes it. */
  readonly open: boolean;
  /** How many times a refusal has opened in the grid: a failure is shown for its opening alone. */
  readonly opening: number;
  /** Close the refusal: Escape, or a click outside it. */
  readonly onClose: () => void;
  /** The value of the cell, formatted or rendered by its column. */
  readonly children: ReactNode;
}

/** Render a computed cell: its mark and its value, and the refusal of an entry once tried. */
export function ComputedCell<Row extends RowData, Sort extends string, Totals>({
  column,
  row,
  dependencies,
  open,
  opening,
  onClose,
  children,
}: ComputedCellProps<Row, Sort, Totals>) {
  const t = useTranslations("grid");
  // Engaged at the first try, and for as long as the row is rendered: what the server said is
  // kept from one opening to the next.
  const [engaged, setEngaged] = useState(open);
  if (open && !engaged) {
    setEngaged(true);
  }
  const content = (
    <span className={MARKED}>
      <Sigma role="img" aria-label={t("computed")} className="size-3 shrink-0" />
      <span className="min-w-0 truncate">{children}</span>
    </span>
  );
  if (!engaged) {
    return content;
  }
  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          onClose();
        }
      }}
    >
      <PopoverAnchor asChild>{content}</PopoverAnchor>
      <ComputedRefusal
        column={column}
        row={row}
        dependencies={dependencies}
        open={open}
        opening={opening}
      />
    </Popover>
  );
}
