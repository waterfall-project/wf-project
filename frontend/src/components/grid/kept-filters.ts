// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of a grid kept as a display preference of the account, with its sort (WF-IHM-0060,
 * US-0380): its search and the parameters its screen filters it by (`GridConfig.filters`), each as
 * the address writes it, under `filters` in the settings of the grid. The address stays the truth
 * of the screen: the filters it shows are recorded once the page shows them, whenever they differ
 * from those the account keeps — lifted ones too, and a reading that filters nothing is kept as
 * such —, and those the account keeps are found again only on opening the screen at an address that
 * says nothing of the grid — neither its sort, nor its search, nor a filter —: the screen then
 * replaces it by the address of the filters kept, which the server reads. Within the screen, an
 * address that says nothing is a reading lifted, never one to fill in.
 */
"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type RefObject, useEffect, useRef } from "react";

import type { GridPreferences } from "./settings";

/** The filters of a reading, as the address writes them: each parameter, and its value. */
export type KeptFilters = Readonly<Record<string, string>>;

/** The filters of a reading the address carries, among the parameters named. */
export function filtersOf(query: URLSearchParams, names: readonly string[]): KeptFilters {
  return Object.fromEntries(
    names.flatMap((name) => {
      const value = query.get(name);
      return value === null ? [] : [[name, value]];
    }),
  );
}

/**
 * The filters an account keeps for a grid, among the parameters named — each a text, as the address
 * writes it —; none when it keeps none.
 */
export function keptFilters(
  preferences: GridPreferences | undefined,
  names: readonly string[],
): KeptFilters | undefined {
  const kept = preferences?.filters;
  if (kept === undefined) {
    return undefined;
  }
  return Object.fromEntries(
    names.flatMap((name) => {
      const value = kept[name];
      return typeof value === "string" ? [[name, value]] : [];
    }),
  );
}

/** Whether two readings filter alike. */
function same(one: KeptFilters, other: KeptFilters): boolean {
  const names = Object.keys(one);
  return (
    names.length === Object.keys(other).length && names.every((name) => one[name] === other[name])
  );
}

/** What the grid tells the kept filters: the parameters of its reading, and those of its sort. */
export interface KeptReading {
  /** The search and the filters of the grid, as the address names them. */
  readonly filters: readonly string[];
  /** The parameters of its sort, which an address that opens the screen may say alone. */
  readonly sort: readonly string[];
}

/**
 * Keep the filters of a grid with its settings: the filters the account keeps, found again when the
 * screen opens at an address that says nothing of the grid; and, each time the page shows filters
 * that differ from those kept, those recorded with the settings of the grid (`record`). A grid whose
 * screen keeps no filter gives none: nothing is read nor written.
 */
export function useKeptFilters(
  reading: KeptReading | undefined,
  preferences: GridPreferences | undefined,
  record: (filters: KeptFilters) => void,
): RefObject<KeptFilters | undefined> {
  const router = useRouter();
  const pathname = usePathname();
  const query = useSearchParams().toString();
  const names = reading?.filters;
  const kept = useRef(names === undefined ? undefined : (keptFilters(preferences, names) ?? {}));
  // The address the screen opened at and replaces by that of the filters kept: nothing is recorded
  // from it, until the screen shows another.
  const restoring = useRef<string>(undefined);
  const opened = useRef(false);
  useEffect(() => {
    if (reading === undefined || kept.current === undefined) {
      return;
    }
    const address = new URLSearchParams(query);
    if (!opened.current) {
      opened.current = true;
      const silent = [...reading.filters, ...reading.sort].every((name) => !address.has(name));
      if (silent && Object.keys(kept.current).length > 0) {
        restoring.current = query;
        const restored = new URLSearchParams(address);
        for (const [name, value] of Object.entries(kept.current)) {
          restored.set(name, value);
        }
        router.replace(`${pathname}?${restored.toString()}`, { scroll: false });
        return;
      }
    }
    if (restoring.current !== undefined) {
      if (restoring.current === query) {
        return;
      }
      restoring.current = undefined;
    }
    const shown = filtersOf(address, reading.filters);
    if (!same(shown, kept.current)) {
      kept.current = shown;
      record(shown);
    }
  }, [query, reading, pathname, router, record]);
  return kept;
}
