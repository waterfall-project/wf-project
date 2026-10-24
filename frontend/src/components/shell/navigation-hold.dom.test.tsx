// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import type { CellEntry, RowsWritten } from "@/components/grid/columns";
import { useCellWrites } from "@/components/grid/cell-writes";
import {
  type HourlyRate,
  rateWritten,
  type RateRow,
  withYears,
} from "@/components/reference/rate-cells";
import { example } from "@/test/fixtures";

import { useNavigationHold } from "./navigation-hold";

// The grid of the rates of the volumes, whose cell of 2015 for the mechanical engineering is written.
const volume = example("volume/hourly_rate_grid") as {
  years: number[];
  rows: components["schemas"]["HourlyRateRow"][];
};
const rows = withYears(
  volume.rows,
  volume.years.map((year, index) => ({ year, index })),
);
const entered = example("hourly_rate_entered") as HourlyRate;
const found = rows.find((row) => row.cost_category_id === entered.cost_category_id);
if (found === undefined) {
  throw new Error("the grid of the volumes has no row of the mechanical engineering");
}
const MECHANICAL: RateRow = found;
const LOST: Outcome<never> = {
  kind: "signed_out",
  problem: { code: "SESSION_REQUIRED", status: 401 },
  conflictingObjectId: null,
};

/** Every promise under way settled. */
function settled(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

/**
 * The page: its shell holding its navigations, a grid of rates whose write waits until answered,
 * and a link of the side bar, followed as the router of Next follows it.
 */
function page() {
  renderHook(() => {
    useNavigationHold();
  });
  const grid = renderHook(() =>
    useCellWrites<RateRow, null>(
      { address: "/reference/costs?", rows, totals: null },
      { rowKey: (row) => row.cost_category_id },
    ),
  );
  let answer: (outcome: Outcome<RowsWritten<RateRow, null>>) => void = () => undefined;
  const entry: CellEntry<RateRow, null> = {
    kind: { type: "decimal", nullable: false },
    in: () => true,
    value: () => undefined,
    write: () =>
      new Promise((resolve) => {
        answer = resolve;
      }),
  };
  const followed = vi.fn((event: MouseEvent) => {
    event.preventDefault();
  });
  const link = document.createElement("a");
  link.href = "/portfolio";
  link.addEventListener("click", followed);
  document.body.append(link);
  /** The pointer goes down on the link: the cell is validated, its write under way. */
  const press = async () => {
    fireEvent.pointerDown(link);
    await act(async () => {
      grid.result.current.write({
        row: MECHANICAL,
        column: "year_2015",
        entry,
        value: "85,48",
        shown: "85,48",
      });
      await settled();
    });
  };
  /** The cell left for the link: validated as the pointer goes down, the click following. */
  const leave = async () => {
    await press();
    link.click();
  };
  /** The server answers the write. */
  const answered = async (outcome: Outcome<RowsWritten<RateRow, null>>) => {
    await act(async () => {
      answer(outcome);
      await settled();
    });
  };
  return { grid, link, followed, press, leave, answered };
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("a navigation while a cell is written (#688)", () => {
  it("waits for the write, and does not take place when the session was lost meanwhile: the write is told not applied, where it was made", async () => {
    const { grid, followed, leave, answered } = page();
    await leave();
    expect(followed).not.toHaveBeenCalled();
    await answered(LOST);
    expect(followed).not.toHaveBeenCalled();
    expect(grid.result.current.outcome).toEqual(LOST);
  });

  it("takes place once the write is applied, the link following as it would have", async () => {
    const { grid, link, followed, leave, answered } = page();
    await leave();
    expect(followed).not.toHaveBeenCalled();
    await answered({ kind: "done", data: rateWritten(MECHANICAL, entered.year, entered, 1) });
    expect(grid.result.current.outcome?.kind).toBe("done");
    expect(followed).toHaveBeenCalledOnce();
    // No write under way: the next navigation goes at once.
    link.click();
    expect(followed).toHaveBeenCalledTimes(2);
  });

  it("does not take place when the session lost answered between the pointer going down and the click: the refusal is told, where the write was made", async () => {
    const { grid, link, followed, press, answered } = page();
    await press();
    await answered(LOST);
    link.click();
    await act(settled);
    expect(followed).not.toHaveBeenCalled();
    expect(grid.result.current.outcome).toEqual(LOST);
    // A gesture begun once the refusal is told: the person decides, and the link is followed.
    fireEvent.pointerDown(link);
    link.click();
    expect(followed).toHaveBeenCalledOnce();
  });

  it("makes again only the last click held", async () => {
    const { link, followed, leave, answered } = page();
    await leave();
    fireEvent.pointerDown(link);
    link.click();
    await answered({ kind: "done", data: rateWritten(MECHANICAL, entered.year, entered, 1) });
    expect(followed).toHaveBeenCalledOnce();
  });

  it("does not wait for the writes of a grid gone: they hold no click of the next screen", async () => {
    const { grid, link, followed, press, answered } = page();
    await press();
    grid.unmount();
    fireEvent.pointerDown(link);
    link.click();
    expect(followed).toHaveBeenCalledOnce();
    await answered(LOST);
    expect(followed).toHaveBeenCalledOnce();
  });

  it("leaves alone a link that opens elsewhere, even while a write is under way", async () => {
    const { followed, leave, link, answered } = page();
    link.target = "_blank";
    await leave();
    expect(followed).toHaveBeenCalledOnce();
    await answered(LOST);
  });
});
