// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Whether the encart « Démarrer le projet » is folded, kept for the session of the tab
 * (`sessionStorage`, as the folds of the grids are): nothing is sent to the server. The server renders
 * the encart open and the browser folds it once hydrated — `useSyncExternalStore` reads the
 * storage, which the server does not have. Kept in memory alone when the browser refuses the storage.
 */
import { useSyncExternalStore } from "react";

import { foldedKey } from "./start-offers";

const memory = new Map<string, boolean>();
const listeners = new Set<() => void>();

/** Whether the encart of a project is folded, in the storage of the tab or in memory. */
function read(projectId: string): boolean {
  const kept = memory.get(projectId);
  if (kept !== undefined) {
    return kept;
  }
  try {
    return window.sessionStorage.getItem(foldedKey(projectId)) === "1";
  } catch {
    return false;
  }
}

/** Keep the encart of a project folded or open, and tell those who listen. */
export function keepFolded(projectId: string, folded: boolean): void {
  try {
    window.sessionStorage.setItem(foldedKey(projectId), folded ? "1" : "0");
    memory.delete(projectId);
  } catch {
    memory.set(projectId, folded);
  }
  for (const listener of listeners) {
    listener();
  }
}

/** Listen to what the encarts keep. */
function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Whether the encart of a project is folded for this session; open on the server. */
export function useFolded(projectId: string): boolean {
  return useSyncExternalStore(
    subscribe,
    () => read(projectId),
    () => false,
  );
}
