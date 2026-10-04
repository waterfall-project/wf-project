// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The bar above a dense grid: the search on the labels, asked of the server when entered — the
 * grid shows what it retains, and the totals of what it retains —, and the choice of the
 * columns shown, a menu whose entries stay open while several are set; for a grid that enters a
 * revision in progress, undo and redo, placed but not wired yet (`UndoCommands`).
 */
"use client";

import { Columns3, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";

import { SEARCH_LENGTH } from "./query";
import { UndoCommands } from "./undo-commands";

/** A column the user may show or hide. */
export interface ToggledColumn {
  readonly key: string;
  readonly label: string;
  readonly visible: boolean;
  readonly toggle: (visible: boolean) => void;
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
}

/** The search on the labels, sent when entered. */
function SearchField({
  search,
  onSearch,
}: {
  readonly search: string | undefined;
  readonly onSearch: (search: string) => void;
}) {
  const t = useTranslations("grid.search");
  const [text, setText] = useState(search ?? "");
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSearch(text);
  };
  return (
    <form role="search" aria-label={t("label")} onSubmit={submit} className="relative w-64">
      <Search
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground"
      />
      <Input
        type="search"
        value={text}
        maxLength={SEARCH_LENGTH}
        aria-label={t("label")}
        placeholder={t("placeholder")}
        onChange={(event) => {
          setText(event.target.value);
        }}
        className="h-7 pl-7 text-xs"
      />
    </form>
  );
}

/** Render the bar of a grid. */
export function GridToolbar({ columns, search, onSearch, undoable }: GridToolbarProps) {
  const t = useTranslations("grid.columnsMenu");
  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* A search the address changed — back in the history — sets the field anew. */}
      {onSearch === undefined ? null : (
        <SearchField key={search ?? ""} search={search} onSearch={onSearch} />
      )}
      <div className="flex-1" />
      {undoable === true ? <UndoCommands /> : null}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button type="button" variant="outline" size="sm" className="h-7 text-xs">
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
