// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { offsetOf, pageOffsets, readingOf } from "./pages";

describe("the offset a page is asked by", () => {
  it("is the offset of the address when a server could take it, none otherwise", () => {
    expect(offsetOf("50")).toBe(50);
    expect(offsetOf(null)).toBeUndefined();
    expect(offsetOf("0")).toBeUndefined();
    expect(offsetOf("-5")).toBeUndefined();
    expect(offsetOf("2.5")).toBeUndefined();
    expect(offsetOf("ten")).toBeUndefined();
  });
});

describe("where a page stands in its list", () => {
  it("has a page before and after it in the middle of the list", () => {
    expect(pageOffsets({ limit: 50, offset: 50, total: 120 }, 50)).toEqual({
      beyond: false,
      previous: 0,
      next: 100,
    });
  });

  it("has no page before the first, nor after the last", () => {
    expect(pageOffsets({ limit: 50, offset: 0, total: 120 }, 50)).toEqual({
      beyond: false,
      previous: undefined,
      next: 50,
    });
    expect(pageOffsets({ limit: 50, offset: 100, total: 120 }, 20)).toEqual({
      beyond: false,
      previous: 50,
      next: undefined,
    });
  });

  it("is neither beyond nor paged when the page holds the list whole, or the list is empty", () => {
    expect(pageOffsets({ limit: 50, offset: 0, total: 3 }, 3)).toEqual({
      beyond: false,
      previous: undefined,
      next: undefined,
    });
    expect(pageOffsets({ limit: 50, offset: 0, total: 0 }, 0)).toEqual({
      beyond: false,
      previous: undefined,
      next: undefined,
    });
  });

  it("is beyond the end when asked past the last row, and leads back to the last page", () => {
    // Sixty rows, the page of the third fifty asked: the last page starts at the second.
    expect(pageOffsets({ limit: 50, offset: 100, total: 60 }, 0)).toEqual({
      beyond: true,
      previous: 50,
      next: undefined,
    });
    // A page asked at the very end: the last page is the one before it.
    expect(pageOffsets({ limit: 2, offset: 8, total: 5 }, 0)).toEqual({
      beyond: true,
      previous: 4,
      next: undefined,
    });
    // Beyond an emptied list: the first page is its last.
    expect(pageOffsets({ limit: 50, offset: 100, total: 0 }, 0)).toEqual({
      beyond: true,
      previous: 0,
      next: undefined,
    });
  });
});

describe("what a list reads of the address", () => {
  it("tells a parameter absent from one given empty, and leaves out those it does not read", () => {
    // `sort_by` empty is a sort lifted, absent the sort the account keeps: not the same list.
    expect(readingOf(new URLSearchParams("sort_by="), ["sort_by"])).not.toBe(
      readingOf(new URLSearchParams(), ["sort_by"]),
    );
    const reads = ["include_inactive", "role_search"];
    const absent = readingOf(new URLSearchParams("calendar_search=x"), reads);
    const empty = readingOf(new URLSearchParams("role_search="), reads);
    expect(absent).not.toBe(empty);
    expect(readingOf(new URLSearchParams("role_search=Ing&include_inactive=true"), reads)).toBe(
      readingOf(
        new URLSearchParams("include_inactive=true&calendar_search=x&role_search=Ing"),
        reads,
      ),
    );
  });

  it("never reads two values as others that hold `&` or `=`", () => {
    const reads = ["search", "states"];
    const one = new URLSearchParams();
    one.set("search", "a&states=b");
    const two = new URLSearchParams();
    two.set("search", "a");
    two.set("states", "b&states");
    expect(readingOf(one, reads)).not.toBe(readingOf(two, reads));
  });
});
