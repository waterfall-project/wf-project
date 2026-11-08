// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The small parts of a dense grid (`dense-grid.tsx`): the spacer of the rows not rendered, whether
 * the grid is busy, the name of a grid among several on its screen, and what holds the grid.
 */
import type { ReactNode } from "react";

import type { GridName } from "./columns";
import type { UndoControl } from "./undo-commands";

/** A spacer for the rows not rendered, before or after those in view. */
export function Spacer({ height, span }: { readonly height: number; readonly span: number }) {
  return height > 0 ? (
    <tr aria-hidden="true">
      <td colSpan={span} style={{ height }} className="p-0" />
    </tr>
  ) : null;
}

/** Whether the grid is busy: reading a sort or a search anew, or a command of its screen waiting. */
export function gridBusy(
  reading: boolean,
  commands: { readonly busy: boolean },
  undo: UndoControl | undefined,
): boolean {
  return reading || commands.busy || undo?.busy === true;
}

/**
 * The name of a grid among several on its screen — one that writes the address under its own
 * names —, which names its search and its menu of the columns; none for a grid alone.
 */
export function sharedName(
  config: { readonly address?: unknown; readonly name: GridName },
  named: (name: GridName) => string,
): string | undefined {
  return config.address === undefined ? undefined : named(config.name);
}

/** The grid, held by what its screen puts around it, if anything. */
export function held<Row>(
  grid: ReactNode,
  rows: readonly Row[],
  around: ((rows: readonly Row[], grid: ReactNode) => ReactNode) | undefined,
): ReactNode {
  return around === undefined ? grid : around(rows, grid);
}
