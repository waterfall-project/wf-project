// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The version of the structure a grid keeps (`CostStructure.lock_version`): the one read with the
 * page, and the one each write answered moved it on to (`NodesWritten.structure_lock_version`) —
 * a cell entered, a node created, moved or deleted, a block pasted, a skeleton generated all
 * advance it. A single account per grid, so that the next move or paste carries the version the
 * last write left, whichever wrote it.
 */
import { useCallback, useState } from "react";

/** The version the structure reached by the writes answered, for the structure it was written in. */
interface Reached {
  readonly structure: string;
  readonly version: number;
}

/**
 * The version of a structure — the highest of the one read with the page and of those the writes
 * answered; an answer may come back after a later one, and a page read anew that is more recent
 * prevails — and what tells it a write's answer (`reach`).
 */
export function useStructureVersion(
  structure: string,
  read: number,
): readonly [version: number, reach: (version: number) => void] {
  const [reached, setReached] = useState<Reached>();
  const reach = useCallback(
    (version: number) => {
      setReached((before) => ({
        structure,
        version: Math.max(before?.structure === structure ? before.version : 0, version),
      }));
    },
    [structure],
  );
  return [Math.max(read, reached?.structure === structure ? reached.version : 0), reach];
}
