// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  differenceQuery,
  differencesOnlyHref,
  isDifferencesOnly,
  readDifferenceFilter,
} from "./difference-filter";

describe("the filter of the differences [WF-REV-0100-A]", () => {
  it("reads the differences of the contract the address names, in the order of the contract", () => {
    expect(readDifferenceFilter(new URLSearchParams("difference=modified,added"))).toEqual([
      "added",
      "modified",
    ]);
  });

  it("reads none from an address that names none, or only values the contract does not know", () => {
    expect(readDifferenceFilter(new URLSearchParams(""))).toBeUndefined();
    expect(readDifferenceFilter(new URLSearchParams("difference=unchanged,x"))).toBeUndefined();
  });

  it("says « Écarts seulement » of the three differences together, and asks the server for them", () => {
    const all = readDifferenceFilter(new URLSearchParams("difference=added,removed,modified"));
    expect(isDifferencesOnly(all)).toBe(true);
    expect(isDifferencesOnly(["added"])).toBe(false);
    expect(differenceQuery(all)).toEqual({ difference: ["added", "removed", "modified"] });
    expect(differenceQuery(undefined)).toEqual({});
  });

  it("writes and lifts the filter in an address, the rest of its query kept", () => {
    const query = new URLSearchParams("structure=s");
    expect(differencesOnlyHref("/p", query, true)).toBe(
      "/p?structure=s&difference=added%2Cremoved%2Cmodified",
    );
    expect(differencesOnlyHref("/p", new URLSearchParams("difference=added"), false)).toBe("/p");
  });
});
