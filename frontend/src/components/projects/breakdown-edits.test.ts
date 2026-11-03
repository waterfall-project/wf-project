// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { edited, elementAt } from "./breakdown-edits";
import { type BreakdownRow, breakdownRows, type WorkBreakdown } from "./settings-grids";

const WHOLE = example("work_breakdown") as WorkBreakdown;
const DEFAULT = example("work_breakdown_default") as WorkBreakdown;
const ROWS = breakdownRows(WHOLE);
const row = (label: string): BreakdownRow => {
  const found = ROWS.find((each) => each.label === label);
  if (found === undefined) {
    throw new Error(`no row ${label}`);
  }
  return found;
};

describe("the gestures on the work breakdown", () => {
  it("send nothing for an element the reading no longer holds", () => {
    const gone = row("Poste 1.1");
    expect(edited(DEFAULT, 0, { kind: "rename", row: gone }, "Armoires")).toBeUndefined();
    expect(edited(DEFAULT, 0, { kind: "delete", row: gone }, gone.label)).toBeUndefined();
    expect(edited(DEFAULT, 0, { kind: "add", parent: gone }, "Armoires")).toBeUndefined();
  });

  it("tell a deletion by the label the reading holds, not the one a row shows", () => {
    const stale = { ...row("Poste 1.1"), label: "Ancien libellé" };
    expect(edited(WHOLE, 1, { kind: "delete", row: stale }, stale.label)).toMatchObject({
      at: undefined,
      label: "Poste 1.1",
    });
  });

  it("point at the element renamed, and at the one added without an identifier", () => {
    expect(edited(WHOLE, 1, { kind: "rename", row: row("Poste 1.1") }, "Armoires")?.at).toBe(
      "/work_packages/0/order_items/0",
    );
    expect(edited(WHOLE, 1, { kind: "add", parent: row("Lot 1") }, "Poste 1.2")?.at).toBe(
      "/work_packages/0/order_items/1",
    );
  });
});

describe("the element a refusal points at", () => {
  const sent = edited(WHOLE, 1, { kind: "rename", row: row("Poste 1.1") }, "Armoires")?.sent ?? {
    work_packages: [],
    lock_version: 0,
  };

  it("is the deepest one whose pointer starts the field's", () => {
    expect(elementAt(sent, "/work_packages/0/order_items/0/label")).toEqual({
      kind: "order_item",
      label: "Armoires",
      pointer: "/work_packages/0/order_items/0",
    });
  });

  it("is the element itself when the pointer is its own", () => {
    expect(elementAt(sent, "/work_packages/0/order_items/0")).toMatchObject({
      kind: "order_item",
      pointer: "/work_packages/0/order_items/0",
    });
  });

  it("is none for a field of no element", () => {
    expect(elementAt(sent, "/lock_version")).toBeUndefined();
  });
});
