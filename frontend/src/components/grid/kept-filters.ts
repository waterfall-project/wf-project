// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The search and the filters of a grid kept with its settings (WF-IHM-0060, US-0380), under `filters`,
 * as the address writes them (`GridConfig.filters`). The address stays the truth: the filters the
 * page shows are recorded whenever they differ from those kept — lifted ones too —, and those kept
 * are found again only on opening the screen at an address that says nothing of the grid, which the
 * screen then replaces by theirs. Within the screen, an address that says nothing is a reading lifted.
 */
"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type RefObject, useEffect, useMemo, useRef } from "react";

import { CONTRACT_ADDRESS, type GridAddress } from "./query";
import type { GridPreferences } from "./settings";

/** The filters of a reading, as the address writes them: each parameter, and its value. */
export type KeptFilters = Readonly<Record<string, string>>;

/** The parameters named to which a source gives a text, each with its text. */
function picked(names: readonly string[], source: (name: string) => unknown): KeptFilters {
  return Object.fromEntries(
    names.flatMap((name) => {
      const value = source(name);
      return typeof value === "string" ? [[name, value]] : [];
    }),
  );
}

/** Whether two readings filter alike. */
function same(one: KeptFilters, other: KeptFilters): boolean {
  const names = Object.keys(one);
  return names.length === Object.keys(other).length && names.every((n) => one[n] === other[n]);
}

/**
 * Keep the filters of a grid with its settings: the filters the account keeps, found again when the
 * screen opens at an address that says nothing of the grid; and, each time the page shows filters
 * that differ from those kept, those recorded with the settings of the grid (`record`). A grid whose
 * screen keeps no filter gives none: nothing is read nor written.
 */
export function useKeptFilters(
  config: { readonly filters?: readonly string[] | undefined; readonly address?: GridAddress },
  preferences: GridPreferences | undefined,
  record: (filters: KeptFilters) => void,
): RefObject<KeptFilters | undefined> {
  // The search and the filters of the grid, and its sort, as the address names them.
  const reading = useMemo(() => {
    const names = config.address ?? CONTRACT_ADDRESS;
    return config.filters === undefined
      ? undefined
      : { filters: [names.search, ...config.filters], sort: [names.sortBy, names.sortOrder] };
  }, [config.address, config.filters]);
  const router = useRouter();
  const pathname = usePathname();
  const query = useSearchParams().toString();
  const names = reading?.filters;
  const kept = useRef(
    names === undefined ? undefined : picked(names, (name) => preferences?.filters?.[name]),
  );
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
    const shown = picked(reading.filters, (name) => address.get(name));
    if (!same(shown, kept.current)) {
      kept.current = shown;
      record(shown);
    }
  }, [query, reading, pathname, router, record]);
  return kept;
}
