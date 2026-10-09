// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { type HourlyRate, rated, rateWritten, type RateRow, withYears } from "./rate-cells";

// The grid of the rates of the volumes; the first rate of 2015 of the mechanical engineering
// (MO-003), and a correction of 2016 of the same category.
const volume = example("volume/hourly_rate_grid") as {
  years: number[];
  rows: components["schemas"]["HourlyRateRow"][];
};
const rows = withYears(
  volume.rows,
  volume.years.map((year, index) => ({ year, index })),
);
const entered = example("hourly_rate_entered") as HourlyRate;
const corrected = example("hourly_rate_corrected") as HourlyRate;
const mechanical = rows.find((row) => row.cost_category_id === entered.cost_category_id);
const Y2015 = volume.years.indexOf(entered.year);
const Y2016 = volume.years.indexOf(corrected.year);

/** The row of the mechanical engineering, which the volumes hold. */
function row(): RateRow {
  if (mechanical === undefined) {
    throw new Error("the volumes hold the mechanical engineering");
  }
  return mechanical;
}

describe("the rate answered in a cell of a row", () => {
  it("takes the place of an older rate of its year, and leaves a rate as new or newer", () => {
    expect(rated(row(), entered).cells[Y2015]).toEqual(entered);
    expect(rated(row(), corrected).cells[Y2016]).toEqual(corrected);
    const newer = rated(row(), { ...corrected, lock_version: 3, amount: "88.00" });
    expect(rated(newer, corrected)).toBe(newer);
  });

  it("finds its cell by its year, leaves a row without one, and grows the row to the column of a year added", () => {
    const shifted = { ...row(), cells: [null, ...row().cells], years: [2011, ...row().years] };
    expect(rated(shifted, entered).cells[Y2015 + 1]).toEqual(entered);
    expect(rated(shifted, entered).cells[Y2015]).toBeNull();
    expect(rated(row(), { ...entered, year: 2040 })).toBe(row());
    const past = row().cells.length + 2;
    const years = [...row().years];
    years[past] = 2040;
    const grown = rated({ ...row(), years }, { ...entered, year: 2040 });
    expect(grown.cells).toHaveLength(past + 1);
    expect(grown.cells[past - 1]).toBeNull();
  });

  it("is a change of the cell judged by its counter, none for the rate of another category", () => {
    const written = rateWritten(row(), entered.year, entered, 1);
    expect(written.rows).toEqual([]);
    expect(written.parts.map((part) => [part.key, part.versioned])).toEqual([
      [entered.cost_category_id, true],
    ]);
    const other = rows[0];
    if (other === undefined) {
      throw new Error("the volumes hold a first category");
    }
    expect(rateWritten(other, entered.year, entered, 1).parts).toEqual([]);
  });
});
