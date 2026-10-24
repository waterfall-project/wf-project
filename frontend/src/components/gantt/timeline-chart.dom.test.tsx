// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { WRITE_DELAY } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import type { TimelineTask } from "./timeline";
import { TimelineChart } from "./timeline-chart";

// The server of Next, as far as the frieze needs it: the preferences it records.
const server = vi.hoisted((): { client: (ApiClient & FakeClient) | undefined } => ({
  client: undefined,
}));
vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

const STEERING = "01926f3a-7c00-7000-8000-000000001000";

/** The rows of the studies and of the control station of the core, by their number in the plan. */
function rows(...numbers: number[]): TimelineTask[] {
  const items = (example("nodes_core") as { items: TimelineTask[] }).items;
  return numbers.map((number) => {
    const row = items.find((item) => item.row_number === number);
    if (row === undefined) {
      throw new Error(`no row ${String(number)} in nodes_core`);
    }
    return row;
  });
}

/** The row of the core with a number in the plan. */
function rowOf(number: number): TimelineTask {
  const [row] = rows(number);
  if (row === undefined) {
    throw new Error(`no row ${String(number)}`);
  }
  return row;
}

// The studies, the detailed studies, the design review, the reception of the studies — a
// milestone —, the design file and the control station. Stacked in the order of the plan: the
// studies in the first lane, the detailed studies and the design review in the second, the design
// file — which overlaps the studies and the detailed studies — in the third, the control station in
// the first, after the studies.
const STUDIES = rows(1, 2, 5, 6, 7, 8);

/** The frieze of the steering committee over tasks, the lanes kept given. */
function friezeOf(tasks: readonly TimelineTask[], kept?: Readonly<Record<string, number>>) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TimelineChart
        name="Comité de pilotage"
        timeline={STEERING}
        tasks={tasks}
        kept={kept}
        scope="timelines:test"
      />
    </NextIntlClientProvider>
  );
}

/** Render the frieze of the steering committee over tasks, the lanes kept given. */
function renderFrieze(
  tasks: readonly TimelineTask[] = STUDIES,
  kept?: Readonly<Record<string, number>>,
) {
  return render(friezeOf(tasks, kept));
}

/** A task of the core with other dates, an identity and a name of its own. */
function dated(
  row: TimelineTask,
  nodeId: string,
  label: string,
  start: string,
  finish = start,
): TimelineTask {
  const task = row.task;
  if (task?.start == null || task.finish == null) {
    throw new Error("a row without dates");
  }
  return {
    ...row,
    node_id: nodeId,
    task: {
      ...task,
      label,
      start: { ...task.start, date: start },
      finish: { ...task.finish, date: finish },
    },
  };
}

/** The frieze, the one stop of the keyboard. */
function frieze(): HTMLElement {
  return screen.getByRole("group", {
    name: /^Frise de la chronologie «\s+Comité de pilotage\s+»$/,
  });
}

/** The rectangle of a task, by the start of its name. */
function rectangle(label: string): HTMLElement {
  return screen.getByRole("img", { name: new RegExp(`^${label}, du `) });
}

/** The lanes the frieze recorded, in the order it recorded them. */
function recorded(): unknown[] {
  return (server.client?.calls ?? [])
    .filter((call) => call.route === "PATCH /me/preferences")
    .map((call) => (call.body as { timelines?: Record<string, unknown> }).timelines?.[STEERING]);
}

/** The node of a task of the core, by its number in the plan. */
function node(number: number): string {
  return rows(number)[0]?.node_id ?? "";
}

beforeEach(() => {
  window.sessionStorage.clear();
  server.client = fakeClient({ "PATCH /me/preferences": "preferences_timeline_lanes" });
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1000);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the frieze of a timeline", () => {
  // aucune exigence : propre à l'US (US-0530, la frise et ses couloirs).
  it("draws each task as a rectangle named by its task, its dates and its lane, its name cut short and whole in its tooltip", () => {
    renderFrieze();
    expect(rectangle("Études")).toHaveAccessibleName(
      "Études, du 02/03/2026 au 24/04/2026, couloir 1",
    );
    expect(rectangle("Études de détail")).toHaveAccessibleName(
      "Études de détail, du 02/03/2026 au 10/04/2026, couloir 2",
    );
    expect(rectangle("Revue de conception")).toHaveAccessibleName(/couloir 2$/);
    expect(rectangle("Dossier de conception")).toHaveAccessibleName(/couloir 3$/);
    expect(rectangle("Poste de commande")).toHaveAccessibleName(/couloir 1$/);
    // The name is cut short by the rectangle, and whole in its tooltip.
    const named = rectangle("Dossier de conception");
    expect(named).toHaveAttribute("title", "Dossier de conception");
    expect(named).toHaveTextContent("Dossier de conception");
  });

  it("draws a milestone as a line across the frieze, named by its task and its date, written at its foot", () => {
    renderFrieze();
    const milestone = screen.getByRole("img", {
      name: "Réception des études, jalon le 24/04/2026",
    });
    expect(milestone.querySelector("line")).not.toBeNull();
    expect(milestone).toHaveTextContent("Réception des études");
    expect(milestone).toHaveTextContent("24/04/2026");
    // Far from the edges of the axis, its name is centred on its line.
    expect(milestone.querySelector("foreignObject")).toHaveAttribute("x", "-64");
  });

  // aucune exigence : propre à l'US (US-0530, le nom d'un jalon au bord de l'axe).
  it("holds the name of a milestone at the edge of the axis within the frame, anchored inwards", () => {
    const studies = rowOf(1);
    const milestone = rowOf(6);
    renderFrieze([
      studies,
      dated(milestone, "01926f3a-7c00-7000-8000-00000000a001", "Ouverture", "2026-03-02"),
      dated(milestone, "01926f3a-7c00-7000-8000-00000000a002", "Clôture", "2026-07-30"),
    ]);
    const first = screen.getByRole("img", { name: /^Ouverture, jalon/ });
    const last = screen.getByRole("img", { name: /^Clôture, jalon/ });
    expect(first.querySelector("foreignObject")).toHaveAttribute("x", "0");
    expect(first.querySelector("foreignObject > div")).toHaveClass("text-left");
    expect(last.querySelector("foreignObject")).toHaveAttribute("x", "-128");
    expect(last.querySelector("foreignObject > div")).toHaveClass("text-right");
  });

  it("keeps the lanes the account placed the rectangles in, and stacks the others around them", () => {
    renderFrieze(STUDIES, { [node(8)]: 1 });
    expect(rectangle("Poste de commande")).toHaveAccessibleName(/couloir 2$/);
    expect(rectangle("Études de détail")).toHaveAccessibleName(/couloir 2$/);
  });

  it("moves a rectangle down by Alt and the down arrow, past a lane where it would overlap, and records the lanes shown after a pause", async () => {
    const user = userEvent.setup();
    renderFrieze();
    // After the zoom in, out and fitted, and the automatic layout, already shown: unavailable, each
    // stays reached, to say why in its tooltip (US-0580).
    for (let press = 0; press < 5; press += 1) {
      await user.tab();
    }
    expect(frieze()).toHaveFocus();
    // The left and right arrows go from rectangle to rectangle: the third is the design review.
    await user.keyboard("{ArrowRight}{ArrowRight}");
    expect(frieze()).toHaveAttribute("aria-activedescendant", rectangle("Revue de conception").id);
    // The third lane holds the design file, which it overlaps: it goes to the empty one below.
    await user.keyboard("{Alt>}{ArrowDown}{/Alt}");
    expect(rectangle("Revue de conception")).toHaveAccessibleName(/couloir 4$/);
    expect(screen.getByRole("status")).toHaveTextContent(
      "« Revue de conception » est dans le couloir 4.",
    );
    // Nothing else moved.
    expect(rectangle("Études de détail")).toHaveAccessibleName(/couloir 2$/);
    await waitFor(
      () => {
        expect(recorded()).toEqual([
          {
            lanes: {
              [node(5)]: 3,
              [node(1)]: 0,
              [node(2)]: 1,
              [node(7)]: 2,
              [node(8)]: 0,
            },
          },
        ]);
      },
      { timeout: WRITE_DELAY * 4 },
    );
  });

  it("refuses by the keyboard a lane where the rectangle would overlap another, says it, and moves nothing", async () => {
    renderFrieze();
    frieze().focus();
    fireEvent.keyDown(frieze(), { key: "ArrowRight" });
    // The detailed studies overlap the studies, in the only lane above.
    fireEvent.keyDown(frieze(), { key: "ArrowUp", altKey: true });
    expect(rectangle("Études de détail")).toHaveAccessibleName(/couloir 2$/);
    expect(screen.getByRole("status")).toHaveTextContent(
      "« Études de détail » chevaucherait « Études » dans le couloir 1 : elle reste dans le couloir 2.",
    );
    // The first lane is the top: nothing goes above it.
    fireEvent.keyDown(frieze(), { key: "Home" });
    fireEvent.keyDown(frieze(), { key: "ArrowUp", altKey: true });
    expect(screen.getByRole("status")).toHaveTextContent(
      "« Études » est déjà dans le premier couloir.",
    );
    await new Promise((resolve) => setTimeout(resolve, WRITE_DELAY * 2));
    expect(recorded()).toEqual([]);
  });

  it("moves a rectangle by dragging it to another lane with the mouse, and refuses a drop where it would overlap", () => {
    renderFrieze();
    const file = rectangle("Dossier de conception");
    // The drawing starts at the top of the window in the simulated document: a lane is 32 points.
    fireEvent.pointerDown(file, { button: 0, pointerId: 1, clientY: 2 * 32 + 10 });
    fireEvent.pointerMove(file, { pointerId: 1, clientY: 32 + 10 });
    // Over the second lane, where it would overlap the detailed studies: the drop is refused.
    expect(file).toHaveClass("border-destructive");
    fireEvent.pointerUp(file, { pointerId: 1, clientY: 32 + 10 });
    expect(rectangle("Dossier de conception")).toHaveAccessibleName(/couloir 3$/);
    expect(screen.getByRole("status")).toHaveTextContent(
      "« Dossier de conception » chevaucherait « Études de détail » dans le couloir 2",
    );
    // The control station, dropped in the second lane, fits there.
    const station = rectangle("Poste de commande");
    fireEvent.pointerDown(station, { button: 0, pointerId: 2, clientY: 10 });
    fireEvent.pointerMove(station, { pointerId: 2, clientY: 32 + 10 });
    fireEvent.pointerUp(station, { pointerId: 2, clientY: 32 + 10 });
    expect(rectangle("Poste de commande")).toHaveAccessibleName(/couloir 2$/);
    expect(screen.getByRole("status")).toHaveTextContent(
      "« Poste de commande » est dans le couloir 2.",
    );
  });

  it("gives back the automatic layout, which the account forgets", async () => {
    const user = userEvent.setup();
    renderFrieze(STUDIES, { [node(8)]: 1 });
    await user.click(screen.getByRole("button", { name: "Disposition automatique" }));
    expect(rectangle("Poste de commande")).toHaveAccessibleName(/couloir 1$/);
    expect(screen.getByRole("button", { name: "Disposition automatique" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    await waitFor(
      () => {
        expect(recorded()).toEqual([null]);
      },
      { timeout: WRITE_DELAY * 4 },
    );
  });

  it("has a name, names each rectangle and milestone, and gives a reading as a table [WF-IHM-0100-A]", async () => {
    const { container } = renderFrieze();
    expect(screen.getByRole("figure", { name: "Comité de pilotage" })).toContainElement(frieze());
    const table = screen.getByRole("table", { name: "Lecture en table" });
    const lines = within(table)
      .getAllByRole("row")
      .map((row) => [...row.querySelectorAll("td, th")].map((cell) => cell.textContent));
    expect(lines).toEqual([
      ["N°", "Libellé", "Début", "Fin", "Couloir"],
      ["1", "Études", "02/03/2026", "24/04/2026", "1"],
      ["2", "Études de détail", "02/03/2026", "10/04/2026", "2"],
      ["5", "Revue de conception", "13/04/2026", "24/04/2026", "2"],
      ["6", "Réception des études", "24/04/2026", "24/04/2026", "Jalon"],
      ["7", "Dossier de conception", "09/04/2026", "15/04/2026", "3"],
      ["8", "Poste de commande", "04/05/2026", "30/06/2026", "1"],
    ]);
    await expectAccessible(container);
  });

  it("scrolls the axis to the rectangle the keyboard reaches, so that the focus stays in view [WF-IHM-0100-A]", async () => {
    // Le focus reste visible.
    const user = userEvent.setup();
    const { container } = renderFrieze();
    await user.click(screen.getByRole("button", { name: "Zoom avant" }));
    await user.click(screen.getByRole("button", { name: "Zoom avant" }));
    const axis = container.querySelector<HTMLElement>(".overflow-x-auto");
    const drawing = container.querySelector<SVGElement>("figure svg.block");
    expect(axis).not.toBeNull();
    frieze().focus();
    // The zoom centred the axis: Home brings the first rectangle back in view.
    await user.keyboard("{Home}");
    const atFirst = axis?.scrollLeft ?? -1;
    expect(atFirst).toBeLessThan(100);
    // The last rectangle lies beyond the frame of a zoomed axis: End scrolls to it.
    await user.keyboard("{End}");
    expect(frieze()).toHaveAttribute("aria-activedescendant", rectangle("Poste de commande").id);
    const scrolled = axis?.scrollLeft ?? 0;
    expect(scrolled).toBeGreaterThan(0);
    expect(drawing?.style.transform).toBe(`translateX(-${String(scrolled)}px)`);
    // Home brings the first back, and Alt and an arrow keep the active one in view too.
    await user.keyboard("{Home}");
    expect(axis?.scrollLeft).toBe(atFirst);
    await user.keyboard("{End}");
    if (axis !== null) {
      axis.scrollLeft = 0;
    }
    fireEvent.keyDown(frieze(), { key: "ArrowDown", altKey: true });
    expect(axis?.scrollLeft).toBe(scrolled);
  });

  // aucune exigence : propre à l'US (US-0530, l'avis relu d'un refus répété).
  it("says again a refusal that repeats, the sentence replaced in the live region", () => {
    renderFrieze();
    frieze().focus();
    fireEvent.keyDown(frieze(), { key: "Home" });
    fireEvent.keyDown(frieze(), { key: "ArrowUp", altKey: true });
    const first = screen.getByText("« Études » est déjà dans le premier couloir.");
    fireEvent.keyDown(frieze(), { key: "ArrowUp", altKey: true });
    const second = screen.getByText("« Études » est déjà dans le premier couloir.");
    expect(second).not.toBe(first);
    expect(first).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toContainElement(second);
  });

  // aucune exigence : propre à l'US (US-0530, les couloirs au-delà de ce que le compte garde).
  it("keeps every lane on the screen past the sixty-four the account keeps, and sends sixty-four", async () => {
    const template = rowOf(1);
    const day = (n: number) => new Date(Date.UTC(2026, 0, 1 + 2 * n)).toISOString().slice(0, 10);
    const node = (n: number) => `01926f3a-7c00-7000-8000-${String(n).padStart(12, "0")}`;
    // Seventy tasks that overlap none: 64 of them placed in the second lane, the others stacked.
    const many = Array.from({ length: 70 }, (_, n) =>
      dated(template, node(n + 1), `Tâche ${String(n + 1)}`, day(n)),
    );
    const placed = Object.fromEntries(many.slice(0, 64).map((each) => [each.node_id, 1]));
    renderFrieze(many, placed);
    const lane = (n: number) =>
      screen.getByRole("img", { name: new RegExp(`^Tâche ${String(n)}, du `) });
    expect(lane(64)).toHaveAccessibleName(/couloir 2$/);
    expect(lane(66)).toHaveAccessibleName(/couloir 1$/);
    frieze().focus();
    fireEvent.keyDown(frieze(), { key: "End" });
    for (let press = 0; press < 5; press += 1) {
      fireEvent.keyDown(frieze(), { key: "ArrowLeft" });
    }
    expect(frieze()).toHaveAttribute("aria-activedescendant", lane(65).id);
    fireEvent.keyDown(frieze(), { key: "ArrowDown", altKey: true });
    expect(lane(65)).toHaveAccessibleName(/couloir 2$/);
    // The others stay where they were drawn.
    expect(lane(64)).toHaveAccessibleName(/couloir 2$/);
    expect(lane(66)).toHaveAccessibleName(/couloir 1$/);
    expect(lane(1)).toHaveAccessibleName(/couloir 2$/);
    await waitFor(
      () => {
        expect(recorded()).toHaveLength(1);
      },
      { timeout: WRITE_DELAY * 4 },
    );
    expect(Object.keys((recorded()[0] as { lanes: object }).lanes)).toHaveLength(64);
  });

  // aucune exigence : propre à l'US (US-0530, le rectangle actif d'une frise qui change de tâches).
  it("keeps the keyboard alive when the tasks change under the rectangle it was on", () => {
    const { rerender } = renderFrieze([]);
    rerender(friezeOf(STUDIES));
    expect(frieze()).toHaveAttribute("aria-activedescendant", rectangle("Études").id);
    frieze().focus();
    fireEvent.keyDown(frieze(), { key: "ArrowRight" });
    expect(frieze()).toHaveAttribute("aria-activedescendant", rectangle("Études de détail").id);
    // The task the keyboard was on is read out of the timeline: the first of the others is active.
    rerender(friezeOf(rows(7, 8)));
    expect(frieze()).toHaveAttribute(
      "aria-activedescendant",
      rectangle("Dossier de conception").id,
    );
    fireEvent.keyDown(frieze(), { key: "ArrowRight" });
    expect(frieze()).toHaveAttribute("aria-activedescendant", rectangle("Poste de commande").id);
  });

  // aucune exigence : propre à l'US (US-0530, un glisser qu'Échap abandonne).
  it("gives up a drag at Escape: the rectangle goes back to its lane and nothing is written", async () => {
    renderFrieze();
    const file = rectangle("Dossier de conception");
    fireEvent.pointerDown(file, { button: 0, pointerId: 1, clientY: 2 * 32 + 10 });
    fireEvent.pointerMove(file, { pointerId: 1, clientY: 3 * 32 + 10 });
    fireEvent.keyDown(frieze(), { key: "Escape" });
    fireEvent.pointerMove(file, { pointerId: 1, clientY: 3 * 32 + 10 });
    fireEvent.pointerUp(file, { pointerId: 1, clientY: 3 * 32 + 10 });
    expect(rectangle("Dossier de conception")).toHaveAccessibleName(/couloir 3$/);
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    await new Promise((resolve) => setTimeout(resolve, WRITE_DELAY * 2));
    expect(recorded()).toEqual([]);
  });
});
