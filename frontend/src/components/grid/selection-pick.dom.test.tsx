// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, fakeClient } from "@/test/fixtures";
import { allShown } from "@/test/grid-preferences";

import type { GridConfig } from "./columns";
import { DenseGrid } from "./dense-grid";
import { ESTIMATE_GRID, type EstimateNode } from "./estimate";
import { type NodeList, type NodeSortColumn, type NodeTotals } from "./nodes";
import type { SelectionBarOptions } from "./selection-bar";

// The rows of a flat table picked one by one, all at once, and acted on from a bar (#2916/L4,
// WF-IHM-0040, WF-IHM-0100): through a flat configuration over the rows of the example.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/admin/users",
  useSearchParams: () => new URLSearchParams(""),
}));

const witness = example("nodes") as NodeList;
const ROWS = witness.items.slice(0, 5);
const FLAT: GridConfig<EstimateNode, NodeSortColumn, NodeTotals> = {
  key: "flat",
  name: "estimate",
  searched: true,
  rowKey: (node) => node.node_id,
  columns: ESTIMATE_GRID.columns.map((column) => ({ ...column, pinned: false })),
};
const DRAG = {
  bar: () => null,
  menu: () => null,
  drag: { accepts: () => false, drop: vi.fn() },
  busy: false,
};

function grid(
  selecting: SelectionBarOptions<EstimateNode> | undefined,
  config: GridConfig<EstimateNode, NodeSortColumn, NodeTotals> = FLAT,
  tree = false,
  stacked?: boolean,
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <DenseGrid
        config={config}
        rows={ROWS}
        totals={witness.totals}
        totalsCaption={() => "—"}
        query={{ sort: undefined, search: undefined, size: undefined }}
        preferences={allShown(ESTIMATE_GRID.columns)}
        selecting={selecting}
        stacked={stacked}
        commands={tree ? DRAG : undefined}
      />
    </NextIntlClientProvider>
  );
}

const handle = (row: number): HTMLElement => {
  const found = document.querySelector<HTMLElement>(
    `td[data-row="${row.toString()}"][data-column="row_number"]`,
  );
  if (found === null) {
    throw new Error(`no handle ${row.toString()}`);
  }
  return found;
};
const selected = (): number[] =>
  ROWS.flatMap((_, index) =>
    handle(index).closest("tr")?.getAttribute("aria-selected") === "true" ? [index] : [],
  );
const header = () => screen.getByRole("checkbox", { name: /toutes les lignes affichées/ });

beforeEach(() => {
  // happy-dom lays nothing out: the frame is given a box, so that the window of rows has rows.
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(600);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1400);
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("the rows of a flat table picked one by one [WF-IHM-0040-A] [WF-IHM-0100-A] #2916", () => {
  it("adds a row by Ctrl and a click and takes it off by another, and counts them in the status", () => {
    render(grid({}));
    fireEvent.click(handle(0));
    fireEvent.click(handle(2), { ctrlKey: true });
    expect(selected()).toEqual([0, 2]);
    expect(screen.getByRole("status")).toHaveTextContent("2 lignes sélectionnées");
    fireEvent.click(handle(0), { metaKey: true });
    expect(selected()).toEqual([2]);
    expect(screen.getByRole("status")).toHaveTextContent("1 ligne sélectionnée");
  });

  it("keeps the extent from the anchor for Shift and a click, and adds it for Ctrl+Shift", () => {
    render(grid({}));
    fireEvent.click(handle(1));
    fireEvent.click(handle(3), { shiftKey: true });
    expect(selected()).toEqual([1, 2, 3]);
    fireEvent.click(handle(0));
    fireEvent.click(handle(1), { ctrlKey: true });
    fireEvent.click(handle(4), { ctrlKey: true, shiftKey: true });
    expect(selected()).toEqual([0, 1, 2, 3, 4]);
  });

  it("toggles the row of the active cell by Ctrl and Space from the keyboard", async () => {
    const user = userEvent.setup();
    render(grid({}));
    act(() => {
      handle(0).focus();
    });
    await user.keyboard("{Control>} {/Control}");
    expect(selected()).toEqual([0]);
    await user.keyboard("{ArrowDown}{ArrowDown}{Control>} {/Control}");
    expect(selected()).toEqual([0, 2]);
    await user.keyboard("{Control>} {/Control}");
    expect(selected()).toEqual([0]);
    await user.keyboard("{Escape}");
    expect(selected()).toEqual([]);
  });

  it("has a box for all the rows shown: unchecked, mixed, checked", () => {
    render(grid({}));
    expect(header()).toHaveAttribute("aria-checked", "false");
    fireEvent.click(handle(0));
    expect(header()).toHaveAttribute("aria-checked", "mixed");
    fireEvent.click(header());
    expect(selected()).toEqual([0, 1, 2, 3, 4]);
    expect(header()).toHaveAttribute("aria-checked", "true");
    fireEvent.click(header());
    expect(selected()).toEqual([]);
    expect(header()).toHaveAttribute("aria-checked", "false");
  });

  it("shows the bar while a row is selected, with the count in the words of the screen, and lifts the selection by « Annuler la sélection »", () => {
    render(
      grid({
        label: (count) => `${count.toString()} comptes`,
        commands: (rows) => <button type="button">Agir sur {rows.length}</button>,
      }),
    );
    expect(screen.queryByRole("toolbar", { name: "Actions sur la sélection" })).toBeNull();
    fireEvent.click(handle(0));
    fireEvent.click(handle(3), { ctrlKey: true });
    const bar = screen.getByRole("toolbar", { name: "Actions sur la sélection" });
    expect(within(bar).getByText("2 comptes")).toBeVisible();
    expect(within(bar).getByRole("button", { name: "Agir sur 2" })).toBeVisible();
    fireEvent.click(within(bar).getByRole("button", { name: "Annuler la sélection" }));
    expect(selected()).toEqual([]);
    expect(screen.queryByRole("toolbar", { name: "Actions sur la sélection" })).toBeNull();
  });

  it("says « n lignes sélectionnées » when the screen gives no words", () => {
    render(grid({}));
    fireEvent.click(handle(0));
    fireEvent.click(handle(1), { ctrlKey: true });
    expect(
      within(screen.getByRole("toolbar", { name: "Actions sur la sélection" })).getByText(
        "2 lignes sélectionnées",
      ),
    ).toBeVisible();
  });

  it("drags nothing where the screen moves nothing", () => {
    render(grid({}));
    expect(handle(0)).toHaveAttribute("draggable", "false");
  });

  it("passes axe with a selection and its bar", async () => {
    const { container } = render(grid({}));
    fireEvent.click(handle(0));
    fireEvent.click(handle(2), { ctrlKey: true });
    await expectAccessible(container);
  });
});

describe("the grid that is a tree keeps the contiguous selection [WF-IHM-0040-A] #2916", () => {
  it("ignores Ctrl and a click, and has no box for all the rows", () => {
    render(grid({}, ESTIMATE_GRID, true));
    fireEvent.click(handle(0));
    fireEvent.click(handle(2), { ctrlKey: true });
    expect(selected()).toEqual([2]);
    expect(screen.queryByRole("checkbox", { name: /toutes les lignes/ })).toBeNull();
    expect(handle(0)).toHaveAttribute("draggable", "true");
  });
});

describe("the grid that offers no selection [WF-IHM-0040-A] #2916", () => {
  it("has no handle, no box and no bar by default", () => {
    render(grid(undefined));
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.queryByRole("toolbar", { name: "Actions sur la sélection" })).toBeNull();
    expect(document.querySelector('td[data-column="row_number"]')).toBeNull();
  });
});

describe("the room the bar of a selection takes above the grid #2916", () => {
  it("is measured again by a grid that takes the room left below it: the bar moves its top down [WF-IHM-0100-A]", () => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      top: 300,
    } as DOMRect);
    vi.stubGlobal("innerHeight", 900);
    vi.stubGlobal("scrollY", 0);
    const { container } = render(grid({}, FLAT, false, true));
    const scroller = container.querySelector<HTMLElement>(".max-h-svh");
    expect(scroller?.style.maxHeight).toBe("600px");
    // The bar, once a row is selected, takes a line above the frame, whose top goes down.
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      top: 336,
    } as DOMRect);
    fireEvent.click(handle(0));
    expect(scroller?.style.maxHeight).toBe("564px");
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      top: 300,
    } as DOMRect);
    fireEvent.click(
      within(screen.getByRole("toolbar", { name: "Actions sur la sélection" })).getByRole(
        "button",
        { name: "Annuler la sélection" },
      ),
    );
    expect(scroller?.style.maxHeight).toBe("600px");
    vi.unstubAllGlobals();
  });
});
