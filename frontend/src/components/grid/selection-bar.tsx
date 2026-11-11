// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The bar of the actions on a selection, above a dense grid as soon as a row is selected (#2916/L4):
 * how many rows are selected — in the words of the screen where it gives them, « 3 comptes
 * sélectionnés » —, the commands the screen gives for those rows, and « Annuler la sélection ». A
 * group named, dark, as wide as the bar of the grid and as high, which it covers from the start of
 * the grid: it takes no room of its own, so that the rows do not move when the first row is selected
 * (the bar of the grid is hidden and inert meanwhile, `GridToolbar.covered`).
 */
"use client";

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode, useMemo } from "react";

import { Button } from "@/components/ui/button";

import type { GridConfig } from "./columns";

/** What a screen gives the bar of the actions on a selection. */
export interface SelectionBarOptions<Row> {
  /** How the selection is counted, in the words of the screen; none, « n lignes sélectionnées ». */
  readonly label?: ((count: number) => string) | undefined;
  /** The commands on the rows selected, in the bar after the count; none, only « Annuler ». */
  readonly commands?: ((rows: readonly Row[]) => ReactNode) | undefined;
}

/**
 * The configuration of a grid that is selected, and how: a flat table (no tree) picks its rows one
 * by one, and has handles — numbered by the place of the row among those shown where its
 * configuration gives no number; a tree keeps what it has.
 */
export function useSelectedConfig<Row, Sort extends string, Totals>(
  given: GridConfig<Row, Sort, Totals>,
  selecting: SelectionBarOptions<Row> | undefined,
) {
  const pick = selecting !== undefined && given.tree === undefined;
  const handles = pick && given.rowNumber === undefined;
  const config = useMemo(() => (handles ? { ...given, handles } : given), [given, handles]);
  return { config, pick };
}

/** Whether the bar of a selection is shown: the screen gives one, and a row is selected. */
export function isBarOpen<Row>(
  options: SelectionBarOptions<Row> | undefined,
  rows: readonly Row[],
): boolean {
  return options !== undefined && rows.length > 0;
}

/** Render the bar of a selection of `rows`, nothing while none is selected. */
export function SelectionBar<Row>({
  rows,
  options,
  width,
  onClear,
}: {
  readonly rows: readonly Row[];
  /** What the screen gives the bar; none, and the grid has no bar. */
  readonly options: SelectionBarOptions<Row> | undefined;
  /** The width of the bar above, as a CSS length. */
  readonly width: string;
  readonly onClear: () => void;
}) {
  const t = useTranslations("grid.selection");
  if (rows.length === 0 || options === undefined) {
    return null;
  }
  return (
    <div
      role="group"
      aria-label={t("bar")}
      className="absolute top-0 left-0 flex h-7 min-w-min max-w-full items-center gap-2 rounded-md bg-foreground px-3 py-1 text-xs text-background"
      style={{ width }}
    >
      <span className="font-medium">
        {options.label === undefined
          ? t("barCount", { count: rows.length })
          : options.label(rows.length)}
      </span>
      {options.commands?.(rows)}
      <div className="flex-1" />
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onClear}
        className="h-6 text-xs text-background hover:bg-background/15 hover:text-background"
      >
        <X aria-hidden="true" />
        {t("clear")}
      </Button>
    </div>
  );
}
