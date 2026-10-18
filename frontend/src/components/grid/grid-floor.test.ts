// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { barWidth, contentRem, floorOf, withBar } from "./grid-floor";

describe("the floor of the frame of a dense grid (#1041)", () => {
  it.each([
    [0, 5.75],
    [1, 5.75],
    [2, 7.5],
    [3, 9.25],
    [4, 11],
  ])(
    "counts the header, the totals and the rows of a grid of %i rows: %f rem [WF-IHM-0060-A]",
    (rows, rem) => {
      expect(contentRem(rows)).toBe(rem);
    },
  );

  it("is the content of a grid that is lower than ten rem, and ten rem otherwise, the borders in [WF-IHM-0060-A]", () => {
    expect(floorOf(2)).toBe("min(10rem, calc(7.5rem + 2px))");
    expect(floorOf(0)).toBe("min(10rem, calc(5.75rem + 2px))");
    expect(floorOf(6000)).toBe("min(10rem, calc(10504rem + 2px))");
  });

  it("adds the bar to the floor for what holds the grid, and the borders to the width of the bar [WF-IHM-0060-A]", () => {
    expect(withBar(2)).toBe("calc(min(10rem, calc(7.5rem + 2px)) + 2.25rem)");
    expect(barWidth(640)).toBe("642px");
  });
});
