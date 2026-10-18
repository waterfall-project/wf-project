// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  BACKUPS_LIST,
  backupsQuery,
  downloadHref,
  downloadRefusedHref,
  narrows,
  NEWEST_FIRST,
  readBackupFilters,
  readDownloadRefusal,
  withoutDownloadRefusal,
} from "./backup-address";

const BACKUP = "01926f3a-7c00-7000-8000-000000000907";

describe("what the list of the backups reads of its address", () => {
  it("reads each filter under the name of the contract, and asks the server for it, with the sort and the page [WF-IHM-0130-A]", () => {
    const filters = readBackupFilters(
      new URLSearchParams(
        "from=2026-05-31T22:00:00Z&to=2026-06-30T22:00:00Z&origins=scheduled,manual&verifications=failed&is_retained=true&size_bytes_min=1000000000&size_bytes_max=1313656012",
      ),
    );
    expect(filters).toEqual({
      period: { from: "2026-05-31T22:00:00Z", to: "2026-06-30T22:00:00Z" },
      origins: ["manual", "scheduled"],
      verifications: ["failed"],
      retained: true,
      size: { min: "1000000000", max: "1313656012" },
    });
    expect(narrows(filters)).toBe(true);
    expect(backupsQuery(filters, { sort: NEWEST_FIRST, search: undefined }, 50)).toEqual({
      sort_by: "taken_at",
      sort_order: "desc",
      offset: 50,
      from: "2026-05-31T22:00:00Z",
      to: "2026-06-30T22:00:00Z",
      origins: ["manual", "scheduled"],
      verifications: ["failed"],
      is_retained: true,
      size_bytes_min: 1000000000,
      size_bytes_max: 1313656012,
    });
  });

  it("reads no filter from an address that names none the server could take, and asks nothing of it", () => {
    const filters = readBackupFilters(
      new URLSearchParams("from=yesterday&origins=cloud&is_retained=yes&size_bytes_max=1.5"),
    );
    expect(narrows(filters)).toBe(false);
    expect(backupsQuery(filters, { sort: undefined, search: undefined }, undefined)).toEqual({});
  });

  it("holds every parameter the list asks of the server, but its page: a filter under way reads another list", () => {
    const query = backupsQuery(
      readBackupFilters(
        new URLSearchParams(
          "from=2026-05-31T22:00:00Z&to=2026-06-30T22:00:00Z&origins=manual&verifications=passed&is_retained=false&size_bytes_min=1&size_bytes_max=2",
        ),
      ),
      { sort: NEWEST_FIRST, search: undefined },
      50,
    );
    const asked = Object.keys(query).filter((name) => name !== BACKUPS_LIST.page);
    expect(asked).toHaveLength(9);
    expect(BACKUPS_LIST.reads).toEqual(expect.arrayContaining(asked));
  });
});

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
