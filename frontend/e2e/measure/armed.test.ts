// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from "vitest";

import { armUsable, type Expected } from "./armed";

const REACHED = "wfTestReached";
const ARMED = "wfTestArmed";
const FRAME = 60;

const slot = window as unknown as Record<string, unknown>;

/** The grid of a planning compared, a row of three cells: the label, the end, the duration. */
function grid(cells: readonly [string, string, string]): void {
  document.body.innerHTML = `<table role="treegrid" aria-label="Planning"><tbody>
    <tr aria-rowindex="2">${cells.map((text) => `<td>${text}</td>`).join("")}</tr>
  </tbody></table>`;
}

/** The end read before the write is 01/02; the sign of a difference is looked for on the label. */
const EXPECTED: Expected = {
  grid: "Planning",
  cell: { row: 2, column: 1, differsFrom: "01/02", marked: 0 },
};

function arm(): void {
  slot[REACHED] = { drawn: () => true, hydrated: () => true, inWindow: () => true };
  armUsable({ reached: REACHED, armed: ARMED, expected: EXPECTED });
}

const frames = () => new Promise((resolve) => setTimeout(resolve, FRAME));

describe("the watch of a cell written in a grid compared", () => {
  afterEach(() => {
    // Stops the watch a test left running.
    slot[`${ARMED}:generation`] = null;
    document.body.innerHTML = "";
  });

  it("gives no signal once the end changed while the label bears no sign of a difference [WF-QUA-0060-A]", async () => {
    grid(["Tâche", "01/02", "3"]);
    arm();
    grid(["Tâche", "05/02", "4"]);
    await frames();
    expect(slot[ARMED]).toBeNull();
  });

  it("gives its signal once the end changed and the label bears the sign of a difference [WF-QUA-0060-A]", async () => {
    grid(["Tâche", "01/02", "3"]);
    arm();
    grid(["Tâche Δ", "05/02", "4"]);
    await frames();
    expect(slot[ARMED]).toEqual(expect.any(Number));
  });

  it("gives no signal while the sign shows but the end is the one read before [WF-QUA-0060-A]", async () => {
    grid(["Tâche", "01/02", "3"]);
    arm();
    grid(["Tâche Δ", "01/02", "4"]);
    await frames();
    expect(slot[ARMED]).toBeNull();
  });
});
