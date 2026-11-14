// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a cell of a dense grid shows: the number of the row, the label with its tree, what its column
 * renders, or its value.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import type { ReactNode } from "react";

import { cn } from "@/components/ui/utils";
import type { Locale } from "@/i18n/locale";

import { formatCell, type GridColumn, type GridConfig } from "./columns";
import { FoldToggle } from "./fold";

/** How far a level of the tree indents its label, in pixels. */
const INDENT = 16;

/** The label of a row and its tree: indented by its level, the icon of its nature before it. */
function TreeLabel<Row extends RowData, Sort extends string, Totals>({
  config,
  row,
  text,
}: {
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly row: Row;
  readonly text: string;
}) {
  const tree = config.tree;
  if (tree === undefined) {
    return text;
  }
  const emphasis = tree.emphasis?.(row);
  return (
    <span
      className={cn(
        "flex min-w-0 items-center gap-1.5",
        emphasis === "strong" ? "font-semibold" : null,
        emphasis === "muted" ? "text-muted-foreground" : null,
      )}
      style={{ paddingLeft: (tree.level(row) - 1) * INDENT }}
    >
      <FoldToggle rowKey={config.rowKey(row)} placeholder />
      {tree.nature(row)}
      <span className="truncate">{text}</span>
    </span>
  );
}

/**
 * The content of a cell: the number of the row, the label and its tree, what its column renders,
 * or its value.
 */
export function cellContent<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  column: GridColumn<Row, Sort, Totals> | undefined,
  row: Row,
  locale: Locale,
  currency: string | undefined,
): ReactNode {
  if (column === undefined) {
    return config.rowNumber?.(row);
  }
  if (column.render !== undefined) {
    return column.render(row);
  }
  const text = formatCell(column.format, column.value(row), locale, currency);
  return column === config.columns[0] ? <TreeLabel config={config} row={row} text={text} /> : text;
}
