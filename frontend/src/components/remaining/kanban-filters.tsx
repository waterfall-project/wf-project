// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters above the Kanban of the start of the tasks (US-0730): a field that searches the label
 * of the tasks in the three columns, and the box « Tâches prêtes » that keeps, among the tasks not
 * started, those whose predecessors are all completed. Both only write the address (`q`, `ready`,
 * `address.ts`) by replacing the entry of the history, as the search of the grids does — they live
 * in the address alone, in no preference nor session —, and the Kanban shows the cards that
 * match. The text is sent when entered, lifted when emptied; an entry is dated by the text the
 * address holds (`useDatedEntry`), so that the history brings it back without remounting the field;
 * the box shows its press until the server answers for it (défaut n° 21 de `typescript.md`).
 */
"use client";

import { Search } from "lucide-react";
import { usePathname } from "next/navigation";
import { type SubmitEvent, useId, useOptimistic, useTransition } from "react";
import { useTranslations } from "next-intl";

import { useDatedEntry } from "@/components/grid/dated-entry";
import { PendingAddress, usePendingAddress } from "@/components/grid/pending-address";
import { SEARCH_LENGTH } from "@/components/grid/query";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { type KanbanFilters, kanbanFilterHref } from "./address";

/** The search of the label, and the box of the tasks ready, over the address last asked. */
function Filters({ filters }: { readonly filters: KanbanFilters }) {
  const t = useTranslations("kanban.filters");
  const id = useId();
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const { entered, enter, sent } = useDatedEntry<"text">(filters.text);
  const text = entered.text ?? filters.text;
  const [ready, showReady] = useOptimistic(filters.ready);
  const [, startTransition] = useTransition();
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    // Sent, the text arrives as the address writes it: only what is typed on after it stays.
    sent();
    request((query) => kanbanFilterHref(pathname, query, { text: text.trim() }), "replace");
  };
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
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
            enter("text", event.target.value);
          }}
          className="h-7 pl-7 text-xs"
        />
      </form>
      <div className="flex items-center gap-2 text-sm">
        <Checkbox
          id={id}
          checked={ready}
          onCheckedChange={(checked) => {
            startTransition(() => {
              showReady(checked === true);
              request(
                (query) => kanbanFilterHref(pathname, query, { ready: checked === true }),
                "replace",
              );
            });
          }}
        />
        <Label htmlFor={id}>{t("ready")}</Label>
      </div>
    </div>
  );
}

/** Render the filters of the Kanban, sharing the address last asked with their screen. */
export function KanbanFilterBar({ filters }: { readonly filters: KanbanFilters }) {
  return (
    <PendingAddress>
      <Filters filters={filters} />
    </PendingAddress>
  );
}
