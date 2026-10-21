// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The account a grid keeps of the writes of its structure: the version of the structure
 * (`CostStructure.lock_version`) — the one read with the page, and the one each write answered moved
 * it on to (`NodesWritten.structure_lock_version`), a cell entered, a node created, moved or deleted,
 * a block pasted, a skeleton generated all advancing it —, and the writes under way. A single account
 * per grid, so that the next move or paste carries the version the last write left, whichever wrote
 * it, and so that the grid is busy while any of them waits — a gesture, a cell entered, a paste
 * (decision of the author of 2026-10-21, #1224): a move or a drop sent meanwhile would leave with a
 * version an answer is about to move on, and be refused.
 *
 * Each is kept for the structure it was written in (défaut n° 1 de `typescript.md`): a grid that
 * shows another structure since — a structure chosen in the address, a revision left — neither takes
 * the version an answer of the first moved on to, nor waits for its writes, nor reads anew for it.
 */
import { useCallback, useLayoutEffect, useRef, useState } from "react";

/** A count by structure, by its identifier. */
type ByStructure = Readonly<Record<string, number>>;

/** The account of the writes of the structure a grid shows. */
export interface StructureAccount {
  /**
   * The version of the structure: the highest of the one read with the page and of those the writes
   * answered — an answer may come back after a later one, and a page read anew that is more recent
   * prevails.
   */
  readonly version: number;
  /** Tell the version a write answered, for the structure it was sent in, whatever is shown since. */
  readonly reach: (version: number) => void;
  /** Count a write under way in the structure, until it settles, whatever its outcome. */
  readonly writing: (write: Promise<unknown>) => void;
  /** Whether a write of the structure shown is under way. */
  readonly busy: boolean;
  /** Whether the grid still shows a structure — the one a write was sent in: read once it answered. */
  readonly shows: (structure: string) => boolean;
}

/** A count with one structure moved by a step, never below zero. */
function stepped(counts: ByStructure, structure: string, step: 1 | -1): ByStructure {
  return { ...counts, [structure]: Math.max(0, (counts[structure] ?? 0) + step) };
}

/** The account of the writes of a structure, read with the page at version `read`. */
export function useStructureVersion(structure: string, read: number): StructureAccount {
  const [reached, setReached] = useState<ByStructure>({});
  const [underWay, setUnderWay] = useState<ByStructure>({});
  // The structure the grid shows, as committed: no callback runs between a commit and its layout
  // effects, so an answer never finds the structure of a render not shown yet; none once the grid is
  // gone.
  const shown = useRef<string>(undefined);
  useLayoutEffect(() => {
    shown.current = structure;
    return () => {
      shown.current = undefined;
    };
  }, [structure]);
  const reach = useCallback(
    (version: number) => {
      setReached((before) => ({
        ...before,
        [structure]: Math.max(before[structure] ?? 0, version),
      }));
    },
    [structure],
  );
  const writing = useCallback(
    (write: Promise<unknown>) => {
      setUnderWay((before) => stepped(before, structure, 1));
      const settled = () => {
        setUnderWay((before) => stepped(before, structure, -1));
      };
      void write.then(settled, settled);
    },
    [structure],
  );
  const shows = useCallback((sent: string) => shown.current === sent, []);
  return {
    version: Math.max(read, reached[structure] ?? 0),
    reach,
    writing,
    busy: (underWay[structure] ?? 0) > 0,
    shows,
  };
}
