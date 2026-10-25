// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { keptReading, restoredAddress, spokenHref } from "./kept-address";
import { CONTRACT_ADDRESS } from "./query";

const READING = keptReading(CONTRACT_ADDRESS, ["origins"]);

describe("the address a grid with settings kept leads to", () => {
  it("names the size of the pages among what it says of the grid, so that the filters kept never take it away [WF-IHM-0060-A]", () => {
    expect(READING.size).toEqual(["limit"]);
    const kept = { origins: "local" };
    const at = (query: string) =>
      restoredAddress("/admin/users", new URLSearchParams(query), READING, kept);
    expect(at("")).toBe("/admin/users?origins=local");
    expect(at("limit=25")).toBeUndefined();
    expect(at("offset=50")).toBe("/admin/users?origins=local");
  });

  it("does not say a reading lifted while the address holds a size", () => {
    expect(spokenHref("/admin/users?limit=25", READING)).toBe("/admin/users?limit=25");
    expect(spokenHref("/admin/users", READING)).toBe("/admin/users?search=");
  });
});
