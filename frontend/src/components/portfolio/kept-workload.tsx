// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The horizon, the threshold and the node of the aggregated workload recorded with the preferences
 * of its key (WF-PTF-0060-A, WF-IHM-0060), as a dense grid records its filters: each time the page
 * shows settings that differ from those kept, those shown; the page finds them again, on the server,
 * when the address leaves one out (`restoredWorkload`). What the account kept for the key besides is sent
 * back as it came. A write the service refuses is told where the screen stands, and may be dismissed.
 *
 * Every prop is data, never a function: a server component hands it over (défaut n° 12 de
 * `typescript.md`).
 */
"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";

import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { keptFilters, sameFilters } from "@/components/grid/kept-address";
import { type GridPreferences, useSettingsWriter } from "@/components/grid/settings";

import { WORKLOAD_KEPT, WORKLOAD_KEY } from "./kept-workload-address";

/** Record the settings the address shows under the key of the workload; renders its refusal, if any. */
export function KeptWorkload({
  preferences,
}: {
  /** What the account kept for the key; none, it kept nothing. */
  readonly preferences: GridPreferences | undefined;
}) {
  const { recordShown, shown, outcome, clear } = useSettingsWriter(WORKLOAD_KEY);
  const query = useSearchParams().toString();
  const kept = useRef(keptFilters(WORKLOAD_KEPT, (name) => preferences?.filters?.[name]));
  useEffect(() => {
    const address = new URLSearchParams(query);
    const filters = keptFilters(WORKLOAD_KEPT, (name) => address.get(name));
    if (!sameFilters(filters, kept.current)) {
      kept.current = filters;
      recordShown(() => ({ ...preferences, filters }));
      shown();
    }
  }, [query, preferences, recordShown, shown]);
  return <OutcomeNotice outcome={outcome} onClear={clear} dismissible />;
}
