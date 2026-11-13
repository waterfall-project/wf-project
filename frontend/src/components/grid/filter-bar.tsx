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
import { usePathname, useSearchParams } from "next/navigation";
import {
  type ReactNode,
  type Ref,
  type RefObject,
  useEffect,
  useId,
  useRef,
  useTransition,
} from "react";

import { Button } from "@/components/ui/button";

import { type FilterChip, liftedHref, liftedInstead, liftedParams } from "./filter-chips";
import { type Asked, usePendingAddress } from "./pending-address";
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
  /**
   * Every parameter of the address the grid reads as a filter, its search apart: clearing the
   * filters lifts them all, those the reading set aside — a value the contract would refuse —
   * besides those of the chips.
   */
  readonly every: readonly string[];
}

/** What a screen gives the bar of its table to fold its filters. */
export type Filtering = Pick<BarFilters, "panel" | "chips">;

/** What the bar is given of the filters of its screen, once the panel's state is known. */
export function barFilters(
  filtering: Filtering | undefined,
  state: Pick<BarFilters, "open" | "onOpen">,
  address: GridAddress | undefined,
  names: readonly string[] | undefined,
): BarFilters | undefined {
  const named = address ?? CONTRACT_ADDRESS;
  return filtering === undefined
    ? undefined
    : {
        ...filtering,
        ...state,
        page: named.offset,
        every: (names ?? []).filter((name) => name !== named.search),
      };
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
  ref,
}: {
  readonly ref?: Ref<HTMLButtonElement>;
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
      ref={ref}
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
      {/* What is seen, « Filtres (3) », is the name: axe's « label in name » (WCAG 2.5.3). */}
      {count === 0 ? null : (
        <>
          {" "}
          <span aria-hidden="true" className="font-semibold text-primary tabular-nums">
            {t("count", { count })}
          </span>
        </>
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

/**
 * What a lift leaves for the focus: the cross to take once the chips lifted are gone from the address —
 * the next one's, the previous one's for the last —, none for the button of the filters. The focus is
 * given in an effect on the chips the address holds, not at the click: the navigation shows them
 * later, and the cross lifted takes the focus with it (défaut n° 20). The navigation asked, and the
 * address it was asked from, tell one that never arrives: another address shown that still holds
 * the chips — Next dropped it, the history went elsewhere — forgets the lift (#2916).
 */
interface Lifted {
  readonly gone: readonly string[];
  readonly next: string | undefined;
  readonly from: string;
  readonly asked: Asked;
}

/**
 * The chips of the filters on, each lifted by its cross, and the button that lifts them all. A
 * chip lifted gives the focus to the cross of the next, or of the previous for the last; the last
 * one, or all of them, to the button of the filters (`toggle`).
 */
export function FilterChips({
  chips,
  page,
  every,
  toggle,
}: {
  readonly chips: readonly FilterChip[];
  readonly page: string | undefined;
  readonly every: readonly string[];
  readonly toggle: RefObject<HTMLButtonElement | null>;
}) {
  const t = useTranslations("grid.filtering");
  const pathname = usePathname();
  const shown = useSearchParams().toString();
  const { request, underWay } = usePendingAddress();
  const [, startTransition] = useTransition();
  const crosses = useRef(new Map<string, HTMLButtonElement>());
  const lifted = useRef<Lifted>(undefined);
  useEffect(() => {
    const waiting = lifted.current;
    if (waiting === undefined) {
      return;
    }
    if (waiting.gone.some((key) => chips.some((c) => c.key === key))) {
      // Another address than the one asked from, and none of the navigation asked: it will not
      // arrive, and nothing is left to give the focus for.
      if (shown !== waiting.from && !waiting.asked.streak.has(shown)) {
        lifted.current = undefined;
      }
      return;
    }
    lifted.current = undefined;
    // The chips gone from the address shown: the navigation arrived. Gone while the address stays
    // the one asked from, they went by another way, and the focus is left where it is.
    // The focus is moved only if it was lost with the cross: it stays where the user took it.
    if (
      shown !== waiting.from &&
      (document.activeElement === document.body || document.activeElement === null)
    ) {
      const next = waiting.next === undefined ? undefined : crosses.current.get(waiting.next);
      (next ?? toggle.current)?.focus();
    }
  }, [chips, shown, toggle]);
  if (chips.length === 0) {
    return null;
  }
  const lift = (gone: readonly FilterChip[], next: string | undefined, all: boolean) => {
    const params = all ? [...every, ...liftedParams(gone)] : liftedParams(gone);
    startTransition(() => {
      request((query) => liftedHref(pathname, query, params, page, liftedInstead(gone)));
      // An address that does not change is no navigation: nothing will arrive to give the focus for.
      const asked = underWay();
      lifted.current =
        asked === undefined
          ? undefined
          : { gone: gone.map((chip) => chip.key), next, from: shown, asked };
    });
  };
  return (
    <div className="flex flex-wrap items-center gap-2">
      <ul aria-label={t("active")} className="flex flex-wrap items-center gap-2">
        {chips.map((chip, at) => (
          <li
            key={chip.key}
            className="inline-flex items-center gap-1 rounded-full border bg-muted py-0.5 pr-0.5 pl-2.5 text-xs"
          >
            <span>{t("chip", { name: chip.name, value: chip.value })}</span>
            <button
              ref={(cross) => {
                if (cross === null) {
                  crosses.current.delete(chip.key);
                } else {
                  crosses.current.set(chip.key, cross);
                }
              }}
              type="button"
              aria-label={t("remove", { name: chip.name, value: chip.value })}
              className="inline-flex size-5 items-center justify-center rounded-full hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              onClick={() => {
                lift([chip], (chips[at + 1] ?? chips[at - 1])?.key, false);
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
          lift(chips, undefined, true);
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
