// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { NodeList, NodeSortColumn } from "@/components/grid/nodes";
import { PlanningGrid } from "@/components/grid/planning-grid";
import type { GridQuery } from "@/components/grid/query";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import { WRITE_DELAY } from "@/components/grid/settings";

import { GanttCell } from "./gantt";

// The server of Next, as far as the grid needs it: the preferences it records.
const server = vi.hoisted((): { client: (ApiClient & FakeClient) | undefined } => ({
  client: undefined,
}));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// The studies of the witness, without their lines (`nodes_planning`).
const planning = example("nodes_planning") as NodeList;

/** Render the grid of the planning, its Gantt last, in a language. */
function renderPlanning(locale: Locale = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <PlanningGrid
        nodes={planning}
        structure={STRUCTURE}
        structureVersion={1}
        filters={{}}
        query={NO_QUERY}
        preferences={undefined}
        undoable
      />
    </NextIntlClientProvider>,
  );
}

/** The cell of the Gantt in the row of a label. */
function ganttOf(label: string): HTMLElement {
  const row = screen
    .getAllByRole("row")
    .find((candidate) => candidate.querySelectorAll("td")[1]?.textContent === label);
  const cell = row?.querySelector<HTMLElement>('td[data-column="gantt"]');
  if (cell === undefined || cell === null) {
    throw new Error(`no Gantt in the row of ${label}`);
  }
  return cell;
}

/** The handle on the left edge of the Gantt, which splits the table from it. */
function splitHandle(): HTMLElement {
  return screen.getByRole("separator", { name: "Largeur de la colonne Gantt" });
}

/** The widths of the columns of the planning the grid recorded, in the order it recorded them. */
function recordedWidths(): unknown[] {
  return (server.client?.calls ?? [])
    .filter((call) => call.route === "PATCH /me/preferences")
    .map(
      (call) =>
        (call.body as { grids?: { planning?: { column_widths?: unknown } } }).grids?.planning
          ?.column_widths,
    );
}

beforeEach(() => {
  router.push.mockReset();
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  // The frame of the grid at its widest: 1 400 points wide, less 200 of borders and scroll bar.
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1400);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the Gantt of the planning", () => {
  it("is the last column of the grid, its axis the months of the tasks, named by its heading", () => {
    renderPlanning();
    const grid = screen.getByRole("treegrid", { name: "Grille de planning" });
    const headers = within(grid).getAllByRole("columnheader");
    expect(headers.at(-1)).toHaveAccessibleName("Gantt");
    expect(headers.at(-1)?.textContent).toContain("mars 26");
    expect(headers.at(-1)?.textContent).toContain("avr. 26");
  });

  it("names each bar by the dates the API gives, a milestone by its day, the critical path in words [WF-PLA-0090-A]", () => {
    renderPlanning();
    const bar = (label: string) => within(ganttOf(label)).getByRole("img");
    expect(bar("Études")).toHaveAccessibleName("Du 02/03/2026 au 24/04/2026");
    expect(bar("Études de détail")).toHaveAccessibleName("Du 02/03/2026 au 10/04/2026 — critique");
    expect(bar("Pupitres opérateurs")).toHaveAccessibleName("Du 02/03/2026 au 24/04/2026");
    expect(bar("Réception des études")).toHaveAccessibleName("Jalon le 24/04/2026 — critique");
    expect(bar("Dossier de conception")).toHaveAccessibleName("Du 09/04/2026 au 15/04/2026");
  });

  it("shows the hierarchy, the links and the critical path by the drawing, never by a colour alone [WF-PLA-0090-A]", () => {
    renderPlanning();
    // A summary is a bracket of three bars; a milestone a diamond; a task a bar, filled on the
    // critical path, an outline off it.
    expect(ganttOf("Études").querySelectorAll("g.fill-foreground rect")).toHaveLength(3);
    expect(
      ganttOf("Réception des études").querySelector("polygon.fill-destructive"),
    ).not.toBeNull();
    expect(ganttOf("Études de détail").querySelector("rect.fill-destructive")).not.toBeNull();
    expect(ganttOf("Dossier de conception").querySelector("rect.fill-background")).not.toBeNull();
    // The review is reached by the link from the detailed studies, which leaves them and passes
    // by the desks between: the stretch along, and the arrow at the end.
    const arrows = (label: string) => ganttOf(label).querySelectorAll("g > svg > polygon").length;
    expect(arrows("Revue de conception")).toBe(1);
    expect(arrows("Réception des études")).toBe(2);
    expect(arrows("Études de détail")).toBe(0);
    expect(ganttOf("Pupitres opérateurs").querySelectorAll("g line").length).toBeGreaterThan(0);
  });

  it("modifies no task, from the pointer or the keyboard, its handle included [WF-PLA-0090-A]", async () => {
    renderPlanning();
    // The handle that splits the table from the Gantt widens the Gantt, and touches no task.
    const handle = splitHandle();
    fireEvent.pointerDown(handle, { button: 0, clientX: 500, pointerId: 1 });
    fireEvent.pointerMove(handle, { clientX: 450, pointerId: 1 });
    fireEvent.pointerUp(handle, { pointerId: 1 });
    await userEvent.keyboard("{ArrowLeft}{Enter}{Delete}");
    expect(handle).toHaveAttribute("aria-valuenow", "466");
    const cell = ganttOf("Revue de conception");
    expect(cell).toHaveAttribute("aria-readonly", "true");
    expect(within(cell).getByRole("img")).toHaveClass("pointer-events-none");
    await userEvent.click(cell);
    expect(cell).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await userEvent.keyboard("{F2}");
    await userEvent.keyboard("12");
    await userEvent.keyboard("{Delete}");
    // No entry opens, nothing is written: the grid asked the server nothing.
    expect(screen.queryByRole("textbox", { name: "Gantt" })).toBeNull();
    expect(server.client?.calls.filter((call) => call.route !== "PATCH /me/preferences")).toEqual(
      [],
    );
    expect(within(cell).getByRole("img")).toHaveAccessibleName(
      "Du 13/04/2026 au 24/04/2026 — critique",
    );
  });

  it("writes its dates and its axis in English too", () => {
    renderPlanning("en");
    expect(within(ganttOf("Réception des études")).getByRole("img")).toHaveAccessibleName(
      "Milestone on 24/04/2026 — critical",
    );
    const headers = screen.getAllByRole("columnheader");
    expect(headers.at(-1)?.textContent).toContain("Mar 26");
  });

  it("draws nothing outside a grid of the planning", () => {
    const { container } = render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <GanttCell row={planning.items[0] ?? { node_id: "none" }} />
      </NextIntlClientProvider>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("is pinned at the end of the grid, over the columns before it, which scroll out from under it", () => {
    renderPlanning();
    const header = screen.getAllByRole("columnheader").at(-1);
    for (const cell of [header, ganttOf("Études")]) {
      expect(cell).toHaveStyle({ right: "0px" });
      expect(cell).toHaveClass("sticky", "border-l");
    }
    // Only the Gantt: the label stays pinned at the start, the description is not pinned.
    expect(screen.getByRole("columnheader", { name: "Libellé" }).style.right).toBe("");
    const description = ganttOf("Études").parentElement?.querySelector(
      'td[data-column="description"]',
    );
    expect(description).not.toHaveClass("sticky");
    const frame = screen.getByRole("treegrid", { name: "Grille de planning" }).parentElement;
    expect(frame).toHaveStyle({ scrollPaddingInlineEnd: "400px" });
    // Its handle is on its left edge, where it meets the table.
    expect(header).toContainElement(splitHandle());
    expect(splitHandle()).toHaveClass("left-0");
  });

  it("widens by its handle up to the room of the frame less the columns pinned at the start and the widest between, and narrows down to the narrowest column", () => {
    renderPlanning();
    const handle = splitHandle();
    // 1 200 points of room — the holder of the frame, less its borders and its scroll bar —, less
    // the row numbers (48) and the label (240), and the widest column between, where the active
    // cell shows (160).
    expect(handle).toHaveAttribute("aria-valuemax", "752");
    fireEvent.pointerDown(handle, { button: 0, clientX: 500, pointerId: 1 });
    fireEvent.pointerMove(handle, { clientX: 300, pointerId: 1 });
    expect(handle).toHaveAttribute("aria-valuenow", "600");
    fireEvent.pointerMove(handle, { clientX: -2000, pointerId: 1 });
    expect(handle).toHaveAttribute("aria-valuenow", "752");
    fireEvent.pointerMove(handle, { clientX: 5000, pointerId: 1 });
    expect(handle).toHaveAttribute("aria-valuenow", "40");
    fireEvent.pointerUp(handle, { pointerId: 1 });
    // Released, the pointer moves the split no more.
    fireEvent.pointerMove(handle, { clientX: 0, pointerId: 1 });
    expect(handle).toHaveAttribute("aria-valuenow", "40");
  });

  it("widens by Shift and the left arrow on its header, narrows by the right, and keeps its width in the preferences of the grid", async () => {
    renderPlanning();
    screen.getAllByRole("columnheader").at(-1)?.focus();
    await userEvent.keyboard("{Shift>}{ArrowLeft}{ArrowLeft}{ArrowRight}{/Shift}");
    expect(splitHandle()).toHaveAttribute("aria-valuenow", "416");
    await waitFor(
      () => {
        expect(recordedWidths()).toEqual([{ gantt: 416 }]);
      },
      { timeout: WRITE_DELAY * 4 },
    );
  });

  it("is accessible", async () => {
    const { container } = renderPlanning();
    await expectAccessible(container);
  });
});
