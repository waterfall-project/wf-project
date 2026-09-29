// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import {
  act,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { startTransition } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
} from "@/test/fixtures";

import type { GridConfig } from "./columns";
import { DenseGrid, ROW_REM } from "./dense-grid";
import {
  ESTIMATE_GRID,
  type Node,
  type NodeList,
  type NodeSortColumn,
  type NodeTotals,
} from "./estimate";
import { EstimateGrid } from "./estimate-grid";
import type { GridQuery } from "./query";
import { type GridPreferences, useSettingsWriter, WRITE_DELAY } from "./settings";

// The server of Next, as far as the grid needs it: the fake back behind serverClient, which the
// server action recording the settings calls; the router, whose address a sort or a search
// changes; and the address of the page.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ pathname: "/projects/p/revisions/r", search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => page.pathname,
  useSearchParams: () => new URLSearchParams(page.search),
}));

const PREFERENCES = "PATCH /me/preferences";
const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined };
// The height of a row at the default size of the root font, and of the element that scrolls,
// as a browser would lay it out: twenty rows.
const ROW_HEIGHT = ROW_REM * 16;
const VIEW = 20 * ROW_HEIGHT;

const witness = example("nodes") as NodeList;

/** Serve the fake back, and give it back to read its calls. */
function serve(
  answers: FakeAnswers = { [PREFERENCES]: "preferences" },
  timing: FakeTiming = {},
): FakeClient {
  const client = fakeClient(answers, timing);
  server.client = client;
  return client;
}

/** The bodies sent to record preferences. */
function recorded(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === PREFERENCES).map((call) => call.body);
}

/** Render the grid of the estimate on an answer, in a language. */
function renderGrid(
  nodes: NodeList,
  options: {
    readonly query?: GridQuery<NodeSortColumn>;
    readonly preferences?: GridPreferences;
    readonly locale?: Locale;
  } = {},
) {
  const locale = options.locale ?? "fr";
  const grid = (query: GridQuery<NodeSortColumn>) => (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <EstimateGrid nodes={nodes} query={query} preferences={options.preferences} />
    </NextIntlClientProvider>
  );
  const rendered = render(grid(options.query ?? NO_QUERY));
  return {
    ...rendered,
    /** Render the grid again, as the page does once the server answered a new address. */
    ask: (query: GridQuery<NodeSortColumn>) => {
      rendered.rerender(grid(query));
    },
  };
}

/** The grid of the estimate. */
function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Grille de devis" });
}

/** The element that scrolls the grid. */
function scroller(): HTMLElement {
  const element = grid().parentElement;
  if (element === null) {
    throw new Error("the grid has no container");
  }
  return element;
}

/** The row at an index among all the rows of the grid — `1` for the header. */
function rowAt(index: number): HTMLElement | undefined {
  return screen
    .queryAllByRole("row")
    .find((row) => row.getAttribute("aria-rowindex") === String(index));
}

/** The rows of the answer rendered, between the header and the totals. */
function bodyRows(): HTMLElement[] {
  const rows = screen.getAllByRole("row");
  return rows.slice(1, -1);
}

/** The texts of the cells of a row. */
function texts(row: HTMLElement | undefined): string[] {
  return [...(row?.querySelectorAll("td, th") ?? [])].map((cell) => cell.textContent);
}

/** The label of each row of the answer rendered. */
function labels(): string[] {
  return bodyRows().map((row) => texts(row)[1] ?? "");
}

/**
 * A thousand rows in the exact shape of an answer of `listNodes`, derived from its example
 * `nodes`: its summary task, then 999 lines under it. The fake back serves the volumes of
 * §4.6.2 with EP-02/L2 (#106), and the journey over a thousand rows it serves comes with
 * US-0110/L2 (#107): here the grid is proved on rows built in the test.
 */
function thousandRows(): NodeList {
  const [summary, , line] = witness.items;
  const facet = line?.estimate_line;
  if (summary === undefined || line === undefined || facet === undefined || facet === null) {
    throw new Error("the example nodes has changed");
  }
  const identifier = (series: number, index: number) =>
    `01926f3a-7c00-7000-8000-${String(series * 100000 + index).padStart(12, "0")}`;
  const lines = Array.from({ length: 999 }, (_, index): Node => ({
    ...line,
    node_id: identifier(1, index),
    lineage_id: identifier(2, index),
    parent_id: summary.node_id,
    position: index,
    row_number: index + 2,
    level: 2,
    estimate_line: { ...facet, label: `Ligne ${String(index + 2)}` },
  }));
  return {
    items: [summary, ...lines],
    totals: { ...witness.totals, task_count: 1, estimate_line_count: 999 },
  };
}

beforeEach(() => {
  router.push.mockReset();
  page.search = "";
  serve();
  // happy-dom lays nothing out: the element that scrolls is given the size a browser gives it.
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(VIEW);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the dense grid, on a thousand rows", () => {
  it("keeps the header and the totals in view after scrolling a thousand rows, and the label after scrolling sideways [WF-IHM-0060-A]", async () => {
    renderGrid(thousandRows());
    // The whole answer is counted, a screenful and a margin rendered.
    expect(grid()).toHaveAttribute("aria-rowcount", "1002");
    expect(bodyRows().length).toBeLessThan(60);
    expect(rowAt(2)).toBeDefined();

    scroller().scrollTop = 1000 * ROW_HEIGHT;
    fireEvent.scroll(scroller());
    await waitFor(() => {
      expect(texts(rowAt(1001)).slice(0, 2)).toEqual(["1000", "Ligne 1000"]);
    });
    expect(rowAt(2)).toBeUndefined();
    expect(bodyRows().length).toBeLessThan(60);

    // The header and the totals are rendered still, stuck to the top and the foot of the
    // element that scrolls — happy-dom lays nothing out: the stickiness is what is checked,
    // the browser does the rest.
    const header = rowAt(1);
    expect(texts(header)).toEqual([
      "N°",
      "Libellé",
      "Qté",
      "Charge (h)",
      "Débours unit.",
      "Budgété",
      "Réestimé",
    ]);
    // The amounts are computed by the server: their headers bear the mark Σ, named.
    expect(within(header ?? grid()).getAllByRole("img", { name: "Calculé" })).toHaveLength(2);
    for (const cell of within(header ?? grid()).getAllByRole("columnheader")) {
      expect(cell).toHaveClass("sticky", "top-0");
    }
    const totals = rowAt(1002);
    expect(texts(totals)).toEqual([
      "",
      "Total — 1 tâche, 999 lignes",
      "",
      "0",
      "",
      "100\u202f000,00",
      "100\u202f000,00",
    ]);
    for (const cell of totals?.querySelectorAll("td") ?? []) {
      expect(cell).toHaveClass("sticky", "bottom-0");
    }

    // Sideways, the number and the label stay at the start, the label just after the number.
    scroller().scrollLeft = 400;
    fireEvent.scroll(scroller());
    const [number, label] = rowAt(1001)?.querySelectorAll("td") ?? [];
    expect(number).toHaveClass("sticky");
    expect(number).toHaveStyle({ left: "0px" });
    expect(label).toHaveClass("sticky");
    expect(label).toHaveStyle({ left: "48px" });
    expect(within(header ?? grid()).getByRole("columnheader", { name: "Libellé" })).toHaveStyle({
      left: "48px",
    });
  });
});

describe("the sort, the search and the totals, asked of the server", () => {
  it("asks the server for the sort of a column clicked, both ways, by the parameters of the contract, and lifts it on a third click", async () => {
    page.search = "subproject_id=unassigned";
    const { ask } = renderGrid(witness);
    const heading = () => screen.getByRole("columnheader", { name: /Budgété/ });
    // No column is sorted: none says so.
    expect(grid().querySelectorAll("[aria-sort]")).toHaveLength(0);

    await userEvent.click(within(heading()).getByRole("button"));
    await waitFor(() => {
      expect(router.push).toHaveBeenLastCalledWith(
        "/projects/p/revisions/r?subproject_id=unassigned&sort_by=budgeted_amount&sort_order=asc",
        { scroll: false },
      );
    });
    ask({ sort: { column: "budgeted_amount", order: "asc" }, search: undefined });
    expect(heading()).toHaveAttribute("aria-sort", "ascending");
    expect(grid().querySelectorAll("[aria-sort]")).toHaveLength(1);

    await userEvent.click(within(heading()).getByRole("button"));
    await waitFor(() => {
      expect(router.push).toHaveBeenLastCalledWith(
        "/projects/p/revisions/r?subproject_id=unassigned&sort_by=budgeted_amount&sort_order=desc",
        { scroll: false },
      );
    });
    ask({ sort: { column: "budgeted_amount", order: "desc" }, search: undefined });
    expect(heading()).toHaveAttribute("aria-sort", "descending");

    await userEvent.click(within(heading()).getByRole("button"));
    await waitFor(() => {
      // Lifted, the sort stays in the address, empty: the page asks none, whatever is kept.
      expect(router.push).toHaveBeenLastCalledWith(
        "/projects/p/revisions/r?subproject_id=unassigned&sort_by=",
        { scroll: false },
      );
    });
  });

  it("records the sort chosen in the preferences of the grid alongside the navigation, and none once lifted", async () => {
    const client = serve();
    const { ask } = renderGrid(witness);
    const heading = () => screen.getByRole("columnheader", { name: /Qté/ });
    await userEvent.click(within(heading()).getByRole("button"));
    // Recorded at once, without the pause of a width.
    await waitFor(() => {
      expect(recorded(client)).toEqual([
        {
          grids: {
            estimate: {
              hidden_columns: [],
              column_widths: {},
              sort: { column: "quantity", order: "asc" },
            },
          },
        },
      ]);
    });
    ask({ sort: { column: "quantity", order: "desc" }, search: undefined });
    await userEvent.click(within(heading()).getByRole("button"));
    await waitFor(() => {
      expect(recorded(client).at(-1)).toEqual({
        grids: { estimate: { hidden_columns: [], column_widths: {}, sort: null } },
      });
    });
  });

  it("navigates to the sort asked without waiting for its preference, and nothing more once the grid is gone", async () => {
    let answer: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      answer = resolve;
    });
    const client = serve({ [PREFERENCES]: "preferences" }, { hold: () => held });
    const { unmount } = renderGrid(witness);
    await userEvent.click(
      within(screen.getByRole("columnheader", { name: /Budgété/ })).getByRole("button"),
    );
    // The preference is still being written: the address has changed already.
    expect(router.push.mock.calls).toEqual([
      ["/projects/p/revisions/r?sort_by=budgeted_amount&sort_order=asc", { scroll: false }],
    ]);
    await waitFor(() => {
      expect(recorded(client)).toHaveLength(1);
    });
    unmount();
    answer();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(router.push).toHaveBeenCalledTimes(1);
  });

  it("lifts the sort by the address, whether or not the preference could be written", async () => {
    serve({ [PREFERENCES]: { problem: { code: "SESSION_REQUIRED", status: 401 } } });
    renderGrid(witness, { query: { sort: { column: "label", order: "desc" }, search: undefined } });
    await userEvent.click(
      within(screen.getByRole("columnheader", { name: /Libellé/ })).getByRole("button"),
    );
    expect(router.push).toHaveBeenLastCalledWith("/projects/p/revisions/r?sort_by=", {
      scroll: false,
    });
    // The refusal is told; the address carries the lifting all the same.
    expect(await screen.findByRole("alert")).toHaveTextContent("Se connecter");
  });

  it("goes on from the sort asked when the header is clicked again before the server answered", async () => {
    let arrive: () => void = () => undefined;
    const navigation = new Promise<void>((resolve) => {
      arrive = resolve;
    });
    // A navigation of Next stays pending until the server has answered for the new address.
    router.push.mockImplementation(() => {
      startTransition(() => navigation);
    });
    renderGrid(witness);
    const button = () =>
      within(screen.getByRole("columnheader", { name: /Budgété/ })).getByRole("button");
    await userEvent.click(button());
    // The server has not answered: the header shows the sort asked, and goes on from it.
    expect(screen.getByRole("columnheader", { name: /Budgété/ })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
    await userEvent.click(button());
    expect(router.push.mock.calls.at(-1)).toEqual([
      "/projects/p/revisions/r?sort_by=budgeted_amount&sort_order=desc",
      { scroll: false },
    ]);
    await act(async () => {
      arrive();
      await navigation;
    });
  });

  it("renders the rows in the order the server gave, and the totals it computed for the request, never a sum of its own", () => {
    // An answer the server sorted otherwise than the plan: the grid keeps its order.
    const answer: NodeList = { ...witness, items: [...witness.items].reverse() };
    renderGrid(answer, { query: { sort: { column: "label", order: "desc" }, search: undefined } });
    expect(labels()).toEqual([
      "Revue de conception",
      "Ingénierie de détail",
      "Études de détail",
      "Études",
    ]);
    expect(screen.getByRole("columnheader", { name: /Libellé/ })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
    // The amounts of the tasks and of the line add up to 300 000; the total of the answer,
    // that of its lines alone, is 100 000.
    expect(texts(rowAt(6)).slice(-2)).toEqual(["100\u202f000,00", "100\u202f000,00"]);
  });

  it("asks the server for the rows a search retains, and for all of them once it is emptied", async () => {
    page.search = "sort_by=label&sort_order=asc";
    const { ask } = renderGrid(witness);
    const field = screen.getByRole("searchbox", { name: "Rechercher un libellé" });
    await userEvent.type(field, "  revue {Enter}");
    expect(router.push).toHaveBeenLastCalledWith(
      "/projects/p/revisions/r?sort_by=label&sort_order=asc&search=revue",
      { scroll: false },
    );
    page.search = "sort_by=label&sort_order=asc&search=revue";
    ask({ sort: undefined, search: "revue" });
    expect(screen.getByRole("searchbox", { name: "Rechercher un libellé" })).toHaveValue("revue");

    await userEvent.clear(screen.getByRole("searchbox", { name: "Rechercher un libellé" }));
    await userEvent.keyboard("{Enter}");
    expect(router.push).toHaveBeenLastCalledWith(
      "/projects/p/revisions/r?sort_by=label&sort_order=asc",
      { scroll: false },
    );
  });

  it("says no row matches when the server retains none, between the header and the totals", () => {
    renderGrid({ items: [], totals: { ...witness.totals, task_count: 0, estimate_line_count: 0 } });
    expect(grid()).toHaveAttribute("aria-rowcount", "3");
    expect(texts(rowAt(2))).toEqual(["Aucune ligne ne répond à la demande."]);
    expect(texts(rowAt(3))[1]).toBe("Total — aucune tâche, aucune ligne");
  });
});

describe("the columns and their widths, a display preference of the account", () => {
  it("shows the columns and widths the session read, and records a column hidden, the rest of the grid as it came", async () => {
    const client = serve();
    const settings = (
      example("session_grid_settings") as {
        user: { display_preferences: { grids: { estimate: GridPreferences } } };
      }
    ).user.display_preferences.grids.estimate;
    // The page sorts by the sort the account keeps when the address asks none.
    const { container } = renderGrid(witness, {
      preferences: settings,
      query: { sort: { column: "budgeted_amount", order: "desc" }, search: undefined },
    });
    await expectAccessible(container);
    // The quantity was hidden, the label widened.
    expect(screen.queryByRole("columnheader", { name: /Qté/ })).toBeNull();
    expect(screen.getByRole("columnheader", { name: /Charge/ })).toBeInTheDocument();
    expect(container.querySelectorAll("col")[1]).toHaveStyle({ width: "400px" });

    await userEvent.click(screen.getByRole("button", { name: "Colonnes" }));
    const menu = screen.getByRole("menu");
    expect(within(menu).getByRole("menuitemcheckbox", { name: "Qté" })).not.toBeChecked();
    await userEvent.click(within(menu).getByRole("menuitemcheckbox", { name: "Charge (h)" }));
    // The menu stays open, so that several columns are set in a row.
    await userEvent.click(within(menu).getByRole("menuitemcheckbox", { name: "Qté" }));
    expect(within(menu).getByRole("menuitemcheckbox", { name: "Qté" })).toBeChecked();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("columnheader", { name: /Charge/ })).toBeNull();
    expect(screen.getByRole("columnheader", { name: /Qté/ })).toBeInTheDocument();

    // Recorded once the user pauses, the last change only, the sort kept as it came.
    await waitFor(() => {
      expect(recorded(client)).toEqual([
        {
          grids: {
            estimate: {
              hidden_columns: ["hours"],
              column_widths: { label: 400 },
              sort: { column: "budgeted_amount", order: "desc" },
            },
          },
        },
      ]);
    });
  });

  it("sends back the sort the session kept when a width changes, not the sort of the address", async () => {
    const client = serve();
    renderGrid(witness, {
      preferences: { sort: { column: "budgeted_amount", order: "desc" } },
      query: { sort: { column: "label", order: "asc" }, search: undefined },
    });
    const handle = screen.getByRole("separator", { name: "Largeur de la colonne Libellé" });
    handle.focus();
    await userEvent.keyboard("{ArrowRight}");
    await waitFor(() => {
      expect(recorded(client)).toEqual([
        {
          grids: {
            estimate: {
              sort: { column: "budgeted_amount", order: "desc" },
              hidden_columns: [],
              column_widths: { label: 336 },
            },
          },
        },
      ]);
    });
  });

  it("widens a column by the arrows of the keyboard, within its bounds, and records the width", async () => {
    const client = serve();
    const { container } = renderGrid(witness);
    const handle = screen.getByRole("separator", { name: "Largeur de la colonne Budgété" });
    expect(handle).toHaveAttribute("aria-valuenow", "128");
    handle.focus();
    await userEvent.keyboard("{ArrowRight}{ArrowRight}{ArrowLeft}{Home}");
    expect(handle).toHaveAttribute("aria-valuenow", "144");
    expect(container.querySelectorAll("col")[5]).toHaveStyle({ width: "144px" });
    await waitFor(() => {
      expect(recorded(client)).toEqual([
        {
          grids: {
            estimate: { hidden_columns: [], column_widths: { budgeted_amount: 144 } },
          },
        },
      ]);
    });

    const narrow = screen.getByRole("separator", { name: "Largeur de la colonne Qté" });
    narrow.focus();
    await userEvent.keyboard("{ArrowLeft}{ArrowLeft}{ArrowLeft}");
    expect(narrow).toHaveAttribute("aria-valuenow", "40");
  });

  it("widens a column dragged by its handle", async () => {
    const client = serve();
    renderGrid(witness);
    const handle = screen.getByRole("separator", { name: "Largeur de la colonne Libellé" });
    fireEvent.mouseDown(handle, { clientX: 500 });
    fireEvent.mouseMove(document, { clientX: 560 });
    fireEvent.mouseUp(document, { clientX: 560 });
    expect(handle).toHaveAttribute("aria-valuenow", "380");
    await waitFor(() => {
      expect(recorded(client)).toEqual([
        { grids: { estimate: { hidden_columns: [], column_widths: { label: 380 } } } },
      ]);
    });
  });

  it("tells a setting the API refused, and only the outcome of the last one", async () => {
    serve({
      [PREFERENCES]: { problem: { code: "SESSION_REQUIRED", status: 401 } },
    });
    renderGrid(witness);
    const handle = screen.getByRole("separator", { name: "Largeur de la colonne Libellé" });
    handle.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(await screen.findByRole("alert")).toHaveTextContent("Se connecter");
  });
});

describe("the writing of the settings", () => {
  /** Widen the label by a step of the keyboard. */
  async function widen() {
    const handle = screen.getByRole("separator", { name: "Largeur de la colonne Libellé" });
    handle.focus();
    await userEvent.keyboard("{ArrowRight}");
  }

  /** The body that records a width of the label, without a sort. */
  const labelAt = (width: number) => ({
    grids: { estimate: { hidden_columns: [], column_widths: { label: width } } },
  });

  it("writes a change still waiting when the grid goes, once", async () => {
    const client = serve();
    const { unmount } = renderGrid(witness);
    await widen();
    expect(recorded(client)).toEqual([]);
    unmount();
    await waitFor(() => {
      expect(recorded(client)).toEqual([labelAt(336)]);
    });
    await new Promise((resolve) => setTimeout(resolve, WRITE_DELAY + 100));
    expect(recorded(client)).toEqual([labelAt(336)]);
  });

  it("writes a change still waiting when the page is left or hidden, and before a search, without waiting", async () => {
    const client = serve();
    renderGrid(witness);
    await widen();
    window.dispatchEvent(new Event("pagehide"));
    // At once: well before the pause after which a change is written.
    await waitFor(
      () => {
        expect(recorded(client)).toEqual([labelAt(336)]);
      },
      { timeout: WRITE_DELAY / 2 },
    );

    await widen();
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    document.dispatchEvent(new Event("visibilitychange"));
    await waitFor(
      () => {
        expect(recorded(client)).toHaveLength(2);
      },
      { timeout: WRITE_DELAY / 2 },
    );
    visibility.mockReturnValue("visible");
    await widen();
    document.dispatchEvent(new Event("visibilitychange"));
    expect(recorded(client)).toHaveLength(2);

    await userEvent.type(
      screen.getByRole("searchbox", { name: "Rechercher un libellé" }),
      "x{Enter}",
    );
    expect(recorded(client)).toEqual([labelAt(336), labelAt(352), labelAt(368)]);
    expect(router.push).toHaveBeenCalledTimes(1);
  });

  it("tells nothing of an earlier write refused after a later one succeeded", async () => {
    let answer: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      answer = resolve;
    });
    const client = serve(
      { [PREFERENCES]: [{ problem: { code: "SESSION_REQUIRED", status: 401 } }, "preferences"] },
      { hold: (_route, index) => (index === 0 ? held : undefined) },
    );
    renderGrid(witness);
    await widen();
    await waitFor(() => {
      expect(recorded(client)).toHaveLength(1);
    });
    await widen();
    await waitFor(() => {
      expect(recorded(client)).toHaveLength(2);
    });
    // The second write succeeded; the first, refused, answers only now.
    answer();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("takes the refusal away once a later write succeeds", async () => {
    serve({
      [PREFERENCES]: [{ problem: { code: "SESSION_REQUIRED", status: 401 } }, "preferences"],
    });
    renderGrid(witness);
    await widen();
    expect(await screen.findByRole("alert")).toHaveTextContent("Se connecter");
    await widen();
    await waitFor(() => {
      expect(screen.queryByRole("alert")).toBeNull();
    });
  });

  it("forgets the outcome told when the notice clears it", async () => {
    serve({ [PREFERENCES]: { problem: { code: "SESSION_REQUIRED", status: 401 } } });
    const { result } = renderHook(() => useSettingsWriter("estimate"));
    act(() => {
      result.current.recordNow({ hidden_columns: [] });
    });
    await waitFor(() => {
      expect(result.current.outcome?.kind).toBe("signed_out");
    });
    act(() => {
      result.current.clear();
    });
    expect(result.current.outcome).toBeUndefined();
  });
});

describe("a grid configured without its options", () => {
  it("shows neither row numbers nor tree, and pins nothing, when its configuration asks none", () => {
    const plain: GridConfig<Node, NodeSortColumn, NodeTotals> = {
      key: "plain",
      name: "estimate",
      rowKey: (node) => node.node_id,
      columns: ESTIMATE_GRID.columns.map((column) => ({ ...column, pinned: false })),
    };
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <DenseGrid
          config={plain}
          rows={witness.items}
          totals={witness.totals}
          totalsCaption="—"
          query={NO_QUERY}
          preferences={undefined}
        />
      </NextIntlClientProvider>,
    );
    expect(screen.queryByRole("columnheader", { name: "N°" })).toBeNull();
    expect(texts(rowAt(3)).slice(0, 2)).toEqual(["Études de détail", ""]);
    expect(within(grid()).queryAllByRole("img", { name: /Tâche|Ligne/ })).toEqual([]);
    expect(
      [...grid().querySelectorAll<HTMLElement>("td, th")].filter((cell) => cell.style.left !== ""),
    ).toEqual([]);
    // Without row numbers, the label is the first column: the caption of the totals is its.
    expect(texts(rowAt(6))[0]).toBe("—");
    // Every column may then be hidden.
    expect(screen.getAllByRole("separator")).toHaveLength(6);
  });

  it("sizes its rows by the root font, so that an enlarged font shifts no row", () => {
    document.documentElement.style.fontSize = "24px";
    try {
      renderGrid(thousandRows());
      const rendered = bodyRows();
      const spacers = [...grid().querySelectorAll<HTMLElement>('tr[aria-hidden="true"] td')];
      // The rows out of view after those rendered take 1.75 rem each: 42 pixels at 24.
      expect(spacers.at(-1)).toHaveStyle({ height: `${String((1000 - rendered.length) * 42)}px` });
    } finally {
      document.documentElement.style.fontSize = "";
    }
  });
});

describe("the figures and the dates of a grid, in the language of the interface", () => {
  const estimate = example("nodes_estimate") as NodeList;

  /** The cells of the row of a label, and of the totals, in a language. */
  function figures(locale: Locale, label: string) {
    const { unmount } = renderGrid(estimate, { locale });
    const row = bodyRows().find((candidate) => texts(candidate)[1] === label);
    const shown = { row: texts(row), totals: texts(rowAt(estimate.items.length + 2)) };
    unmount();
    return shown;
  }

  it("shows the same amount « 1 234,56 » in French and « 1,234.56 » in English, and the same total of the project [WF-INTF-0180-A]", () => {
    const french = figures("fr", "Borniers");
    const english = figures("en", "Borniers");
    // Number, label, quantity, hours, unit disbursement, budgeted, re-estimated.
    expect(french.row).toEqual(["4", "Borniers", "1", "", "1 234,56", "1 234,56", "1 234,56"]);
    expect(english.row).toEqual(["4", "Borniers", "1", "", "1,234.56", "1,234.56", "1,234.56"]);
    // The total of the project is the one the server gave, 2734.56, in either language.
    expect(french.totals.slice(-2)).toEqual(["2 734,56", "2 734,56"]);
    expect(english.totals.slice(-2)).toEqual(["2,734.56", "2,734.56"]);
    expect(english.totals[1]).toBe("Total — 3 tasks, 3 lines");
  });

  it("marks each row by the icon of its nature, named in the language of the interface", () => {
    renderGrid(estimate, { locale: "en" });
    expect(
      bodyRows().map((row) => within(row).getByRole("img").getAttribute("aria-label")),
    ).toEqual([
      "Summary task",
      "Task",
      "Labour line",
      "Disbursement line",
      "Provision line",
      "Milestone",
    ]);
  });

  describe("a column of planning dates", () => {
    const original = process.env.TZ;
    afterEach(() => {
      process.env.TZ = original;
    });

    // The grid of the estimate, with the finish date of the tasks: a column of dates, as the
    // grid of planning will configure it.
    const dated: GridConfig<Node, NodeSortColumn, NodeTotals> = {
      ...ESTIMATE_GRID,
      key: "dated",
      columns: [
        ...ESTIMATE_GRID.columns.slice(0, 1),
        {
          key: "finish_date",
          label: "finishDate",
          format: "date",
          width: 120,
          sortBy: "finish_date",
          value: (node) => node.task?.finish_date,
        },
      ],
    };

    // From fourteen hours ahead of UTC to eleven behind: a date read at midnight in the zone
    // of the workstation would fall a day off at one end or the other.
    it.each(["Pacific/Kiritimati", "Europe/Paris", "America/Los_Angeles", "Pacific/Pago_Pago"])(
      "shows a task planned on 30 June on 30 June, in the zone %s [WF-DAT-0100-A]",
      (zone) => {
        process.env.TZ = zone;
        render(
          <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
            <DenseGrid
              config={dated}
              rows={estimate.items}
              totals={estimate.totals}
              totalsCaption=""
              query={NO_QUERY}
              preferences={undefined}
            />
          </NextIntlClientProvider>,
        );
        const milestone = bodyRows().find((row) => texts(row)[1] === "Réception usine");
        expect(texts(milestone)).toEqual(["6", "Réception usine", "30 juin 2026"]);
        expect(screen.getByRole("columnheader", { name: "Fin" })).toBeInTheDocument();
      },
    );
  });
});
