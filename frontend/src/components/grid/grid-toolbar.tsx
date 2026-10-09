// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The bar above a dense grid: the search on the labels, asked of the server when entered — the
 * grid shows what it retains, and the totals of what it retains —, and the choice of the
 * columns shown, a menu whose entries stay open while several are set; for a grid that enters a
 * revision in progress, undo and redo, placed but not wired yet (`UndoCommands`); for a tree, the
 * menu that unfolds it whole, folds it whole, or folds it down to a level, as the « Afficher » of
 * Microsoft Project (`fold.tsx`).
 */
"use client";

import { Columns3, ListTree, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import type { SubmitEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";

import { useDatedEntry } from "./dated-entry";
import { useFoldReach } from "./fold";
import { SEARCH_LENGTH } from "./query";
import { UndoCommands } from "./undo-commands";

/** A column the user may show or hide. */
export interface ToggledColumn {
  readonly key: string;
  readonly label: string;
  readonly visible: boolean;
  readonly toggle: (visible: boolean) => void;
}

/** How the bar folds the tree of a grid. */
export interface GridOutline {
  /** The deepest level of a row that folds: the tree is folded down to each level up to it. */
  readonly levels: number;
  readonly expandAll: () => void;
  /** Fold the tree to show it down to a level — the first, folded whole. */
  readonly collapseTo: (level: number) => void;
}

/** What the bar of a grid offers. */
export interface GridToolbarProps {
  /** The columns the user may hide, in the order of the grid. */
  readonly columns: readonly ToggledColumn[];
  /** The search the address holds. */
  readonly search: string | undefined;
  /**
   * Ask the server for the rows a search retains — all of them, for an empty one; none for a grid
   * the server does not search, and the bar offers no search.
   */
  readonly onSearch: ((search: string) => void) | undefined;
  /** Whether the grid enters a revision in progress, whose entries undo and redo will act on. */
  readonly undoable: boolean | undefined;
  /** How the tree of the grid folds; none for a grid that is no tree. */
  readonly outline?: GridOutline | undefined;
  /**
   * The name of the grid, which names its search and its menu of the columns, for a grid among
   * several on its screen — three searches of the same name would not be told apart —; none for a
   * grid alone.
   */
  readonly grid?: string | undefined;
}

/**
 * The search on the labels, sent when entered. An entry is dated by the search of the address
 * (`useDatedEntry`): a search the address changes — back in the history — shows anew, what was
 * typed and not sent given up, what was typed on while the search sent was on its way kept, and the
 * field keeps the focus once the search it sent arrives.
 */
function SearchField({
  search,
  onSearch,
  grid,
}: {
  readonly search: string | undefined;
  readonly onSearch: (search: string) => void;
  readonly grid: string | undefined;
}) {
  const t = useTranslations("grid.search");
  const label = grid === undefined ? t("label") : t("labelIn", { grid });
  const { entered, enter, sent } = useDatedEntry<"text">(search ?? "");
  const text = entered.text ?? search ?? "";
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    // Sent, the search arrives as the address writes it: only what is typed on after it stays.
    sent();
    onSearch(text);
  };
  return (
    <form role="search" aria-label={label} onSubmit={submit} className="relative w-64">
      <Search
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground"
      />
      <Input
        type="search"
        value={text}
        maxLength={SEARCH_LENGTH}
        aria-label={label}
        placeholder={t("placeholder")}
        onChange={(event) => {
          enter("text", event.target.value);
        }}
        className="h-7 pl-7 text-xs"
      />
    </form>
  );
}

/**
 * The menu that folds a tree: unfolded whole — as Alt+* does —, folded whole, or down to
 * each level that has rows to fold.
 */
function OutlineMenu({ outline }: { readonly outline: GridOutline }) {
  const t = useTranslations("grid.fold");
  // Alt and * off a Mac alone, where Option types no * (`useFoldReach`).
  const reach = useFoldReach();
  const levels = Array.from({ length: Math.max(outline.levels - 1, 0) }, (_, at) => at + 2);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="outline" size="sm" className="h-7 text-xs">
          <ListTree aria-hidden="true" />
          {t("open")}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>{t("title")}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={outline.expandAll}
          aria-keyshortcuts={reach === "all" ? "Alt+*" : undefined}
        >
          {t("expandAll")}
          {reach === "all" ? (
            <span aria-hidden="true" className="ml-auto text-xs text-muted-foreground">
              {t("expandAllKeys")}
            </span>
          ) : null}
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={() => {
            outline.collapseTo(1);
          }}
        >
          {t("collapseAll")}
        </DropdownMenuItem>
        {levels.map((level) => (
          <DropdownMenuItem
            key={level}
            onSelect={() => {
              outline.collapseTo(level);
            }}
          >
            {t("level", { level })}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Render the bar of a grid. */
export function GridToolbar({
  columns,
  search,
  onSearch,
  undoable,
  outline,
  grid,
}: GridToolbarProps) {
  const t = useTranslations("grid.columnsMenu");
  return (
    <div className="flex flex-wrap items-center gap-2">
      {onSearch === undefined ? null : (
        <SearchField search={search} onSearch={onSearch} grid={grid} />
      )}
      <div className="flex-1" />
      {undoable === true ? <UndoCommands /> : null}
      {outline === undefined ? null : <OutlineMenu outline={outline} />}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-label={grid === undefined ? undefined : t("openIn", { grid })}
            className="h-7 text-xs"
          >
            <Columns3 aria-hidden="true" />
            {t("open")}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>{t("title")}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {columns.map((column) => (
            <DropdownMenuCheckboxItem
              key={column.key}
              checked={column.visible}
              onCheckedChange={column.toggle}
              onSelect={(event) => {
                event.preventDefault();
              }}
            >
              {column.label}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
