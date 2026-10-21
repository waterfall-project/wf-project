// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CommandOffer } from "@/components/commands/offer";
import { PlanningGrid } from "@/components/grid/planning-grid";
import { forgetMessages } from "@/components/notices/message-history";

import { expectAccessible } from "@/test/axe";
import {
  AVAILABLE,
  cache,
  cellAt,
  intl,
  NO_QUERY,
  STRUCTURE,
  CUSTOMER,
  DETAIL,
  MILESTONE,
  openMenu,
  openSubmenu,
  planning,
  planningGrid,
  REVIEW,
  router,
  select,
  sent,
  serve,
  server,
  STEERING,
  STUDIES,
  TIMELINES,
  TRACKING,
  timelines,
  prepareMenuTests,
} from "@/test/choice-menu";
import { example, held, type Problem } from "@/test/fixtures";

// The submenu « Chronologies » of the menu of a cell (US-0480), through the grid of the planning.
// The fake back keeps nothing: what a write sends is read from its calls, what it answers from the
// row it replaces. Some tests render a variant of a row of `nodes_planning`, passed to the grid as a
// prop and never served as an answer (guide, « Tests »), each saying what it changes.

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({
  refresh: () => {
    cache.refresh();
  },
}));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

prepareMenuTests(forgetMessages);

describe("the submenu « Chronologies » of a task", () => {
  it("lists the timelines of the project as boxes, checked where the task is inscribed, and the time/time tracking of a milestone [WF-PLA-0060-A]", async () => {
    // Une tâche peut être inscrite à une chronologie, ou en être retirée. Un jalon peut de la même
    // façon être inscrit au suivi temps/temps.
    serve();
    render(planningGrid());
    const task = await openSubmenu(STUDIES, "Chronologies");
    const boxes = within(task).getAllByRole("menuitemcheckbox");
    expect(boxes.map((box) => box.textContent)).toEqual(["Comité de pilotage", "Revue client"]);
    expect(boxes.map((box) => box.getAttribute("aria-checked"))).toEqual(["true", "false"]);
    await userEvent.keyboard("{Escape}{Escape}");
    const milestone = await openSubmenu(MILESTONE, "Chronologies");
    const marks = within(milestone).getAllByRole("menuitemcheckbox");
    expect(marks.map((box) => box.textContent)).toEqual([
      "Comité de pilotage",
      "Revue client",
      "Suivi temps/temps",
    ]);
    expect(marks.map((box) => box.getAttribute("aria-checked"))).toEqual(["true", "true", "true"]);
  });

  it("checks a timeline: sends the whole list of the inscriptions of the task with its version, and the row answered takes the place of the row read [WF-PLA-0060-A]", async () => {
    // Une tâche inscrite apparaît dans la chronologie et disparaît lorsqu'elle est retirée.
    const client = serve({ [TRACKING]: "node_tracked" });
    render(planningGrid());
    expect(cellAt(REVIEW, "timelines")).toHaveTextContent(/^$/);
    const menu = await openSubmenu(REVIEW, "Chronologies");
    await userEvent.click(within(menu).getByRole("menuitemcheckbox", { name: "Revue client" }));
    await waitFor(() => {
      expect(sent(client, TRACKING)).toHaveLength(1);
    });
    expect(sent(client, TRACKING)).toEqual([
      { entries: [{ kind: "timeline", timeline_id: CUSTOMER }], lock_version: 1 },
    ]);
    expect(client.calls.find((call) => call.route === TRACKING)?.path).toContain(
      `/nodes/${planning.items[REVIEW]?.node_id ?? ""}/tracking`,
    );
    // The row answered shows the timeline it is now inscribed to, and the grid is read anew.
    await waitFor(() => {
      expect(cellAt(REVIEW, "timelines")).toHaveTextContent("Revue client");
    });
    expect(
      await screen.findByText("Chronologies de « Revue de conception » mises à jour."),
    ).toBeInTheDocument();
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("unchecks a timeline: sends the inscriptions the task keeps, and none when it keeps none [WF-PLA-0060-A]", async () => {
    // Une tâche inscrite apparaît dans la chronologie et disparaît lorsqu'elle est retirée.
    const client = serve({ [TRACKING]: "node_tracked" });
    render(planningGrid());
    const menu = await openSubmenu(STUDIES, "Chronologies");
    await userEvent.click(
      within(menu).getByRole("menuitemcheckbox", { name: "Comité de pilotage" }),
    );
    await waitFor(() => {
      expect(sent(client, TRACKING)).toHaveLength(1);
    });
    expect(sent(client, TRACKING)).toEqual([{ entries: [], lock_version: 1 }]);
  });

  it("keeps the other inscriptions of a milestone when the time/time tracking is unchecked [WF-PLA-0060-A]", async () => {
    // Le diagramme temps/temps ne suit que les jalons inscrits.
    const client = serve({ [TRACKING]: "node_tracked" });
    render(planningGrid());
    const menu = await openSubmenu(MILESTONE, "Chronologies");
    await userEvent.click(
      within(menu).getByRole("menuitemcheckbox", { name: "Suivi temps/temps" }),
    );
    await waitFor(() => {
      expect(sent(client, TRACKING)).toHaveLength(1);
    });
    expect(sent(client, TRACKING)).toEqual([
      {
        entries: [
          { kind: "timeline", timeline_id: STEERING },
          { kind: "timeline", timeline_id: CUSTOMER },
        ],
        lock_version: 1,
      },
    ]);
  });

  it("offers the time/time tracking to a milestone alone, and the whole submenu to a task that names the inscriptions alone [WF-PLA-0060-A]", async () => {
    serve();
    const read = structuredClone(planning);
    const stripped = read.items[DETAIL];
    if (stripped !== undefined) {
      stripped.editable_fields = stripped.editable_fields.filter(
        (name) => name !== "task.tracking",
      );
    }
    render(planningGrid(read));
    const task = await openSubmenu(REVIEW, "Chronologies");
    expect(
      within(task)
        .getAllByRole("menuitemcheckbox")
        .map((box) => box.textContent),
    ).toEqual(["Comité de pilotage", "Revue client"]);
    await userEvent.keyboard("{Escape}{Escape}");
    const menu = await openMenu(DETAIL);
    expect(within(menu).queryByRole("menuitem", { name: "Chronologies" })).toBeNull();
  });

  it("offers no submenu in a grid read only, nor when the list of the timelines was refused [WF-PLA-0060-A]", async () => {
    serve();
    const view = render(planningGrid(planning, { editable: false }));
    fireEvent.contextMenu(cellAt(REVIEW, "label"), { clientX: 300, clientY: 200 });
    expect(screen.queryByRole("menuitem", { name: "Chronologies" })).toBeNull();
    view.unmount();
    render(planningGrid(planning, { named: null }));
    const menu = await openMenu(REVIEW);
    expect(within(menu).queryByRole("menuitem", { name: "Chronologies" })).toBeNull();
  });

  it("tells the refusal of the time/time tracking at the row, and writes nothing more [WF-PLA-0060-A]", async () => {
    const client = serve({
      [TRACKING]: {
        problem: example("node_tracking_milestone_refused") as Problem & { status: 422 },
      },
    });
    render(planningGrid());
    const menu = await openSubmenu(MILESTONE, "Chronologies");
    await userEvent.click(
      within(menu).getByRole("menuitemcheckbox", { name: "Suivi temps/temps" }),
    );
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Refusé à la ligne 6,");
    expect(alert).toHaveTextContent("Seul un jalon s’inscrit au suivi temps/temps.");
    expect(sent(client, TRACKING)).toHaveLength(1);
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("applies to each task of the selection, one write per task with its own version, the tasks that do not name the inscriptions left aside [WF-PLA-0060-A]", async () => {
    const read = structuredClone(planning);
    const [studies, detail, desks] = [read.items[STUDIES], read.items[DETAIL], read.items[2]];
    if (studies === undefined || detail === undefined || desks === undefined) {
      throw new Error("the example holds no such rows");
    }
    detail.lock_version = 4;
    desks.lock_version = 7;
    desks.editable_fields = desks.editable_fields.filter((name) => name !== "task.tracking");
    const client = serve({ [TRACKING]: "node_tracked" });
    render(planningGrid(read));
    await select(DETAIL, 2);
    const menu = await openSubmenu(DETAIL, "Chronologies");
    await userEvent.click(within(menu).getByRole("menuitemcheckbox", { name: "Revue client" }));
    await waitFor(() => {
      expect(sent(client, TRACKING)).toHaveLength(1);
    });
    expect(sent(client, TRACKING)).toEqual([
      { entries: [{ kind: "timeline", timeline_id: CUSTOMER }], lock_version: 4 },
    ]);
    expect(await screen.findByText(/mises à jour\./)).toBeInTheDocument();
  });

  it("applies to every task of the selection that names the inscriptions, each with its version [WF-PLA-0060-A]", async () => {
    const read = structuredClone(planning);
    const [detail, desks] = [read.items[DETAIL], read.items[2]];
    if (detail === undefined || desks === undefined) {
      throw new Error("the example holds no such rows");
    }
    detail.lock_version = 4;
    desks.lock_version = 7;
    const client = serve({ [TRACKING]: "node_tracked" });
    render(planningGrid(read));
    await select(DETAIL, 2);
    const menu = await openSubmenu(DETAIL, "Chronologies");
    await userEvent.click(within(menu).getByRole("menuitemcheckbox", { name: "Revue client" }));
    await waitFor(() => {
      expect(sent(client, TRACKING)).toHaveLength(2);
    });
    expect(sent(client, TRACKING)).toEqual([
      { entries: [{ kind: "timeline", timeline_id: CUSTOMER }], lock_version: 4 },
      { entries: [{ kind: "timeline", timeline_id: CUSTOMER }], lock_version: 7 },
    ]);
    expect(
      await screen.findByText(
        "Chronologies de « Études de détail » et d’une autre tâche mises à jour.",
      ),
    ).toBeInTheDocument();
  });

  it("offers to create a timeline in a project that has none, and inscribes the task to it [WF-PLA-0060-A]", async () => {
    const client = serve({
      [TIMELINES]: { example: "timeline_created", status: 201 },
      [TRACKING]: "node_tracked",
    });
    render(planningGrid(planning, { named: [] }));
    const menu = await openSubmenu(REVIEW, "Chronologies");
    expect(within(menu).queryAllByRole("menuitemcheckbox")).toHaveLength(0);
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Créer une chronologie…" }));
    const dialog = await screen.findByRole("dialog", { name: "Créer une chronologie" });
    // A label left blank creates nothing.
    await userEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    expect(within(dialog).getByRole("textbox", { name: "Libellé" })).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(sent(client, TIMELINES)).toHaveLength(0);
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Libellé" }), {
      target: { value: "Réunion de chantier" },
    });
    await userEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    await waitFor(() => {
      expect(sent(client, TRACKING)).toHaveLength(1);
    });
    expect(sent(client, TIMELINES)).toEqual([{ label: "Réunion de chantier" }]);
    expect(sent(client, TRACKING)).toEqual([
      {
        entries: [{ kind: "timeline", timeline_id: "01926f3a-7c00-7000-8000-000000001002" }],
        lock_version: 1,
      },
    ]);
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
  });

  it.each([
    ["lists it", AVAILABLE, true, false],
    ["does not list it", null, false, false],
    [
      "lists it unavailable",
      { is_available: false, missing_conditions: ["is_project_manager"] } satisfies CommandOffer,
      true,
      true,
    ],
  ] as const)(
    "offers the creation of a timeline as the project %s [WF-IHM-0090-A]",
    async (_, creation, shown, greyed) => {
      const client = serve({ [TIMELINES]: { example: "timeline_created", status: 201 } });
      render(planningGrid(planning, { named: [], creation }));
      const menu = await openSubmenu(MILESTONE, "Chronologies");
      const entry = within(menu).queryByRole("menuitem", { name: /Créer une chronologie…/ });
      expect(entry !== null).toBe(shown);
      if (entry === null) {
        return;
      }
      if (!greyed) {
        expect(entry).not.toHaveAttribute("aria-disabled");
        return;
      }
      // Unavailable, it is greyed out with what it lacks, and opens nothing.
      expect(entry).toHaveAttribute("aria-disabled", "true");
      expect(entry).toHaveTextContent("Condition non remplie : être chef de projet.");
      await userEvent.click(entry);
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(sent(client, TIMELINES)).toHaveLength(0);
    },
  );

  it("stops at the first refusal of a selection: the rows before it stay written, the ones after it are not written [WF-PLA-0060-A]", async () => {
    const client = serve({
      [TRACKING]: [
        "node_tracked",
        { problem: example("node_tracking_milestone_refused") as Problem & { status: 422 } },
        "node_tracked",
      ],
    });
    // The milestone is read inscribed to nothing, so that the write reaches it.
    const read = structuredClone(planning);
    const milestone = read.items[MILESTONE]?.task;
    if (milestone === undefined || milestone === null) {
      throw new Error("the example holds no such row");
    }
    milestone.tracking = [];
    render(planningGrid(read));
    await select(REVIEW, 5);
    const menu = await openSubmenu(REVIEW, "Chronologies");
    await userEvent.click(within(menu).getByRole("menuitemcheckbox", { name: "Revue client" }));
    const alert = await screen.findByRole("alert");
    const second = planning.items[MILESTONE]?.row_number ?? 0;
    expect(alert).toHaveTextContent(`Refusé à la ligne ${second.toString()},`);
    expect(sent(client, TRACKING)).toHaveLength(2);
    // The first row answered stands in its column; the third was never written.
    expect(cellAt(REVIEW, "timelines")).toHaveTextContent("Revue client");
    // The row at the index 5 names the inscriptions, so that it was left unwritten by the refusal, not
    // by the rule that sets a row aside.
    expect(planning.items[5]?.editable_fields).toContain("task.tracking");
    expect(cellAt(5, "timelines")).toHaveTextContent(/^$/);
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("sends nothing for a row already in the state a selection aims at [WF-PLA-0060-A]", async () => {
    // The milestone is inscribed to « Revue client » already, the review is not.
    const client = serve({ [TRACKING]: "node_tracked" });
    render(planningGrid());
    await select(REVIEW, MILESTONE);
    const menu = await openSubmenu(REVIEW, "Chronologies");
    await userEvent.click(within(menu).getByRole("menuitemcheckbox", { name: "Revue client" }));
    await waitFor(() => {
      expect(sent(client, TRACKING)).toHaveLength(1);
    });
    expect(client.calls.find((call) => call.route === TRACKING)?.path).toContain(
      planning.items[REVIEW]?.node_id ?? "",
    );
    expect(await screen.findByText(/mises à jour\./)).toBeInTheDocument();
    expect(sent(client, TRACKING)).toHaveLength(1);
  });

  it("keeps the menu open and sends nothing when a box is checked while a write is under way [WF-PLA-0060-A]", async () => {
    // The write is held: the grid is busy until it is let go.
    const hold = held();
    const client = serve({ [TRACKING]: "node_tracked" }, hold.timing);
    render(planningGrid());
    const first = await openSubmenu(REVIEW, "Chronologies");
    await userEvent.click(within(first).getByRole("menuitemcheckbox", { name: "Revue client" }));
    await waitFor(() => {
      expect(sent(client, TRACKING)).toHaveLength(1);
    });
    const again = await openSubmenu(REVIEW, "Chronologies");
    await userEvent.click(
      within(again).getByRole("menuitemcheckbox", { name: "Comité de pilotage" }),
    );
    expect(screen.getByRole("menu", { name: "Chronologies" })).toBeInTheDocument();
    expect(sent(client, TRACKING)).toHaveLength(1);
    hold.release();
    await screen.findByText(/mises à jour\./);
  });

  it("is reached and checked from the keyboard alone, the focus coming back to the cell [WF-PLA-0060-A]", async () => {
    const client = serve({ [TRACKING]: "node_tracked" });
    render(planningGrid());
    const cell = cellAt(REVIEW, "label");
    await userEvent.click(cell);
    await userEvent.keyboard("{Shift>}{F10}{/Shift}");
    const menu = await screen.findByRole("menu", { name: "Menu de la cellule" });
    for (let step = 0; step < 20; step += 1) {
      if (document.activeElement?.textContent === "Chronologies") {
        break;
      }
      await userEvent.keyboard("{ArrowDown}");
    }
    expect(document.activeElement).toHaveTextContent("Chronologies");
    expect(menu).toContainElement(document.activeElement as HTMLElement);
    await userEvent.keyboard("{ArrowRight}");
    await screen.findByRole("menu", { name: "Chronologies" });
    await userEvent.keyboard("{ArrowDown}");
    expect(document.activeElement).toHaveTextContent("Revue client");
    await userEvent.keyboard(" ");
    await waitFor(() => {
      expect(sent(client, TRACKING)).toHaveLength(1);
    });
    expect(sent(client, TRACKING)).toEqual([
      { entries: [{ kind: "timeline", timeline_id: CUSTOMER }], lock_version: 1 },
    ]);
    await screen.findByText(/mises à jour\./);
    // Whatever the menu left open is closed by Escape, and the focus is back in the grid.
    await userEvent.keyboard("{Escape}{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("menu")).toBeNull();
    });
    await waitFor(() => {
      expect(cell).toHaveFocus();
    });
  });

  it("breaks no rule of accessibility, in the submenu nor in the dialog that creates a timeline [WF-PLA-0060-A]", async () => {
    serve();
    render(planningGrid(planning, { named: [] }));
    const menu = await openSubmenu(MILESTONE, "Chronologies");
    await expectAccessible(menu);
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Créer une chronologie…" }));
    const dialog = await screen.findByRole("dialog", { name: "Créer une chronologie" });
    await expectAccessible(dialog);
  });

  it("breaks no rule of accessibility where the creation of a timeline is unavailable, with the condition it lacks [WF-PLA-0060-A]", async () => {
    serve();
    const missing: CommandOffer = {
      is_available: false,
      missing_conditions: ["is_project_manager"],
    };
    render(planningGrid(planning, { named: [], creation: missing }));
    const menu = await openSubmenu(MILESTONE, "Chronologies");
    const entry = within(menu).getByRole("menuitem", { name: /Créer une chronologie…/ });
    expect(entry).toHaveAttribute("aria-disabled", "true");
    expect(entry).toHaveTextContent("Condition non remplie : être chef de projet.");
    await expectAccessible(menu);
  });

  it("starts with the column « Chronologies » hidden, and shows it from the menu of the columns [WF-PLA-0060-A]", () => {
    serve({ "PATCH /me/preferences": "preferences" });
    const view = render(
      intl(
        <PlanningGrid
          nodes={planning}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{ kinds: ["task"] }}
          query={NO_QUERY}
          preferences={undefined}
          timelines={timelines}
        />,
      ),
    );
    expect(screen.queryByRole("columnheader", { name: "Chronologies" })).toBeNull();
    view.unmount();
    render(planningGrid());
    expect(screen.getByRole("columnheader", { name: "Chronologies" })).toBeInTheDocument();
    // The names of the timelines, and the time/time tracking, in a column that reads only.
    expect(cellAt(MILESTONE, "timelines")).toHaveTextContent(
      "Comité de pilotage, Revue client, Suivi temps/temps",
    );
    expect(cellAt(MILESTONE, "timelines")).toHaveAttribute("aria-readonly", "true");
  });
});
