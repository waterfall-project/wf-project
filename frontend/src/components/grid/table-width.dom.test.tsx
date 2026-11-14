// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The width of a flat table, its lines and its totals, in CSS alone (US-2080, #3075, #3072): the
 * frame at the width of its card, the table the wider of the card and of its columns, the label
 * taking what the others leave, its width chosen its least; no line between the columns but beside
 * a pinned one; the row under the pointer tinted by a token; the caption of the totals spanning the
 * columns with no figure. The browser lays the table out: `grid-frame.spec.ts` measures it.
 */
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";
import { allShown } from "@/test/grid-preferences";

import type { GridConfig } from "./columns";
import { DenseGrid } from "./dense-grid";
import { ESTIMATE_GRID, type EstimateNode } from "./estimate";
import type { GridPreferences } from "./settings";
import { LABEL_COLUMN, type NodeList, type NodeSortColumn, type NodeTotals } from "./nodes";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

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
function grid(config: Config, preferences?: GridPreferences) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <DenseGrid
        config={config}
        rows={witness.items.slice(0, 3)}
        totals={witness.totals}
        totalsCaption={() => "3 lignes"}
        query={{ sort: undefined, search: undefined, size: undefined }}
        preferences={preferences ?? allShown(config.columns)}
      />
    </NextIntlClientProvider>
  );
}

/** Render a grid in a frame the test sizes, so that its rows are rendered, and what it reads of it. */
function renderGrid(config: Config, preferences?: GridPreferences) {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(400);
  const { container } = render(grid(config, preferences));
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
    const columns = [column("cost_category"), column("resource_role"), column("hours")];
    const { cols } = renderGrid(flat(columns));
    expect(cols.map((col) => col.style.width)).toEqual(["48px", "160px", "160px", ""]);
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
      expect(cell).toHaveClass("group-hover/row:bg-row-hover");
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
