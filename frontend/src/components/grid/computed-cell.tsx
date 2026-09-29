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
 * The cell is a button, which the pointer and the keyboard reach alike; the entry at the keyboard
 * (US-0120) will open the same refusal from the cell it lands on. Its popover mounts on the first
 * try only: a root of Radix in each computed cell would cost the hydration of the first screen as
 * many contexts, and the second of §4.6.2 counts it. The server is asked while the refusal is
 * open, once for each question — the row, its version, the field —: a page read anew asks
 * nothing of a closed refusal, nor again of a row in the same version. The refusal reads out, in
 * one live region, that it is reading, then what the server said.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import { Sigma } from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode, useEffect, useId, useState } from "react";

import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

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

/** The cell as a button: the whole of it, the mark at its start and the value at its end. */
const TRIGGER =
  "flex w-full min-w-0 items-center justify-between gap-0.5 rounded-sm text-inherit outline-none focus-visible:ring-[3px] focus-visible:ring-ring";

/** The API out of reach: the server action itself did not answer — the network is down. */
const UNREACHABLE: Outcome<ComputedDependencies> = { kind: "unreachable" };

/**
 * Ask the server what the value of a field of a row depends on, while the refusal is open and
 * has no answer to this question — the identity of the row, its version, the field —:
 * `undefined` until it answers. The answer is kept for the question it answers: a row read anew
 * in the same version is not asked again, and one in another version is asked afresh, the answer
 * before never shown for it. An answer that comes once the question has changed, or the cell has
 * gone, is dropped.
 */
function useDependencies<Row>(
  dependencies: DependencyReader<Row> | undefined,
  row: Row,
  field: ComputedValueField,
  open: boolean,
) {
  const identity = dependencies?.identity(row);
  const id = identity?.id;
  const question =
    identity === undefined ? undefined : `${identity.id}@${String(identity.version)}/${field}`;
  const [answer, setAnswer] = useState<{
    readonly question: string;
    readonly outcome: Outcome<ComputedDependencies>;
  }>();
  const current = answer?.question === question ? answer?.outcome : undefined;
  const asking = open && current === undefined;
  useEffect(() => {
    if (!asking || dependencies === undefined || id === undefined || question === undefined) {
      return undefined;
    }
    let live = true;
    const answered = (outcome: Outcome<ComputedDependencies>) => {
      if (live) {
        setAnswer({ question, outcome });
      }
    };
    void dependencies.read(id, field).then(answered, () => {
      answered(UNREACHABLE);
    });
    return () => {
      live = false;
    };
  }, [asking, dependencies, id, field, question]);
  return { answer: current, reading: asking && question !== undefined };
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
}: ComputedRefusalProps<Row, Sort, Totals>) {
  const t = useTranslations("computedValue");
  const columns = useTranslations("grid.columns");
  const title = useId();
  const { answer, reading } = useDependencies(dependencies, row, column.computed.field(row), open);
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

/** What a computed cell shows, and how it asks what its value depends on. */
export interface ComputedCellProps<Row, Sort extends string, Totals> {
  readonly column: ComputedColumn<Row, Sort, Totals>;
  /** The row of the cell. */
  readonly row: Row;
  /** How to ask the server what the value depends on, once an entry is tried. */
  readonly dependencies: DependencyReader<Row> | undefined;
  /** The value of the cell, formatted or rendered by its column. */
  readonly children: ReactNode;
}

/** Render a computed cell: its mark and its value, and the refusal of an entry once tried. */
export function ComputedCell<Row extends RowData, Sort extends string, Totals>({
  column,
  row,
  dependencies,
  children,
}: ComputedCellProps<Row, Sort, Totals>) {
  const t = useTranslations("grid");
  // Engaged at the first try, and for as long as the row is rendered: the trigger stays the same
  // element from then on, which the focus comes back to once the popover closes.
  const [engaged, setEngaged] = useState(false);
  const [open, setOpen] = useState(false);
  const content = (
    <>
      <Sigma role="img" aria-label={t("computed")} className="size-3 shrink-0" />
      <span className="min-w-0 truncate">{children}</span>
    </>
  );
  if (!engaged) {
    return (
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded="false"
        className={TRIGGER}
        onClick={() => {
          setEngaged(true);
          setOpen(true);
        }}
      >
        {content}
      </button>
    );
  }
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger className={TRIGGER}>{content}</PopoverTrigger>
      <ComputedRefusal column={column} row={row} dependencies={dependencies} open={open} />
    </Popover>
  );
}
