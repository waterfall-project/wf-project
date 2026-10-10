// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { sortColumns } from "@/components/grid/columns";
import { example } from "@/test/fixtures";

import type { Backup } from "./backup-address";
import { BACKUP_SORTS, backupGrid, listedCommands, NONE_LISTED } from "./backup-columns";

/** The backups of the witness, as a session that may modify them and restore the platform reads them. */
const BACKUPS = (example("backups") as { items: Backup[] }).items;

/** The same, read by a session that may neither modify them nor restore the platform. */
const READ_ALONE = (example("backups_reader") as { items: Backup[] }).items;

/** The backup of last night, the first of the witness. */
function lastNight(): Backup {
  const [first] = BACKUPS;
  if (first === undefined) {
    throw new Error("the witness lists backups");
  }
  return first;
}

describe("the grid of the backups", () => {
  it("sorts each of its columns by the server, the most recent first unasked and never lifted, and keeps its settings under its own key [WF-IHM-0060-A]", () => {
    const config = backupGrid(NONE_LISTED);
    expect(config.key).toBe("backups");
    expect(config.searched).toBe(false);
    expect(config.lifts).toBe(false);
    expect(sortColumns(config)).toEqual([
      "taken_at",
      "size_bytes",
      "verification",
      "origin",
      "is_retained",
    ]);
    expect(BACKUP_SORTS).toEqual(sortColumns(config));
    expect(config.columns[0]?.descendingFirst).toBe(true);
  });

  it("reads each backup by its date, size, verification, origin and retention, and gives the download and the restoration a column when a backup of the page lists them [WF-IHM-0090-A]", () => {
    const read = backupGrid(listedCommands(READ_ALONE));
    expect(read.columns.map((column) => column.key)).toEqual([
      "taken_at",
      "size_bytes",
      "verification",
      "origin",
      "is_retained",
    ]);
    expect(read.columns.map((column) => column.value(lastNight()))).toEqual([
      "2026-06-03T01:00:00Z",
      "1313656012",
      "passed",
      "scheduled",
      "false",
    ]);
    // The commands listed decide the columns, never the session: the retention widens for the
    // marking, the download and the restoration take a column each.
    expect(listedCommands(READ_ALONE)).toEqual(NONE_LISTED);
    expect(listedCommands(BACKUPS)).toEqual({ marks: true, downloads: true, restores: true });
    const every = backupGrid(listedCommands(BACKUPS));
    expect(every.columns.slice(5).map((column) => [column.key, column.value(lastNight())])).toEqual(
      [
        ["download", null],
        ["restore", null],
      ],
    );
    expect(every.columns[4]?.width).toBeGreaterThan(read.columns[4]?.width ?? 0);
    // A page where one backup alone lists its marking has the column widened all the same.
    const one = [...READ_ALONE.slice(1), ...BACKUPS.slice(0, 1)];
    expect(listedCommands(one)).toEqual({ marks: true, downloads: true, restores: true });
  });
});
