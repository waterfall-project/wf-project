// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { Caller } from "./background";
import {
  currentOf,
  dayOf,
  keptReads,
  markedOf,
  type RevisionRef,
  revisionsOf,
  spread,
} from "./volumes";

const REVISIONS: readonly RevisionRef[] = [
  { revision_id: "current", status: "draft", marked_at: null },
  { revision_id: "later", status: "marked", marked_at: "2026-09-07T09:00:00Z" },
  { revision_id: "earlier", status: "marked", marked_at: "2026-07-06T09:00:00Z" },
];

describe("the revisions of a project", () => {
  it("finds the current revision, the one in progress [US-2970]", () => {
    expect(currentOf(REVISIONS)).toBe("current");
    expect(() => currentOf([])).toThrow("no revision in progress");
  });

  it("lists the marked revisions, the oldest first [US-2970]", () => {
    expect(markedOf(REVISIONS).map(({ revision_id: id }) => id)).toEqual(["earlier", "later"]);
  });

  it("spreads a few revisions over the history, the first and the last among them [US-2970]", () => {
    const history = Array.from({ length: 180 }, (_, index) => index);
    expect(spread(history, 5)).toEqual([0, 45, 90, 134, 179]);
    expect(spread([1, 2], 5)).toEqual([1, 2]);
  });

  it("reads the day of an instant as the contract writes a date [US-2970]", () => {
    expect(dayOf("2026-07-06T09:00:00Z")).toBe("2026-07-06");
  });

  it("reads the revisions page after page up to their total [US-2970]", async () => {
    const asked: string[] = [];
    const api = {
      get: (path: string) => {
        asked.push(path);
        return Promise.resolve({ items: REVISIONS, meta: { total: 3 } });
      },
    } as unknown as Caller;
    expect(await revisionsOf(api, "p")).toEqual(REVISIONS);
    expect(asked).toEqual(["/projects/p/revisions?limit=500&offset=0"]);
  });
});

describe("the indicators kept at a past date", () => {
  it("are read at the day each revision was marked, the reading of a past date [WF-DAT-0040]", async () => {
    const asked: string[] = [];
    const api = {
      timed: (path: string) => {
        asked.push(path);
        return Promise.resolve({ seconds: 0.1, status: 200 });
      },
    } as unknown as Caller;
    const reads = await keptReads(api, "p", markedOf(REVISIONS), 2);
    expect(reads.map(({ name }) => name)).toEqual([
      "indicators kept at 2026-07-06",
      "indicators kept at 2026-09-07",
    ]);
    expect(asked[0]).toBe("/projects/p/indicators?as_of=2026-07-06");
    expect(asked).toHaveLength(6);
  });

  it("leave out the revisions that kept none, refused 409, and fail when none kept any [WF-DAT-0040]", async () => {
    const api = {
      timed: (path: string) =>
        Promise.resolve({ seconds: 0.1, status: path.includes("2026-07-06") ? 409 : 200 }),
    } as unknown as Caller;
    const reads = await keptReads(api, "p", markedOf(REVISIONS), 2);
    expect(reads.map(({ name }) => name)).toEqual(["indicators kept at 2026-09-07"]);
    const refusing = {
      timed: () => Promise.resolve({ seconds: 0, status: 409 }),
    } as unknown as Caller;
    await expect(keptReads(refusing, "p", markedOf(REVISIONS), 2)).rejects.toThrow(
      "no revision of the project kept its indicators",
    );
  });

  it("refuse a revision with no marking instant [WF-DAT-0040]", async () => {
    const api = {} as unknown as Caller;
    await expect(
      keptReads(api, "p", [{ revision_id: "x", status: "draft", marked_at: null }], 2),
    ).rejects.toThrow("instant of its marking");
  });
});
