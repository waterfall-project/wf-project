// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { backupGrid } from "./backup-grid";

type Backup = components["schemas"]["Backup"];

/** The backup of last night, the first of the witness. */
function lastNight(): Backup {
  const [first] = (example("backups") as { items: Backup[] }).items;
  if (first === undefined) {
    throw new Error("the witness lists backups");
  }
  return first;
}

describe("the grid of the backups", () => {
  it("neither sorts nor searches, the contract doing neither, and keeps its settings under its own key [WF-IHM-0090-A]", () => {
    const config = backupGrid({ editable: false, restorable: false });
    expect(config.key).toBe("backups");
    expect(config.sorts).toBe(false);
    expect(config.searched).toBe(false);
  });

  it("reads each backup by its date, size, verification, origin and retention, and gives each command the columns of the permission that guards it [WF-ADM-0100-A]", () => {
    const read = backupGrid({ editable: false, restorable: false });
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
    const keys = (offers: { editable: boolean; restorable: boolean }) =>
      backupGrid(offers)
        .columns.slice(5)
        .map((column) => [column.key, column.value(lastNight())]);
    // Who may modify the backups marks them in their retention; who may restore the platform
    // downloads and restores them (decision of the author of 2026-10-09, #588).
    expect(keys({ editable: true, restorable: false })).toEqual([]);
    expect(keys({ editable: false, restorable: true })).toEqual([
      ["download", null],
      ["restore", null],
    ]);
  });
});
