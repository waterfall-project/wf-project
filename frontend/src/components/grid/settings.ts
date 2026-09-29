// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of a grid — the columns hidden, the widths set, the sort chosen —, a display
 * preference of the account (WF-ADM-0040, WF-IHM-0060): personal, and without effect on the
 * data. The grid starts from those the session read, when there are any — the page sorts by the
 * one kept when the address asks none —, and records each change under its key
 * (`updateGridPreferences`), the API replacing that grid whole: what the grid does not set — the
 * filters kept there — goes back as it came.
 *
 * A column shown or widened is recorded once the user pauses: a column dragged wider changes
 * its width at every move, and only the last one is written; it sends back the sort as the
 * account keeps it. A sort is recorded at once, alongside the navigation that shows it — only a
 * header writes the sort. What still waits is written when the page is left or hidden, before a
 * search, and when the grid goes: at best, for a server action carries no `keepalive`, and a
 * browser closing a tab may cut it short. Only the outcome of the last write is told: an
 * earlier one answering late says nothing of what the grid now shows.
 */
"use client";

import { startTransition, useCallback, useEffect, useRef, useState } from "react";

import { updateGridPreferences } from "@/api/actions/preferences";
import type { components } from "@/api/generated/schema";
import type { Settled } from "@/api/problem";

import { MAX_WIDTH, MIN_WIDTH } from "./columns";

/** The settings of a grid, as the account keeps them. */
export type GridPreferences = components["schemas"]["GridPreferences"];

/** The settings of a grid, as the table holds them: visibility and width by column. */
export interface GridSettings {
  /** The columns hidden, each `false`; a column absent shows. */
  readonly visibility: Readonly<Record<string, boolean>>;
  /** The widths the user set, in pixels; a column absent has its width by default. */
  readonly sizing: Readonly<Record<string, number>>;
}

/** How long the grid waits after a change before recording it, in milliseconds. */
export const WRITE_DELAY = 500;

/** What of a column the settings read: its key, and whether it can be hidden. */
interface SettledColumn {
  readonly key: string;
  readonly pinned?: boolean;
}

/** A width within the bounds of the grid. */
function bounded(width: number): number {
  return Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Math.round(width)));
}

/**
 * The settings a grid starts with, from the preferences the session read: the columns it has
 * and may hide, the widths of the columns it has. A key of another version of the grid is left
 * aside, and a width out of bounds is brought within them.
 */
export function initialSettings(
  preferences: GridPreferences | undefined,
  columns: readonly SettledColumn[],
): GridSettings {
  const hideable = new Set(columns.filter((column) => column.pinned !== true).map((c) => c.key));
  const known = new Set(columns.map((column) => column.key));
  const hidden = (preferences?.hidden_columns ?? []).filter((key) => hideable.has(key));
  const widths = Object.entries(preferences?.column_widths ?? {}).filter(([key]) => known.has(key));
  return {
    visibility: Object.fromEntries(hidden.map((key) => [key, false])),
    sizing: Object.fromEntries(widths.map(([key, width]) => [key, bounded(width)])),
  };
}

/** The sort the account keeps for a grid, as the contract gives it: none is `null`. */
export type KeptGridSort = GridPreferences["sort"];

/**
 * The preferences to record for a grid: its settings, the sort to keep — the one a header just
 * asked, or the one the account kept, as it came —, and what the account kept of it besides,
 * as it came: the grid is replaced whole.
 */
export function recordedPreferences(
  preferences: GridPreferences | undefined,
  settings: GridSettings,
  sort: KeptGridSort,
): GridPreferences {
  const recorded: GridPreferences = {
    ...preferences,
    hidden_columns: Object.entries(settings.visibility)
      .filter(([, visible]) => !visible)
      .map(([key]) => key),
    column_widths: Object.fromEntries(
      Object.entries(settings.sizing).map(([key, width]) => [key, bounded(width)]),
    ),
  };
  return sort === undefined ? recorded : { ...recorded, sort };
}

/** What the writer of the settings gives the grid. */
export interface SettingsWriter {
  /** Record preferences once the user pauses. */
  readonly record: (preferences: GridPreferences) => void;
  /** Record preferences at once, whatever waited dropped: they replace it. */
  readonly recordNow: (preferences: GridPreferences) => void;
  /** Record at once what waits, if anything. */
  readonly flush: () => void;
  /** The outcome of the last write that failed; nothing once it succeeded. */
  readonly outcome: Settled | undefined;
  /** Forget the outcome told. */
  readonly clear: () => void;
}

/** Record the settings of a grid under its key: after a pause, or at once. */
export function useSettingsWriter(grid: string): SettingsWriter {
  const [outcome, setOutcome] = useState<Settled>();
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const waiting = useRef<GridPreferences>(undefined);
  const latest = useRef(0);

  const send = useCallback(
    async (sent: GridPreferences) => {
      latest.current += 1;
      const write = latest.current;
      const result = await updateGridPreferences(grid, sent);
      if (write === latest.current) {
        setOutcome(result.kind === "done" ? undefined : result);
      }
    },
    [grid],
  );

  const flush = useCallback(() => {
    clearTimeout(timer.current);
    const sent = waiting.current;
    waiting.current = undefined;
    if (sent !== undefined) {
      startTransition(() => send(sent));
    }
  }, [send]);

  // What waits is written when the page is left or hidden — a tab closed, another opened —,
  // and when the grid goes; at best, as said above.
  useEffect(() => {
    const hidden = () => {
      if (document.visibilityState === "hidden") {
        flush();
      }
    };
    window.addEventListener("pagehide", flush);
    document.addEventListener("visibilitychange", hidden);
    return () => {
      window.removeEventListener("pagehide", flush);
      document.removeEventListener("visibilitychange", hidden);
      flush();
    };
  }, [flush]);

  const record = useCallback(
    (preferences: GridPreferences) => {
      waiting.current = preferences;
      clearTimeout(timer.current);
      timer.current = setTimeout(flush, WRITE_DELAY);
    },
    [flush],
  );
  const recordNow = useCallback(
    (preferences: GridPreferences) => {
      clearTimeout(timer.current);
      waiting.current = undefined;
      startTransition(() => send(preferences));
    },
    [send],
  );
  const clear = useCallback(() => {
    setOutcome(undefined);
  }, []);
  return { record, recordNow, flush, outcome, clear };
}
