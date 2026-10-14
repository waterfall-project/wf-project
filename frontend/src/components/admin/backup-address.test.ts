// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { backupContentHref, backupsHref } from "./backup-address";

describe("the address of the archive of a backup", () => {
  it("names the page of the list it leaves from", () => {
    expect(backupContentHref("01926f3a-7c00-7000-8000-000000000907", backupsHref(50))).toBe(
      "/admin/backups/01926f3a-7c00-7000-8000-000000000907/content?from=%2Fadmin%2Fbackups%3Foffset%3D50",
    );
    expect(backupsHref(0)).toBe("/admin/backups");
  });
});
