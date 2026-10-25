// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The level of the Gantt kept for the session of the tab (`sessionStorage`), by grid and by
 * revision, as the folds of the grids are (`fold.tsx`): nothing is sent to the server. The server
 * renders the Gantt fitted to the project, and the browser shows the kept level once hydrated.
 */
"use client";

import { useSyncExternalStore } from "react";

import type { Zoom } from "./scale";

/** The prefix of the keys the levels are kept under. */
const ZOOM_STORAGE_PREFIX = "waterfall.gantt.zoom.";

/** What is kept in memory alone, by scope, when the browser refuses its storage. */
const memory = new Map<string, string>();

/** Who listens to the levels kept. */
const listeners = new Set<() => void>();

/** What is kept under a scope, if anything. */
function rawOf(scope: string): string | null {
  const kept = memory.get(scope);
  if (kept !== undefined) {
    return kept;
  }
  try {
    return window.sessionStorage.getItem(ZOOM_STORAGE_PREFIX + scope);
  } catch {
    return null;
  }
}

/** The level kept under a scope, among those offered: fitted to the project otherwise. */
function keptZoom(scope: string, levels: number): Zoom {
  const raw = rawOf(scope) ?? "";
  const level = /^\d$/.test(raw) ? Number.parseInt(raw, 10) : -1;
  return level >= 0 && level < levels ? level : "fit";
}

/** Keep a level under a scope, and tell those who listen. */
function keep(scope: string, zoom: Zoom): void {
  const raw = String(zoom);
  try {
    window.sessionStorage.setItem(ZOOM_STORAGE_PREFIX + scope, raw);
    memory.delete(scope);
  } catch {
    // Refused — a quota, a private window —: kept in memory, a reload loses it.
    memory.set(scope, raw);
  }
  for (const listener of listeners) {
    listener();
  }
}

/** Listen to the levels kept. */
function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/**
 * The level of the Gantt kept under a scope — a grid and a revision —, and how to change it; a Gantt
 * without a scope stays fitted to the project.
 */
export function useKeptZoom(
  scope: string | undefined,
  levels: number,
): readonly [Zoom, (zoom: Zoom) => void] {
  const zoom = useSyncExternalStore(
    subscribe,
    () => (scope === undefined ? "fit" : keptZoom(scope, levels)),
    () => "fit" as const,
  );
  return [
    zoom,
    (next) => {
      if (scope !== undefined) {
        keep(scope, next);
      }
    },
  ];
}
