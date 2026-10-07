// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The columns of a dense grid in a journey, found by their heading as a user reads them, never by
 * a position written in the journey (#400): a column added to a grid moves the others, and a
 * journey that counted them would land on the wrong cell.
 */
import type { Locator } from "@playwright/test";

/**
 * The position of each column among the cells of a row, by its heading — its accessible name, a
 * narrow column named by the icon that heads it, a computed one after its mark —, the number of
 * the row first: the position of the cell, which `getByRole("gridcell").nth` takes.
 */
export async function columnsOf<K extends string>(
  grid: Locator,
  headings: Readonly<Record<K, string>>,
): Promise<Readonly<Record<K, number>>> {
  const entries = await Promise.all(
    Object.entries<string>(headings).map(async ([key, heading]) => {
      const header = grid.getByRole("columnheader", { name: heading });
      const position = await header.evaluate((cell) =>
        cell instanceof HTMLTableCellElement ? cell.cellIndex : -1,
      );
      if (position < 0) {
        throw new Error(`no column headed ${heading}`);
      }
      return [key, position] as const;
    }),
  );
  // Each key of the headings, given its position.
  return Object.fromEntries(entries) as Record<K, number>;
}
