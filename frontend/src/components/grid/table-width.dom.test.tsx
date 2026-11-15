// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The width of a flat table, its lines and its totals, in CSS alone (US-2080, #3075, #3072): the
 * frame at the width of its card, the table the wider of the card and of its columns, the label
 * taking what the others leave, its width chosen its least; no line between the columns but beside
 * a pinned one; the row under the pointer tinted by a token; the caption of the totals spanning the
 * columns with no figure. The browser lays the table out: `grid-frame.spec.ts` measures it.
 */
import { act, fireEvent, render, renderHook } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient, type FakeClient } from "@/test/fixtures";
import { allShown, PREFERENCES } from "@/test/grid-preferences";

import type { GridConfig } from "./columns";
import { DenseGrid } from "./dense-grid";
import { ESTIMATE_GRID, type EstimateNode } from "./estimate";
import { useGridTable } from "./grid-table";
import { type GridPreferences, WRITE_DELAY } from "./settings";
import { LABEL_COLUMN, type NodeList, type NodeSortColumn, type NodeTotals } from "./nodes";
import { stretchedColumn } from "./table-width";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

/** The client the fake back serves, to read its calls. */
function served(): FakeClient {
  return server.client as FakeClient;
}

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/reference/costs",
  useSearchParams: () => new URLSearchParams(""),
}));

beforeEach(() => {
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
});

afterEach(() => {
  vi.restoreAllMocks();
});

type Config = GridConfig<EstimateNode, NodeSortColumn, NodeTotals>;

const witness = example("nodes") as NodeList;

/** A flat table of the lines of the witness, under the columns given. */
function flat(columns: Config["columns"]): Config {
  return {
    key: "flat",
    name: "estimate",
    searched: true,
    rowKey: (node) => node.node_id,
    rowNumber: (node) => node.row_number,
    columns,
  };
}

/** A column of the estimate, by its key. */
function column(key: string): Config["columns"][number] {
  const found = ESTIMATE_GRID.columns.find((each) => each.key === key);
  if (found === undefined) {
    throw new Error(`no column ${key}`);
  }
  return found;
}

/** A grid of the witness, every column shown unless the preferences say otherwise. */
function grid(config: Config, preferences?: GridPreferences, caption = "3 lignes") {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <DenseGrid
        config={config}
        rows={witness.items.slice(0, 3)}
        totals={witness.totals}
        totalsCaption={() => caption}
        query={{ sort: undefined, search: undefined, size: undefined }}
        preferences={preferences ?? allShown(config.columns)}
      />
    </NextIntlClientProvider>
  );
}

/** Render a grid in a frame the test sizes, so that its rows are rendered, and what it reads of it. */
function renderGrid(config: Config, preferences?: GridPreferences, caption?: string) {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(400);
  const { container } = render(grid(config, preferences, caption));
  const table = container.querySelector("table");
  const frame = table?.parentElement;
  if (table === null || frame === null || frame === undefined) {
    throw new Error("no table");
  }
  return {
    frame,
    cols: Array.from(container.querySelectorAll("col")),
    totals: Array.from(container.querySelectorAll<HTMLElement>("tfoot td")),
    body: Array.from(container.querySelectorAll<HTMLElement>("tbody tr[aria-rowindex]")),
    handle: (key: string) => {
      const found = container.querySelector<HTMLElement>(
        `th[data-column='${key}'] [role='separator']`,
      );
      if (found === null) {
        throw new Error(`no handle for ${key}`);
      }
      return found;
    },
  };
}

describe("the width of a flat table (#3075)", () => {
  it("takes the width of its card, the table the wider of the card and of its columns, the label taking the rest [WF-IHM-0060-A]", () => {
    // The columns hidden and the widths chosen are found again: the width chosen for the label
    // becomes its least, the label taking the rest of the card.
    const preferences = { ...allShown(ESTIMATE_GRID.columns), column_widths: { label: 400 } };
    const { frame, cols } = renderGrid(ESTIMATE_GRID, preferences);
    expect(frame).toHaveClass("w-full");
    expect(frame).not.toHaveClass("w-fit");
    const widths = cols.map((col) => col.style.width);
    // The row numbers, then the label, which the fixed layout hands the room the others leave.
    expect(widths[1]).toBe("");
    expect(widths.filter((width) => width === "")).toHaveLength(1);
    const others = widths.reduce((total, width) => total + (Number.parseInt(width, 10) || 0), 0);
    const sum = others + 400;
    // The test document drops a width it cannot compute: the page as the server writes it says it.
    expect(renderToStaticMarkup(grid(ESTIMATE_GRID, preferences))).toContain(
      `style="width:max(100%, ${String(sum)}px)"`,
    );
  });

  it("lets the last column take the rest in a table without a label, every other keeping its width [WF-IHM-0060-A]", () => {
    const columns = [column("cost_category"), column("resource_role")];
    const { cols } = renderGrid(flat(columns));
    expect(cols.map((col) => col.style.width)).toEqual(["48px", "160px", ""]);
  });

  it("lets no column of figures take the rest, which would open before its figures, while another can [WF-IHM-0060-A]", () => {
    // The hours, last, are aligned at the end: the role before them takes the rest.
    const columns = [column("cost_category"), column("resource_role"), column("hours")];
    const { cols } = renderGrid(flat(columns));
    expect(cols.map((col) => col.style.width)).toEqual(["48px", "160px", "", "96px"]);
  });

  it("keeps a column the configuration does not hold a candidate to take the rest (#3281) [WF-IHM-0060-A]", () => {
    // The table shows a category, a role and the hours; a configuration that holds the hours alone
    // knows nothing of the alignment of the two others: the role, last before the figures, takes
    // the rest, never the hours, whose room would open before their figures.
    const table = flat([column("cost_category"), column("resource_role"), column("hours")]);
    const { result } = renderHook(() =>
      useGridTable({
        config: table,
        rows: witness.items.slice(0, 3),
        sort: undefined,
        onSort: vi.fn(),
        settings: { visibility: {}, sizing: {} },
        onSettings: vi.fn(),
      }),
    );
    expect(stretchedColumn(result.current, flat([column("hours")]))).toBe("resource_role");
    expect(stretchedColumn(result.current, table)).toBe("resource_role");
  });
});

describe("the handle of the column that takes the rest (#3075)", () => {
  // The label, chosen 200 wide, in a frame of 900 whose other columns take 48 + 160 + 96: it
  // shows the 596 points they leave it, under the 800 a column gets at its widest.
  const columns = [LABEL_COLUMN, column("cost_category"), column("hours")];
  const chosen = { ...allShown(columns), column_widths: { label: 200 } };
  const ROOM = 900;
  const REST = ROOM - (48 + 160 + 96);

  it("announces the width the label shows, and steps from it: no narrower than the rest of its card, wider by a step [WF-IHM-0060-A]", () => {
    vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(ROOM);
    const { handle } = renderGrid(flat(columns), chosen);
    const label = handle("label");
    expect(label).toHaveAttribute("aria-valuenow", String(REST));
    expect(label).toHaveAttribute("aria-valuemin", String(REST));
    // Narrower than what the others leave it, it would show the same: nothing changes.
    fireEvent.keyDown(label, { key: "ArrowLeft" });
    expect(label).toHaveAttribute("aria-valuenow", String(REST));
    // Wider, it widens from the edge seen, and the table passes its card.
    fireEvent.keyDown(label, { key: "ArrowRight" });
    expect(label).toHaveAttribute("aria-valuenow", String(REST + 16));
    expect(label).toHaveAttribute("aria-valuemin", String(REST));
    // Back by a step, it goes back to the rest of the card, and no further.
    fireEvent.keyDown(label, { key: "ArrowLeft" });
    fireEvent.keyDown(label, { key: "ArrowLeft" });
    expect(label).toHaveAttribute("aria-valuenow", String(REST));
  });

  it("drags the label from its visible edge, which follows the pointer down to the rest of its card [WF-IHM-0060-A]", () => {
    vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(ROOM);
    const { handle } = renderGrid(flat(columns), chosen);
    const label = handle("label");
    fireEvent.pointerDown(label, { button: 0, clientX: 1400, pointerId: 1 });
    fireEvent.pointerMove(label, { clientX: 1450, pointerId: 1 });
    expect(label).toHaveAttribute("aria-valuenow", String(REST + 50));
    // Fifty points left of where it was pressed: the label at the rest of its card, not at the
    // 150 points its width chosen less fifty would say.
    fireEvent.pointerMove(label, { clientX: 1350, pointerId: 1 });
    expect(label).toHaveAttribute("aria-valuenow", String(REST));
    fireEvent.pointerUp(label, { pointerId: 1 });
    fireEvent.pointerMove(label, { clientX: 1500, pointerId: 1 });
    expect(label).toHaveAttribute("aria-valuenow", String(REST));
  });

  it("announces the width chosen, and steps from it, before the room of its frame is known [WF-IHM-0060-A]", () => {
    const { handle } = renderGrid(flat(columns), chosen);
    const label = handle("label");
    expect(label).toHaveAttribute("aria-valuenow", "200");
    expect(label).toHaveAttribute("aria-valuemin", "40");
    fireEvent.keyDown(label, { key: "ArrowLeft" });
    expect(label).toHaveAttribute("aria-valuenow", "184");
  });

  it("lets the label no wider than the widest a column gets, nor writes a width it would not show [WF-IHM-0060-A]", () => {
    // In a frame of 1600, the label shows 1296 points, more than the 800 of its widest: its
    // handle cannot widen it, and narrowing it would show the same.
    vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
    const { handle } = renderGrid(flat(columns), chosen);
    const label = handle("label");
    expect(label).toHaveAttribute("aria-valuenow", "1296");
    expect(label).toHaveAttribute("aria-valuemax", "1296");
    fireEvent.keyDown(label, { key: "ArrowRight" });
    fireEvent.keyDown(label, { key: "ArrowLeft" });
    expect(label).toHaveAttribute("aria-valuenow", "1296");
  });

  it("writes nothing for a step that changes nothing on the screen: the width chosen stays (#3280) [WF-IHM-0060-A]", async () => {
    vi.useFakeTimers();
    try {
      vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(ROOM);
      const { handle } = renderGrid(flat(columns), chosen);
      const label = handle("label");
      // Chosen at 200, it shows the rest of its card: a step narrower shows the same.
      fireEvent.keyDown(label, { key: "ArrowLeft" });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(WRITE_DELAY * 2);
      });
      expect(label).toHaveAttribute("aria-valuenow", String(REST));
      expect(served().calls.filter((call) => call.route === PREFERENCES)).toEqual([]);
      // A step wider changes the screen, and is written once the grid has waited.
      fireEvent.keyDown(label, { key: "ArrowRight" });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(WRITE_DELAY * 2);
      });
      expect(served().calls.filter((call) => call.route === PREFERENCES)).toHaveLength(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("draws the axis of the column that takes the rest at its width chosen, before and after the room is measured (#3282) [WF-IHM-0060-A]", () => {
    vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(ROOM);
    const drawn: number[] = [];
    const axised = [
      {
        ...LABEL_COLUMN,
        axis: (width: number) => {
          drawn.push(width);
          return <span data-axis={width} />;
        },
      },
      column("cost_category"),
      column("hours"),
    ];
    const { handle } = renderGrid(flat(axised), chosen);
    // The room is measured: the label shows the rest of its card.
    expect(handle("label")).toHaveAttribute("aria-valuenow", String(REST));
    expect(drawn.length).toBeGreaterThan(0);
    expect(new Set(drawn)).toEqual(new Set([200]));
  });

  it("keeps the handle of every other column at the width chosen for it [WF-IHM-0060-A]", () => {
    vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(ROOM);
    const { handle } = renderGrid(flat(columns), chosen);
    expect(handle("cost_category")).toHaveAttribute("aria-valuenow", "160");
    expect(handle("cost_category")).toHaveAttribute("aria-valuemin", "40");
  });
});

describe("the lines and the tint of the rows of a grid (#3075)", () => {
  it("draws no line between the columns but beside the last one pinned, and tints the row under the pointer by its token [WF-IHM-0060-A]", () => {
    const { body } = renderGrid(ESTIMATE_GRID);
    const [row] = body;
    expect(row).toHaveClass("group/row", "h-7");
    const cells = Array.from(row?.querySelectorAll<HTMLElement>("td") ?? []);
    const lined = cells.filter((cell) => /\bborder-[rl]\b/.test(cell.className));
    // The label, pinned last at the start.
    expect(lined).toHaveLength(1);
    expect(lined[0]?.dataset.column).toBe("label");
    for (const cell of cells.filter((each) => !each.className.includes("bg-muted"))) {
      // On the card the table is set on, never the grey of the page (#3277).
      expect(cell).toHaveClass("bg-card", "group-hover/row:bg-row-hover");
      expect(cell).not.toHaveClass("bg-background");
    }
  });
});

describe("the caption of the totals (#3072)", () => {
  it("spans the columns after it with no figure, stuck over the pinned columns alone, its words at the start of its column [WF-IHM-0060-A]", () => {
    // The label pinned, then a category, a role and a quantity, which have no total, then the hours.
    const { totals } = renderGrid(ESTIMATE_GRID);
    const caption = totals.find((cell) => cell.textContent === "3 lignes");
    expect(caption).toHaveAttribute("colspan", "4");
    // Stuck, it ends where the label does: its offset less the 160 + 160 + 72 points it spans
    // that scroll; its words stick after the 48 points of the row numbers.
    expect(caption?.style.left).toBe(`${String(48 - 392)}px`);
    expect(caption).toHaveClass("sticky", "overflow-clip");
    expect(caption).not.toHaveClass("overflow-hidden", "text-ellipsis", "border-r");
    expect(caption?.querySelector("span")?.style.left).toBe("48px");
    // The hours, the first figure, are a cell of their own.
    expect(totals.find((cell) => cell.textContent === "0")).toHaveClass("text-right");
  });

  it("keeps a caption wider than the pinned columns stuck as they scroll, its words at the start of its column, cut by its own edge where the pinned columns end [WF-IHM-0060-A]", () => {
    // Decision 3 of #3072: scrolled, the caption ends where the label does, and its words, wider
    // than the label, are clipped there — never over the figures scrolled under it, never
    // ellipsed at the end of a cell that would scroll away.
    const long = "Trois lignes de l'estimation, sans compter les lots ni les postes repliés";
    const preferences = { ...allShown(ESTIMATE_GRID.columns), column_widths: { label: 40 } };
    const { totals } = renderGrid(ESTIMATE_GRID, preferences, long);
    const caption = totals.find((cell) => cell.textContent === long);
    expect(caption).toHaveAttribute("colspan", "4");
    expect(caption?.style.left).toBe(`${String(48 - 392)}px`);
    expect(caption).toHaveClass("sticky", "overflow-clip", "px-0");
    expect(caption).not.toHaveClass("overflow-hidden", "text-ellipsis", "truncate");
    const words = caption?.querySelector("span");
    expect(words?.style.left).toBe("48px");
    expect(words).toHaveClass("sticky", "w-fit");
    expect(words).not.toHaveClass("truncate", "text-ellipsis", "overflow-hidden");
  });

  it("spans pinned columns alone as one pinned cell, with the line beside the last [WF-IHM-0060-A]", () => {
    const columns = [LABEL_COLUMN, { ...column("cost_category"), pinned: true }, column("hours")];
    const { totals } = renderGrid(flat(columns));
    const caption = totals.find((cell) => cell.textContent === "3 lignes");
    expect(caption).toHaveAttribute("colspan", "2");
    expect(caption?.style.left).toBe("48px");
    expect(caption).toHaveClass("sticky", "border-r", "text-ellipsis");
    expect(caption?.querySelector("span")).toBeNull();
  });

  it("spans, unpinned, the columns with no figure, and scrolls with them [WF-IHM-0060-A]", () => {
    const columns = [
      { ...LABEL_COLUMN, pinned: false },
      column("cost_category"),
      column("hours"),
      column("resource_role"),
    ];
    const { totals } = renderGrid(flat(columns));
    const caption = totals.find((cell) => cell.textContent === "3 lignes");
    expect(caption).toHaveAttribute("colspan", "2");
    expect(caption?.style.left).toBe("");
    // The row numbers, the caption, the hours and the role: every column has its place.
    expect(totals).toHaveLength(4);
  });
});
