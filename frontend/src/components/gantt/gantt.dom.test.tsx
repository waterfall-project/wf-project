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
  window.sessionStorage.clear();
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
  // aucune exigence : propre à l'US (US-0530, l'axe à deux rangées).
  it("is the last column of the grid, its axis the months over the weeks of the tasks, named by its heading", () => {
    renderPlanning();
    const grid = screen.getByRole("treegrid", { name: "Grille de planning" });
    const headers = within(grid).getAllByRole("columnheader");
    expect(headers.at(-1)).toHaveAccessibleName("Gantt");
    // Fitted to the project, two months in 400 points: the months over the Mondays of the weeks.
    const axis = [...(headers.at(-1)?.querySelectorAll("text") ?? [])].map((t) => t.textContent);
    expect(axis).toEqual([
      "mars 2026",
      "avril 2026",
      "2",
      "9",
      "16",
      "23",
      "30",
      "6",
      "13",
      "20",
      "27",
    ]);
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
    expect(headers.at(-1)?.textContent).toContain("March 2026");
  });

  it("draws nothing outside a grid of the planning", () => {
    const { container } = render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <GanttCell row={planning.items[0] ?? { node_id: "none" }} />
      </NextIntlClientProvider>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  // aucune exigence : propre à l'US (US-0530, la colonne du Gantt épinglée et sa poignée).
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

  // aucune exigence : propre à l'US (US-0530, la colonne du Gantt épinglée et sa poignée).
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

  // aucune exigence : propre à l'US (US-0530, la colonne du Gantt épinglée et sa poignée).
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

  it("zooms by the buttons of its header, by Ctrl and plus or minus in the grid, by Ctrl and the wheel on the Gantt, and modifies no task [WF-PLA-0090-A]", async () => {
    renderPlanning();
    const header = screen.getAllByRole("columnheader").at(-1);
    if (header === undefined) {
      throw new Error("no header");
    }
    // In the corner of the header of the Gantt, out of its name and of the order of tabulation.
    const zoomIn = within(header).getByRole("button", { name: "Zoom avant" });
    expect(zoomIn).toHaveAttribute("tabindex", "-1");
    expect(header).toHaveAccessibleName("Gantt");
    await userEvent.click(zoomIn);
    // The weeks over their days, the drawing wider than its column, which scrolls it.
    expect(header.textContent).toContain("9 mars 2026");
    expect(ganttOf("Études").querySelector("svg")).toHaveStyle({ width: "1464px" });
    expect(screen.getByRole("button", { name: "Zoom avant" })).toBeDisabled();
    ganttOf("Études").focus();
    await userEvent.keyboard("{Control>}-{/Control}");
    expect(header.textContent).toContain("avril 2026");
    expect(ganttOf("Études").querySelector("svg")).toHaveStyle({ width: "366px" });
    // happy-dom keeps no modifier key of a wheel event: Ctrl is held by hand.
    const wheel = new WheelEvent("wheel", { deltaY: 100, bubbles: true, cancelable: true });
    Object.defineProperty(wheel, "ctrlKey", { value: true });
    fireEvent(ganttOf("Études").querySelector("svg") ?? document.body, wheel);
    expect(wheel.defaultPrevented).toBe(true);
    expect(header.textContent).toContain("T1 2026");
    await userEvent.click(screen.getByRole("button", { name: "Ajuster au projet" }));
    expect(ganttOf("Études").querySelector("svg")?.style.width).toBe("");
    // Nothing is written: the grid asked the server nothing, its preferences included.
    expect(server.client?.calls).toEqual([]);
  });

  it("zooms by the menu of a cell too, where a narrow bar has no room for its buttons [WF-PLA-0090-A]", async () => {
    renderPlanning();
    fireEvent.contextMenu(ganttOf("Études"), { clientX: 300, clientY: 200 });
    const menu = await screen.findByRole("menu");
    expect(within(menu).getByRole("menuitem", { name: "Ajuster au projet" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Zoom avant" }));
    expect(ganttOf("Études").querySelector("svg")?.style.width).not.toBe("");
    expect(server.client?.calls).toEqual([]);
  });

  // aucune exigence : propre à l'US (US-0530, la molette sur le Gantt zoomé).
  it("lets a wheel mostly downward scroll the grid, though it drifts aside, and scrolls itself by a wheel across", async () => {
    renderPlanning();
    await userEvent.click(screen.getByRole("button", { name: "Zoom avant" }));
    const drawing = ganttOf("Études").querySelector("svg") ?? document.body;
    const down = new WheelEvent("wheel", {
      deltaY: 100,
      deltaX: 3,
      bubbles: true,
      cancelable: true,
    });
    fireEvent(drawing, down);
    expect(down.defaultPrevented).toBe(false);
    const across = new WheelEvent("wheel", {
      deltaY: 3,
      deltaX: 100,
      bubbles: true,
      cancelable: true,
    });
    fireEvent(drawing, across);
    expect(across.defaultPrevented).toBe(true);
  });

  // aucune exigence : propre à l'US (US-0530, la molette sur le Gantt zoomé).
  it("removes its wheel listener when it unmounts", () => {
    const removed = vi.spyOn(HTMLElement.prototype, "removeEventListener");
    const { unmount } = renderPlanning();
    unmount();
    expect(removed.mock.calls.some(([type]) => type === "wheel")).toBe(true);
    removed.mockRestore();
  });

  // aucune exigence : propre à l'US (US-0530, le niveau gardé pour la session).
  it("keeps its level for the session, by grid and by revision, and opens fitted to the project", async () => {
    const first = renderPlanning();
    expect(screen.getByRole("button", { name: "Ajuster au projet" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Zoom arrière" }));
    first.unmount();
    renderPlanning();
    expect(screen.getAllByRole("columnheader").at(-1)?.textContent).toContain("T1 2026");
    expect(screen.getByRole("button", { name: "Ajuster au projet" })).toBeEnabled();
    expect(
      window.sessionStorage.getItem(`waterfall.gantt.zoom.planning:${STRUCTURE.revision_id}`),
    ).toBe("1");
  });

  it("is accessible", async () => {
    const { container } = renderPlanning();
    await expectAccessible(container);
  });
});
