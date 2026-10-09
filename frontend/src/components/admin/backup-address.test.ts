// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  downloadHref,
  downloadRefusedHref,
  readDownloadRefusal,
  withoutDownloadRefusal,
} from "./backup-address";

const BACKUP = "01926f3a-7c00-7000-8000-000000000907";

describe("the way of the download of a backup", () => {
  it("leaves from the screen it names, and comes back to it with the refusal, which reads again as it was", () => {
    expect(downloadHref(BACKUP, "/admin/backups?offset=50")).toBe(
      `/admin/backups/${BACKUP}/content?from=%2Fadmin%2Fbackups%3Foffset%3D50`,
    );
    const back = downloadRefusedHref("/admin/backups?offset=50", BACKUP, {
      kind: "refused",
      problem: { code: "PERMISSION_MISSING", status: 403 },
      conflictingObjectId: null,
    });
    const search = new URLSearchParams(back.split("?")[1]);
    expect(readDownloadRefusal(search)).toEqual({
      id: BACKUP,
      refusal: {
        kind: "refused",
        problem: { code: "PERMISSION_MISSING", status: 403 },
        conflictingObjectId: null,
      },
    });
    expect(
      withoutDownloadRefusal({ pathname: "/admin/backups", search: `?${search.toString()}` }),
    ).toBe("/admin/backups?offset=50");
  });

  it("reads no refusal from an address that names no backup or no refusal it can stand for, and an unknown code as the unexpected error", () => {
    expect(
      readDownloadRefusal(new URLSearchParams("refusal=403%3APERMISSION_MISSING")),
    ).toBeUndefined();
    expect(
      readDownloadRefusal(new URLSearchParams(`refused_backup=${BACKUP}&refusal=nope`)),
    ).toBeUndefined();
    expect(
      readDownloadRefusal(new URLSearchParams(`refused_backup=a%2Fb&refusal=unreachable`)),
    ).toBeUndefined();
    expect(
      readDownloadRefusal(
        new URLSearchParams(`refused_backup=${BACKUP}&refusal=500%3ANO_SUCH_CODE`),
      )?.refusal,
    ).toEqual({
      kind: "refused",
      problem: { code: "INTERNAL_ERROR", status: 500 },
      conflictingObjectId: null,
    });
    expect(
      withoutDownloadRefusal({ pathname: "/admin/backups", search: "?refusal=unreachable" }),
    ).toBe("/admin/backups");
  });
});
