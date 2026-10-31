// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The search and the filters of a grid recorded with its settings (WF-IHM-0060, US-0380), under
 * `filters`, as the address writes them (`GridConfig.filters`): each time the page shows filters that
 * differ from those kept — a reading lifted too, which the address says (`spokenHref`) —, those
 * recorded. Finding them again is the page's, on the server, when the address says nothing of the
 * grid (`restoredAddress`, `kept-address.ts`): nothing is replaced in the browser, nor read twice.
 */
"use client";

import { useSearchParams } from "next/navigation";
import { type RefObject, useEffect, useMemo, useRef } from "react";

import { type KeptFilters, keptFilters, keptReading, sameFilters } from "./kept-address";
import { CONTRACT_ADDRESS, type GridAddress } from "./query";
import type { GridPreferences } from "./settings";

export type { KeptFilters } from "./kept-address";

/**
 * Record the filters of a grid with its settings: each time the page shows filters that differ from
 * those kept, those shown (`record`). A grid whose screen keeps no filter gives none: nothing is
 * read nor written.
 */
export function useKeptFilters(
  config: {
    readonly filters?: readonly string[] | undefined;
    readonly address?: GridAddress;
    readonly defaulted?: Readonly<Record<string, string>> | undefined;
    readonly searchKept?: boolean | undefined;
  },
  preferences: GridPreferences | undefined,
  record: (filters: KeptFilters) => void,
): RefObject<KeptFilters | undefined> {
  // The search and the filters of the grid, as the address names them.
  const reading = useMemo(() => {
    if (config.filters === undefined) {
      return undefined;
    }
    const read = keptReading(config.address ?? CONTRACT_ADDRESS, config.filters);
    return config.searchKept === false
      ? { ...read, filters: read.filters.filter((name) => name !== read.search) }
      : read;
  }, [config.address, config.filters, config.searchKept]);
  const query = useSearchParams().toString();
  const kept = useRef(
    reading === undefined
      ? undefined
      : keptFilters(reading, (name) => preferences?.filters?.[name]),
  );
  useEffect(() => {
    if (reading === undefined || kept.current === undefined) {
      return;
    }
    const address = new URLSearchParams(query);
    const shown = keptFilters(reading, (name) =>
      shownFilter(name, address.get(name), config.defaulted, kept.current),
    );
    if (!sameFilters(shown, kept.current)) {
      kept.current = shown;
      record(shown);
    }
  }, [query, reading, record, config.defaulted]);
  return kept;
}

/**
 * The text a filter shows in the address, for the record: a filter with a default that the address
 * does not name is the one kept, and one shown at the default keeps nothing.
 */
function shownFilter(
  name: string,
  text: string | null,
  defaulted: Readonly<Record<string, string>> | undefined,
  kept: KeptFilters | undefined,
): string | null | undefined {
  const base = defaulted?.[name];
  if (base === undefined) {
    return text;
  }
  const shown = text ?? kept?.[name];
  return shown === base ? undefined : shown;
}
