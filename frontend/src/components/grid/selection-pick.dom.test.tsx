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
import { closeMenu, openMenu, menuButton } from "@/test/check-menu";
import { allShown } from "@/test/grid-preferences";

import type { GridConfig } from "./columns";
import { DenseGrid } from "./dense-grid";
import { ESTIMATE_GRID, type EstimateNode } from "./estimate";
import { type NodeList, type NodeSortColumn, type NodeTotals } from "./nodes";
import { CheckMenu } from "./check-menu";
import type { Filtering } from "./filter-bar";
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
  rows: readonly EstimateNode[] = ROWS,
  filtering?: Filtering,
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <DenseGrid
        config={config}
        rows={rows}
        totals={witness.totals}
        totalsCaption={() => "—"}
        query={{ sort: undefined, search: undefined, size: undefined }}
        preferences={allShown(ESTIMATE_GRID.columns)}
        selecting={selecting}
        filtering={filtering}
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
  [...document.querySelectorAll<HTMLElement>('td[data-column="row_number"]')].flatMap(
    (cell, index) => (cell.closest("tr")?.getAttribute("aria-selected") === "true" ? [index] : []),
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

  it("toggles the row of the active cell by Space alone, as a listbox that takes several does, and by Ctrl and Space too", async () => {
    const user = userEvent.setup();
    render(grid({}));
    act(() => {
      handle(0).focus();
    });
    await user.keyboard(" ");
    expect(selected()).toEqual([0]);
    await user.keyboard("{ArrowDown}{ArrowDown} ");
    expect(selected()).toEqual([0, 2]);
    await user.keyboard("{Control>} {/Control}");
    expect(selected()).toEqual([0]);
    await user.keyboard("{Escape}");
    expect(selected()).toEqual([]);
  });

  it("selects all the rows shown by Ctrl+A from the column of the handles, the box of the header then checked", async () => {
    const user = userEvent.setup();
    render(grid({}));
    act(() => {
      handle(1).focus();
    });
    await user.keyboard("{Control>}a{/Control}");
    expect(selected()).toEqual([0, 1, 2, 3, 4]);
    expect(header()).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Toutes les lignes affichées sont sélectionnées",
    );
  });

  it("extends the selection by Shift and an arrow, from the anchor", async () => {
    const user = userEvent.setup();
    render(grid({}));
    act(() => {
      handle(1).focus();
    });
    await user.keyboard(" {Shift>}{ArrowDown}{ArrowDown}{/Shift}");
    expect(selected()).toEqual([1, 2, 3]);
  });

  it("says in its status that none is selected after a removal, and that all are, and tells the box of the header on Space", async () => {
    const user = userEvent.setup();
    render(grid({}));
    const status = screen.getByRole("status");
    act(() => {
      handle(0).focus();
    });
    await user.keyboard(" ");
    expect(status).toHaveTextContent("1 ligne sélectionnée");
    await user.keyboard(" ");
    expect(status).toHaveTextContent("Aucune ligne sélectionnée");
    const head = document.querySelector<HTMLElement>('th[data-column="row_number"]');
    act(() => {
      head?.focus();
    });
    await user.keyboard(" ");
    expect(status).toHaveTextContent("Toutes les lignes affichées sont sélectionnées");
    expect(header()).toHaveAttribute("aria-checked", "true");
    await user.keyboard(" ");
    expect(status).toHaveTextContent("Aucune ligne sélectionnée");
    expect(header()).toHaveAttribute("aria-checked", "false");
  });

  it("keeps the extent from the anchor for Shift and a click after a selection that is not contiguous", () => {
    render(grid({}));
    fireEvent.click(handle(0));
    fireEvent.click(handle(2), { ctrlKey: true });
    fireEvent.click(handle(4), { shiftKey: true });
    expect(selected()).toEqual([2, 3, 4]);
  });

  it("says it takes several rows, and gives the focus back to the active cell once the selection is cancelled", () => {
    render(grid({}));
    expect(document.querySelector("[aria-multiselectable=true]")).not.toBeNull();
    act(() => {
      handle(2).focus();
    });
    fireEvent.click(handle(2));
    fireEvent.click(
      within(screen.getByRole("group", { name: "Actions sur la sélection" })).getByRole("button", {
        name: "Annuler la sélection",
      }),
    );
    expect(selected()).toEqual([]);
    expect(handle(2)).toHaveFocus();
  });

  it("thins the selection to the rows a reading anew still shows, and lifts it when none is, on a page or a sort that changes", () => {
    const { rerender } = render(grid({}));
    fireEvent.click(handle(0));
    fireEvent.click(handle(2), { ctrlKey: true });
    fireEvent.click(handle(4), { ctrlKey: true });
    // Rows 0 and 2 go: only the fifth is left, now the third.
    rerender(grid({}, FLAT, false, undefined, [ROWS[1], ROWS[3], ROWS[4]] as EstimateNode[]));
    expect(selected()).toEqual([2]);
    expect(screen.getByRole("status")).toHaveTextContent("1 ligne sélectionnée");
    rerender(grid({}, FLAT, false, undefined, [ROWS[1], ROWS[3]] as EstimateNode[]));
    expect(selected()).toEqual([]);
    expect(screen.queryByRole("group", { name: "Actions sur la sélection" })).toBeNull();
    // An anchor that is gone: Shift and a click select alone.
    rerender(grid({}));
    fireEvent.click(handle(0));
    rerender(grid({}, FLAT, false, undefined, ROWS.slice(1)));
    fireEvent.click(handle(2), { shiftKey: true });
    expect(selected()).toEqual([2]);
  });

  it("makes the box of the header unavailable where the grid shows no row", () => {
    render(grid({}, FLAT, false, undefined, []));
    expect(header()).toBeDisabled();
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
    expect(screen.queryByRole("group", { name: "Actions sur la sélection" })).toBeNull();
    fireEvent.click(handle(0));
    fireEvent.click(handle(3), { ctrlKey: true });
    const bar = screen.getByRole("group", { name: "Actions sur la sélection" });
    expect(within(bar).getByText("2 comptes")).toBeVisible();
    expect(within(bar).getByRole("button", { name: "Agir sur 2" })).toBeVisible();
    fireEvent.click(within(bar).getByRole("button", { name: "Annuler la sélection" }));
    expect(selected()).toEqual([]);
    expect(screen.queryByRole("group", { name: "Actions sur la sélection" })).toBeNull();
  });

  it("says « n lignes sélectionnées » when the screen gives no words", () => {
    render(grid({}));
    fireEvent.click(handle(0));
    fireEvent.click(handle(1), { ctrlKey: true });
    expect(
      within(screen.getByRole("group", { name: "Actions sur la sélection" })).getByText(
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
    expect(screen.queryByRole("group", { name: "Actions sur la sélection" })).toBeNull();
    expect(document.querySelector('td[data-column="row_number"]')).toBeNull();
  });
});

describe("the bar of a selection lies over the bar of the grid #2916", () => {
  it("moves nothing: the frame of the rows keeps its height and the bar of the grid is hidden and inert meanwhile [WF-IHM-0100-A]", () => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      top: 300,
    } as DOMRect);
    vi.stubGlobal("innerHeight", 900);
    vi.stubGlobal("scrollY", 0);
    const { container } = render(grid({}, FLAT, false, true));
    const scroller = container.querySelector<HTMLElement>(".max-h-svh");
    const wrapper = container.querySelector<HTMLElement>("[class~=gap-2]");
    expect(scroller?.style.maxHeight).toBe("600px");
    const before = wrapper?.style.minHeight;
    fireEvent.click(handle(0));
    expect(scroller?.style.maxHeight).toBe("600px");
    expect(wrapper?.style.minHeight).toBe(before);
    const bar = screen.getByRole("group", { name: "Actions sur la sélection" });
    expect(bar.className).toContain("absolute");
    expect(container.querySelector("[inert]")).not.toBeNull();
    vi.unstubAllGlobals();
  });
});

describe("the grid that is a tree keeps its keyboard #2916", () => {
  it("takes Space as a selection alone, and neither Ctrl and Space nor Ctrl+A", async () => {
    const user = userEvent.setup();
    render(grid({}, ESTIMATE_GRID, true));
    act(() => {
      handle(0).focus();
    });
    await user.keyboard(" ");
    expect(selected()).toEqual([0]);
    await user.keyboard("{ArrowDown}{Control>} {/Control}");
    expect(selected()).toEqual([0]);
    await user.keyboard("{Control>}a{/Control}");
    expect(selected()).toEqual([0]);
  });
});

const cancel = () =>
  within(screen.getByRole("group", { name: "Actions sur la sélection" })).getByRole("button", {
    name: "Annuler la sélection",
  });
const inGrid = (element: Element | null) =>
  element !== null && document.querySelector("table")?.contains(element) === true;

describe("the bar of the grid covered by the bar of the selection #2916", () => {
  it("gives the focus back to the active cell when it was in the bar of the grid as the selection came", () => {
    render(grid({}));
    const search = screen.getByRole("searchbox");
    act(() => {
      search.focus();
    });
    expect(search).toHaveFocus();
    fireEvent.click(handle(1));
    expect(search).not.toHaveFocus();
    expect(inGrid(document.activeElement)).toBe(true);
  });

  it("keeps the search typed while the bar is covered, and shows it again when the selection is lifted", async () => {
    const user = userEvent.setup();
    render(grid({}));
    await user.type(screen.getByRole("searchbox"), "câble");
    fireEvent.click(handle(0));
    fireEvent.click(cancel());
    expect(screen.getByRole("searchbox")).toHaveValue("câble");
    expect(screen.getByRole("searchbox").closest("[inert]")).toBeNull();
  });

  it("is reached by Shift and Tab from the grid, lifts the selection on Escape and gives the focus back to the active cell", async () => {
    const user = userEvent.setup();
    render(grid({}));
    await user.click(handle(2));
    await user.tab({ shift: true });
    expect(cancel()).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(selected()).toEqual([]);
    expect(inGrid(document.activeElement)).toBe(true);
  });

  it("gives the focus back to the grid when the selection is emptied by a command of the screen, the bar gone with the focus in it", async () => {
    const user = userEvent.setup();
    let empty: () => void = () => undefined;
    render(
      grid({
        commands: () => (
          <button
            type="button"
            onClick={() => {
              empty();
            }}
          >
            Vider
          </button>
        ),
      }),
    );
    await user.click(handle(1));
    // The command of the screen empties the selection by the box of the header, as a click would.
    empty = () => {
      fireEvent.click(header());
    };
    await user.click(header());
    expect(selected()).toEqual([0, 1, 2, 3, 4]);
    const command = screen.getByRole("button", { name: "Vider" });
    act(() => {
      command.focus();
    });
    await user.click(command);
    expect(selected()).toEqual([]);
    expect(inGrid(document.activeElement)).toBe(true);
  });

  it("scrolls in a narrow window rather than wrap: its height stays that of the bar it covers", () => {
    render(grid({}));
    fireEvent.click(handle(0));
    const bar = screen.getByRole("group", { name: "Actions sur la sélection" });
    expect(bar.className).toContain("overflow-x-auto");
    expect(bar.innerHTML).not.toContain("flex-wrap");
    expect(bar.firstElementChild?.className).toContain("min-w-full");
  });
});

describe("the box of all the rows #2916", () => {
  it("describes its state, which changes as the rows are selected", () => {
    render(grid({}));
    const described = () =>
      document.getElementById(header().getAttribute("aria-describedby") ?? "")?.textContent;
    expect(described()).toBe("Aucune ligne n’est sélectionnée");
    fireEvent.click(handle(0));
    expect(described()).toBe("Une partie des lignes affichées est sélectionnée");
    fireEvent.click(header());
    expect(described()).toBe("Toutes les lignes affichées sont sélectionnées");
  });

  it("is selected by Ctrl+A from any cell of the grid but one entered", async () => {
    const user = userEvent.setup();
    render(grid({}));
    const cell = document.querySelector<HTMLElement>('td[data-row="2"][data-column="label"]');
    act(() => {
      cell?.focus();
    });
    await user.keyboard("{Control>}a{/Control}");
    expect(selected()).toEqual([0, 1, 2, 3, 4]);
  });
});

describe("the bar of the selection over a bar that folds filters #2916", () => {
  it("covers the line of the bar alone: the open panel and the chips stay visible and active, and the frame does not move [WF-IHM-0100-A]", async () => {
    const user = userEvent.setup();
    const used = vi.fn();
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      top: 300,
    } as DOMRect);
    vi.stubGlobal("innerHeight", 900);
    vi.stubGlobal("scrollY", 0);
    const filtering: Filtering = {
      panel: (
        <button type="button" onClick={used}>
          Filtre du panneau
        </button>
      ),
      chips: [{ key: "origins", name: "Origine", value: "Local", params: ["origins"] }],
    };
    const { container } = render(grid({}, FLAT, false, true, ROWS, filtering));
    await user.click(screen.getByRole("button", { name: /^Filtres/ }));
    const scroller = container.querySelector<HTMLElement>(".max-h-svh");
    const before = scroller?.style.maxHeight;
    expect(before).not.toBe("");
    await user.click(handle(0));
    expect(selected()).toEqual([0]);
    expect(scroller?.style.maxHeight).toBe(before);
    // Only the line is covered: hidden and inert, the search and the button of the filters with it.
    const line = container.querySelector("[data-grid-toolbar]");
    expect(line).toHaveAttribute("inert");
    expect(line?.closest("[data-folded]")).not.toBeNull();
    const panel = screen.getByRole("button", { name: "Filtre du panneau" });
    expect(panel.closest("[inert]")).toBeNull();
    await user.click(panel);
    expect(used).toHaveBeenCalledTimes(1);
    const chips = screen.getByText("Origine", { exact: false });
    expect(chips.closest("[inert]")).toBeNull();
    // The bar of the selection has the width of the line it covers.
    const bar = screen.getByRole("group", { name: "Actions sur la sélection" });
    const folded = line?.closest<HTMLElement>("[data-folded]");
    expect(bar.style.width).not.toBe("");
    expect(bar.style.width).toBe(folded?.style.width);
    vi.unstubAllGlobals();
  });
});

describe("the menu of a filter with a selection #2916", () => {
  it("opens and closes over a selection without lifting it, the focus back to its button, while the panel is open under the bar of the selection", async () => {
    const user = userEvent.setup();
    const changed = vi.fn();
    const filtering: Filtering = {
      panel: (
        <CheckMenu
          label="État"
          every="Tous les états"
          options={[{ value: "a", text: "Actif" }]}
          chosen={[]}
          multiple
          onChange={changed}
        />
      ),
      chips: [],
    };
    render(grid({}, FLAT, false, undefined, ROWS, filtering));
    await user.click(screen.getByRole("button", { name: /^Filtres/ }));
    await user.click(handle(1));
    fireEvent.click(handle(3), { ctrlKey: true });
    const list = await openMenu("État");
    await user.click(within(list).getByRole("checkbox", { name: "Actif" }));
    expect(changed).toHaveBeenCalledTimes(1);
    await closeMenu();
    expect(menuButton("État")).toHaveFocus();
    expect(screen.getByRole("group", { name: "Actions sur la sélection" })).toBeVisible();
    expect(selected()).toEqual([1, 3]);
  });
});
