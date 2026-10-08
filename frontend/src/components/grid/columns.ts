// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of a dense grid (EP-02, « Composants partagés »): one component, and for
 * each screen — planning, estimate, remaining to commit, risks, actual costs, rates — the
 * columns it shows and the key under which the account keeps its settings. A column says what
 * it reads of a row, how its value shows, where it aligns, how wide it starts, which of its
 * cells the server computes, and by which column of the contract the server sorts it; the totals row
 * reads the totals of the answer, never a sum of the rows (WF-ARC-0020).
 *
 * Neither server nor client: the page reads the sortable columns of a configuration to check
 * the address, the grid the rest. Its functions stay on the side of the browser, which is why
 * a screen hands its configuration to the grid in a client component of its own.
 */
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import type { Catalogue } from "@/i18n/catalogues";
import { formatDecimal, formatMoney, formatPercent, formatPlanningDate } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

/**
 * How the value of a cell shows, from the exact string of the contract: as it is (`text`), an
 * amount (`money`), a decimal — hours, a quantity (`decimal`) —, a ratio as a percentage
 * (`percent`), a date of planning (`date`).
 */
export type CellFormat = "text" | "money" | "decimal" | "percent" | "date";

/**
 * Where the content of a cell aligns: the start for a text, the end for a figure, the centre
 * for an icon alone.
 */
export type CellAlign = "start" | "end" | "center";

/** The key of the heading of a column in the catalogue, under `grid.columns`. */
export type ColumnLabel = keyof Catalogue["grid"]["columns"];

/** The key of the accessible name of a grid in the catalogue, under `grid.names`. */
export type GridName = keyof Catalogue["grid"]["names"];

/** The value of a cell as the contract gives it, or none. */
export type CellValue = string | null | undefined;

/** A column of a grid of rows `Row`, sorted by a column `Sort` of the contract. */
export interface GridColumn<Row, Sort extends string, Totals> {
  /** The key of the column: stable, for it names the column in the settings of the account. */
  readonly key: string;
  readonly label: ColumnLabel;
  /**
   * A heading the answer gives — the year of a column of rates —, shown as it is in place of the
   * heading of its label, which then says what the column holds.
   */
  readonly heading?: string;
  readonly format: CellFormat;
  /** Where the column aligns; by default, as its format does. */
  readonly align?: CellAlign;
  /** Its width before the user sets one, in pixels. */
  readonly width: number;
  /**
   * The icon its header shows in place of its heading, which names it: a narrow column whose
   * cells are icons too. The menu of the columns names it by its heading all the same.
   */
  readonly icon?: LucideIcon;
  /**
   * Which of its cells the server computes, and the field of the contract each shows, which the
   * refusal of an entry asks the server about: none, and every cell holds what was entered.
   */
  readonly computed?: ComputedCells<Row>;
  /** How its cells are entered from the keyboard (WF-IHM-0040); none, and no cell of it is. */
  readonly entry?: CellEntry<Row, Totals> | undefined;
  /**
   * The identifying column: it stays at the start when the grid scrolls sideways, and cannot
   * be hidden. The first of them carries the tree, when the grid has one.
   */
  readonly pinned?: boolean;
  /** The column of the contract the server sorts it by; none, and it does not sort. */
  readonly sortBy?: Sort;
  /**
   * What it reads of a row: the value its cell formats — or, for a column that renders its cell,
   * only what TanStack Table asks of a column to offer its sort, never shown nor sorted here.
   */
  readonly value: (row: Row) => CellValue;
  /**
   * What its cell shows in place of the value formatted: an icon named for what it says, a
   * figure with its unit or its mark — rendered in the browser, as the rest of the grid. Its
   * `value` then serves the sort offered alone.
   */
  readonly render?: (row: Row) => ReactNode;
  /** What it reads of the totals of the answer, for the totals row; none, and it is blank. */
  readonly total?: (totals: Totals) => CellValue;
  /**
   * What its header draws in place of its heading, at the width of the column — the axis of time
   * of the Gantt —; its heading then names it to the readers of the screen alone.
   */
  readonly axis?: (width: number) => ReactNode;
}

/** A field whose value the server computes, as the contract names it: `task.finish`. */
export type ComputedValueField = components["schemas"]["ComputedValueField"];

/**
 * What a computed value depends on (WF-IHM-0030), as the server says it: the rules that compute
 * it, and the rows it is drawn from, named by their number and their label.
 */
export type ComputedDependencies = components["schemas"]["ComputedValueDependencies"];

/** A rule that computes a value, as the contract names it: `subordinates`, `own_estimate`. */
export type ComputedDependency = components["schemas"]["ComputedDependency"];

/**
 * How a grid asks the server what the value of a field of a row depends on, once an entry is
 * tried on it: the refusal names it. One reader for each reading of the page: what a value depends
 * on names other rows, whose numbers and labels a new reading may change, so that an answer is
 * kept for the reader that asked it, never beyond. The question is then the identifier of the
 * row and the field, and a server action answers it, decoded as every other (`Outcome`).
 */
export interface DependencyReader<Row> {
  /**
   * The reading of the page this reader asks for — its rows —: an answer is kept for it alone. A
   * function, never the array: the reader reaches the props of each row and each computed cell,
   * which the development build of React compares again at each navigation of the grid.
   */
  readonly reading: () => readonly Row[];
  /** The identifier of a row, as the server knows it. */
  readonly id: (row: Row) => string;
  readonly read: (id: string, field: ComputedValueField) => Promise<Outcome<ComputedDependencies>>;
}

/**
 * The cells of a column the server computes (WF-IHM-0030), row by row: a computed cell is shaded
 * and marked Σ, named, never entered, and says what its value depends on when one tries — what
 * the server answers for its field, never a rule read here.
 */
export interface ComputedCells<Row> {
  /** Whether the server computes the whole column — a field no entry writes —: Σ in its header. */
  readonly whole: boolean;
  /** Whether the server computes the cell of a row. */
  readonly in: (row: Row) => boolean;
  /**
   * The field of a node of the contract the cell of a row shows, which the refusal asks the server
   * about (`getComputedValueDependencies`); none for a value the row says itself what it depends
   * on (`dependsOn`).
   */
  readonly field: (row: Row) => ComputedValueField | undefined;
  /**
   * What the value of the cell of a row depends on, as the row itself says it — a risk names the
   * rules of its severity and its provision (`Risk.computed_fields`) —: the refusal names them
   * without asking the server. None where the refusal asks it.
   */
  readonly dependsOn?: (row: Row) => readonly ComputedDependency[] | undefined;
}

/**
 * A choice of the reference data: the identifier the contract writes, the name the grid shows,
 * and whether it may still be chosen — a deactivated one stays readable (WF-REF-0150).
 */
export interface Choice {
  readonly id: string;
  readonly label: string;
  readonly active: boolean;
  /** The code that names it before its label in a list — a sub-project's —, if it has one. */
  readonly code?: string | undefined;
}

/**
 * What a cell takes (WF-IHM-0040): a text, never blank, of `maxLength` characters at most, as the
 * contract bounds it; a number in the format of the language, which travels as the exact decimal
 * of the contract — an amount keeps two decimals at most —; a whole number, of digits alone, as
 * the contract takes an integer — a number of days —; one of the choices of a list. A cell that
 * may be emptied (`nullable`) writes `null` then.
 */
export type EntryKind =
  | { readonly type: "text"; readonly maxLength: number }
  | { readonly type: "decimal" | "money" | "integer"; readonly nullable: boolean }
  | {
      readonly type: "choice";
      /** The choices, read by the entry alone: a function, never the list (défaut n° 14). */
      readonly choices: () => readonly Choice[];
      readonly nullable: boolean;
    };

/**
 * A part of a row a write changed without writing it nor answering it whole — the schedule of a
 * task it rescheduled —, by the key of the row: the row with that part as it now is, from the row
 * shown.
 */
export interface RowPart<Row> {
  readonly key: string;
  readonly change: (row: Row) => Row;
}

/**
 * What the server answers a write of a grid with, as the grid reads it (#218): the rows written,
 * as they now are; the other rows the write changed, whole — the summaries above them
 * recalculated —, or in part — the tasks it rescheduled —; the totals of the reading as the write
 * left them; and the place of the write among those of the rows. The grid shows each of them in
 * place of what it showed, never a sum nor a date of its own (WF-ARC-0020).
 */
export interface RowsWritten<Row, Totals> {
  readonly rows: readonly Row[];
  readonly changed: readonly Row[];
  readonly parts: readonly RowPart<Row>[];
  /**
   * The totals of the reading after the write; none when those the server answers are not the
   * reading's — a filtered reading keeps its own.
   */
  readonly totals: Totals | undefined;
  /**
   * The place of the write among those of the rows: a later write answers a greater one. Writes
   * of different rows leave together, and an answer may come back after a later one: a row or
   * totals a later write answered are never taken back to an earlier one (`answers.ts`).
   */
  readonly order: number;
}

/**
 * How the cells of a column are entered, row by row: which take an entry, what an entry starts
 * from, and how a value validated is written — each cell alone, the server answering the row as
 * it now is, which the grid shows in place of what was typed, with the other rows and the totals
 * the write changed.
 */
export interface CellEntry<Row, Totals = unknown> {
  readonly kind: EntryKind;
  /**
   * Whether the cell of a row takes an entry: the row accepts its field, and the server does not
   * compute it here — a computed cell is traversed, and refuses the entry.
   */
  readonly in: (row: Row) => boolean;
  /** The value of the contract an entry starts from: the text, the decimal, the identifier. */
  readonly value: (row: Row) => CellValue;
  /** Write a value validated, `null` for a cell emptied, and give what the server answers. */
  readonly write: (row: Row, value: string | null) => Promise<Outcome<RowsWritten<Row, Totals>>>;
}

/** A block of cells pasted from a spreadsheet: its rows, each the texts of its cells, as copied. */
export type PastedBlock = readonly (readonly string[])[];

/** What the server would write and refuse of a block pasted (WF-IHM-0050). */
export type PastePlan = components["schemas"]["PastePlan"];

/**
 * How a block pasted from a spreadsheet is written in a grid, in two steps (WF-IHM-0050): the
 * server says what it would write and refuse — nothing is written yet —, then applies the plan
 * once the user confirmed it, in one operation. The grid judges nothing of what is pasted.
 */
export interface GridPaste<Row, Sort extends string = string, Totals = unknown> {
  /** Ask the plan of a block pasted from the cell of a row, in a column, named as the server sorts by it. */
  readonly preview: (row: Row, column: Sort, block: PastedBlock) => Promise<Outcome<PastePlan>>;
  /** Apply a plan confirmed: what the server wrote, as the grid reads it. */
  readonly apply: (plan: PastePlan) => Promise<Outcome<RowsWritten<Row, Totals>>>;
  /**
   * The columns a block pasted on the cell of a row fills, from its column, in the order the
   * server fills them — those of the contract, whether the grid shows them or not (#223) —; none
   * when the contract does not say, and the server alone judges the block.
   */
  readonly span: (row: Row, column: Sort) => readonly Sort[] | undefined;
  /** The name of a column of the contract the grid has none for, in the language of the interface. */
  readonly name: (column: Sort) => string;
}

/** The tree of a grid: the depth of a row, the icon of its nature, how its label stands out. */
export interface GridTree<Row> {
  /** The depth of a row, `1` at the root, as the API computes it. */
  readonly level: (row: Row) => number;
  /** The icon of the nature of the row, named for it. */
  readonly nature: (row: Row) => ReactNode;
  /** Whether its label is set in bold — a summary — or muted — what nobody enters. */
  readonly emphasis?: (row: Row) => "strong" | "muted" | undefined;
  /**
   * The identity of the row a row is under, as the API gives it — none at the root —: given, the
   * tree folds and unfolds, a row under which the answer holds others folding them (`fold.tsx`).
   */
  readonly parent?: (row: Row) => string | null;
}

/** A grid: its columns, its rows and how to tell them apart, its tree if it has one. */
export interface GridConfig<Row, Sort extends string, Totals> {
  /** The key of its settings in the account (`DisplayPreferences.grids`): stable. */
  readonly key: string;
  readonly name: GridName;
  /** The identity of a row, stable from one answer to the next. */
  readonly rowKey: (row: Row) => string;
  /**
   * Whether the server searches the rows on their labels, which the bar of the grid then offers:
   * an operation without `search` — the actual costs — offers none.
   */
  readonly searched: boolean;
  /** The number of a row, shown first and pinned, as the API computes it; none, no column. */
  readonly rowNumber?: (row: Row) => number;
  readonly tree?: GridTree<Row>;
  readonly columns: readonly GridColumn<Row, Sort, Totals>[];
  /** How a block pasted from a spreadsheet is written; none, and the grid takes no paste. */
  readonly paste?: GridPaste<Row, Sort, Totals> | undefined;
  /**
   * How the totals of the reading are read anew once its writes answered, for a reading whose
   * totals the writes do not answer — narrowed by a search or a filter (#218); none, and the
   * totals are those the writes answer.
   */
  readonly retotal?: (() => Promise<Outcome<Totals>>) | undefined;
}

/** The key of the column of row numbers, which no configuration may take. */
export const ROW_NUMBER_KEY = "row_number";

/** The narrowest a column gets: the contract keeps no width under 20. */
export const MIN_WIDTH = 40;

/** The widest a column gets. */
export const MAX_WIDTH = 800;

/** What names a column: its label in the catalogue, and the heading the answer gives it, if any. */
export interface ColumnName {
  readonly label: ColumnLabel;
  readonly heading?: string;
}

/** The heading of a column: the one the answer gives it, or that of its label in the catalogue. */
export function headingOf(column: ColumnName, translate: (label: ColumnLabel) => string): string {
  return column.heading ?? translate(column.label);
}

/** Where a column aligns. */
export function alignment(column: { readonly format: CellFormat; readonly align?: CellAlign }) {
  return column.align ?? (column.format === "text" ? "start" : "end");
}

/**
 * Show the value of a cell in a language, from the exact string of the contract: nothing for
 * none, a text as it is, a figure by the formats of the interface — never through a float.
 */
export function formatCell(format: CellFormat, value: CellValue, locale: Locale): string {
  if (value === null || value === undefined) {
    return "";
  }
  switch (format) {
    case "money":
      return formatMoney(value, locale);
    case "decimal":
      return formatDecimal(value, locale);
    case "percent":
      return formatPercent(value, locale);
    case "date":
      // A dense grid shows a date in its short form, the same width on every row; the year keeps
      // its four digits, clearer over the fifteen years a project may span than the mock-up's two.
      return formatPlanningDate(value, locale, "short");
    case "text":
      return value;
  }
}

/** The columns of a configuration the server sorts, by the column of the contract. */
export function sortColumns<Sort extends string>(config: {
  readonly columns: readonly { readonly sortBy?: Sort }[];
}): readonly Sort[] {
  return config.columns.flatMap((column) => (column.sortBy === undefined ? [] : [column.sortBy]));
}
