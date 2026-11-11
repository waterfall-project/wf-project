// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of a flat table, folded into its bar (WF-IHM-0020, WF-IHM-0060, #2916): the button
 * « Filtres (n) », which opens and closes the panel the screen gives — its filters as they are —,
 * the panel itself, and under the bar the chips of the filters on, each lifted by its cross, and
 * « Effacer les filtres ». The panel stays in the page when closed, hidden, so that what a filter
 * holds of an entry is not lost; whether it is open is kept with the settings of the grid
 * (`filters_open`). A chip lifted changes the address only, back to the first page: the server
 * filters (WF-ARC-0020). The search is a field of the bar and not a chip, and clearing the filters
 * leaves it.
 */
"use client";

import { ChevronDown, ChevronUp, ListFilter, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { usePathname } from "next/navigation";
import { type ReactNode, useId, useTransition } from "react";

import { Button } from "@/components/ui/button";

import { type FilterChip, liftedHref } from "./filter-chips";
import { usePendingAddress } from "./pending-address";
import { CONTRACT_ADDRESS, type GridAddress } from "./query";

/** What the bar of a flat table offers of its filters. */
export interface BarFilters {
  /** The filters of the screen, in the panel. */
  readonly panel: ReactNode;
  /** The filters on, as the address says them. */
  readonly chips: readonly FilterChip[];
  /** Whether the panel is open. */
  readonly open: boolean;
  readonly onOpen: (open: boolean) => void;
  /** The parameter of the page of the list the server pages, which lifting a filter takes back to its first. */
  readonly page: string | undefined;
}

/** What a screen gives the bar of its table to fold its filters. */
export type Filtering = Pick<BarFilters, "panel" | "chips">;

/** What the bar is given of the filters of its screen, once the panel's state is known. */
export function barFilters(
  filtering: Filtering | undefined,
  state: Pick<BarFilters, "open" | "onOpen">,
  address: GridAddress | undefined,
): BarFilters | undefined {
  return filtering === undefined
    ? undefined
    : { ...filtering, ...state, page: (address ?? CONTRACT_ADDRESS).offset };
}

/** What moves the top of the frame under the bar, to measure the room below again. */
export function panelLayout(
  filtering: Filtering | undefined,
  open: boolean | undefined,
): string | undefined {
  return filtering === undefined ? undefined : `${String(open)}:${String(filtering.chips.length)}`;
}

/** The identifier of the panel the button controls, from that of the bar. */
export function usePanelId(): string {
  return `${useId()}-filters`;
}

/** The button that opens and closes the panel of the filters, with how many are on. */
export function FiltersButton({
  count,
  open,
  panel,
  onOpen,
}: {
  readonly count: number;
  readonly open: boolean;
  /** The identifier of the panel it controls. */
  readonly panel: string;
  readonly onOpen: (open: boolean) => void;
}) {
  const t = useTranslations("grid.filtering");
  const Chevron = open ? ChevronUp : ChevronDown;
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      aria-expanded={open}
      aria-controls={panel}
      aria-label={t("open", { count })}
      className="h-7 text-xs"
      onClick={() => {
        onOpen(!open);
      }}
    >
      <ListFilter aria-hidden="true" />
      {t("panel")}
      {count === 0 ? null : (
        <span
          aria-hidden="true"
          className="min-w-4 rounded-full bg-primary px-1 text-center text-[0.7rem] leading-4 text-primary-foreground"
        >
          {count}
        </span>
      )}
      <Chevron aria-hidden="true" />
    </Button>
  );
}

/** The panel of the filters: hidden when closed, the filters of the screen in a bordered box. */
export function FilterPanel({
  id,
  open,
  children,
}: {
  readonly id: string;
  readonly open: boolean;
  readonly children: ReactNode;
}) {
  const t = useTranslations("grid.filtering");
  return (
    <div id={id} hidden={!open}>
      <div
        role="group"
        aria-label={t("panel")}
        className="rounded-md border bg-muted/40 p-3 text-sm"
      >
        {children}
      </div>
    </div>
  );
}

/** The chips of the filters on, each lifted by its cross, and the button that lifts them all. */
export function FilterChips({
  chips,
  page,
}: {
  readonly chips: readonly FilterChip[];
  readonly page: string | undefined;
}) {
  const t = useTranslations("grid.filtering");
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const [, startTransition] = useTransition();
  if (chips.length === 0) {
    return null;
  }
  const lift = (lifted: readonly FilterChip[]) => {
    startTransition(() => {
      request((query) => liftedHref(pathname, query, lifted, page));
    });
  };
  return (
    <div className="flex flex-wrap items-center gap-2">
      <ul aria-label={t("active")} className="flex flex-wrap items-center gap-2">
        {chips.map((chip) => (
          <li
            key={chip.key}
            className="inline-flex items-center gap-1 rounded-full border bg-muted py-0.5 pr-0.5 pl-2.5 text-xs"
          >
            <span>{t("chip", { name: chip.name, value: chip.value })}</span>
            <button
              type="button"
              aria-label={t("remove", { name: chip.name, value: chip.value })}
              className="inline-flex size-5 items-center justify-center rounded-full hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              onClick={() => {
                lift([chip]);
              }}
            >
              <X aria-hidden="true" className="size-3" />
            </button>
          </li>
        ))}
      </ul>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-7 text-xs"
        onClick={() => {
          lift(chips);
        }}
      >
        {t("clear")}
      </Button>
    </div>
  );
}

/** Whether the account keeps the panel of the filters of a grid open, if it set it. */
export function keptOpenOf(
  preferences: { readonly filters_open?: boolean } | undefined,
): boolean | undefined {
  return preferences?.filters_open;
}
