// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, expectTypeOf, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { example, fakeClient } from "@/test/fixtures";
import { allShown, keysOf, PREFERENCES } from "@/test/grid-preferences";
import { estimateReference } from "@/test/reference";

import { comparedGrid, type FieldsOf } from "./compared";
import { PLANNING_GRID } from "./planning";
import { REMAINING_GRID } from "./remaining";
import { ESTIMATE_FIELDS } from "./estimate";
import { EstimateGrid } from "./estimate-grid";
import { type NodeList, type NodeRows, projectNodes } from "./nodes";
import { PLANNING_FIELDS, PLANNING_KINDS, type PlanningNode } from "./planning";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";
import type { GridPreferences } from "./settings";
import { REMAINING_FIELDS } from "./remaining";
import { RemainingGrid } from "./remaining-grid";

// The server of Next, as far as the grids need it: the fake back behind the action that records the
// settings.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<never> = { sort: undefined, search: undefined, size: undefined };
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};

// The comparison of the planning the contract gives (`comparison_planning`): the design file, whose
// finish the base put two days earlier (its duration five days against seven), the other tasks as
// the base held them. The grid reads it as the fake back serves it, nothing posed by hand.
const compared = example("comparison_planning") as NodeList;
const DESIGN = "Dossier de conception";
const CABLING = "Câblage sur site";
const PUSHED = (() => {
  const pushed = projectNodes(compared, PLANNING_FIELDS, PLANNING_KINDS).items.find(
    (node) => node.task?.label === DESIGN,
  ) as PlanningNode;
  return { base: pushed.base, deltas: pushed.deltas };
})();

// A frame that lays out: the rows of the answer are in the window of the rows in view.
beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});
afterEach(() => {
  vi.restoreAllMocks();
});

// The comparison of the current revision of the witness to the reference it comes from: the line
// of the provision, removed, is read in its place (EP-27).
const comparison = example("comparison_current") as NodeList;

/** The grid of the planning, compared or not, entered or not. */
function planningGrid(comparing: boolean, editable = true) {
  const nodes = projectNodes(compared, PLANNING_FIELDS, PLANNING_KINDS) as NodeRows<PlanningNode>;
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        filters={{}}
        query={NO_QUERY}
        preferences={undefined}
        editable={editable}
        comparing={comparing}
      />
    </NextIntlClientProvider>
  );
}

/** The columns the menu of the columns offers, by their names. */
async function offered(): Promise<string[]> {
  await userEvent.click(screen.getByRole("button", { name: "Colonnes" }));
  const names = within(screen.getByRole("menu"))
    .getAllByRole("menuitemcheckbox")
    .map((item) => item.textContent);
  await userEvent.keyboard("{Escape}");
  return names;
}

/** The row of a node, by the label it shows. */
function rowOf(label: string): HTMLElement {
  const cell = [...document.querySelectorAll<HTMLElement>('[data-column="label"]')].find(
    (candidate) => candidate.textContent.includes(label),
  );
  const row = cell?.closest("tr");
  if (row === null || row === undefined) {
    throw new Error(`no row of ${label}`);
  }
  return row;
}

/** The cell of a task, by its label and the key of its column. */
function cellOf(label: string, column: string): HTMLElement {
  const found = rowOf(label).querySelector<HTMLElement>(`td[data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} on ${label}`);
  }
  return found;
}

describe("the grid of the planning on a comparison", () => {
  it("keeps the columns it shows, and offers the columns of difference only while it reads one [WF-IHM-0150-A]", async () => {
    // Une comparaison activée ne change pas les colonnes affichées.
    const { unmount } = render(planningGrid(false));
    const plain = await offered();
    const headers = screen.getAllByRole("columnheader").map((header) => header.textContent);
    unmount();
    render(planningGrid(true));
    const withBase = await offered();
    expect(plain.some((name) => name.startsWith("Écart"))).toBe(false);
    expect(withBase.filter((name) => !name.startsWith("Écart"))).toEqual(plain);
    expect(withBase).toContain("Écart de la fin");
    // Hidden until chosen: the columns shown are those of the grid read alone, the marks aside.
    const shownNow = screen.getAllByRole("columnheader").map((header) => header.textContent);
    expect(shownNow.filter((name) => name !== "Écart")).toEqual(headers);
    expect(screen.queryByRole("columnheader", { name: "Écart de la fin" })).toBeNull();
  });

  it("marks the task whose finish differs, marks its cell of finish, and gives the date of the base from the keyboard alone [WF-IHM-0150-A]", async () => {
    render(planningGrid(true));
    expect(within(rowOf(DESIGN)).getByText("Modifié")).toBeInTheDocument();
    const finish = cellOf(DESIGN, "finish");
    // The sign, not the colour alone, and the base for a reader of the screen.
    expect(within(finish).getByText("Δ")).toBeInTheDocument();
    expect(finish).toHaveTextContent("Base : 15/04/2026");
    // The cells that do not differ bear no mark.
    expect(within(cellOf(DESIGN, "start")).queryByText("Δ")).toBeNull();
    // The focus of the keyboard shows the date of the base.
    expect(screen.queryByRole("tooltip")).toBeNull();
    act(() => {
      finish.focus();
    });
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Base : 15/04/2026");
    act(() => {
      finish.blur();
    });
    await waitFor(() => {
      expect(screen.queryByRole("tooltip")).toBeNull();
    });
  });

  it("gives the date of the base to the pointer too: the tooltip opens on the cell hovered, and closes when it leaves [WF-IHM-0150-A]", async () => {
    render(planningGrid(true));
    const finish = cellOf(DESIGN, "finish");
    expect(screen.queryByRole("tooltip")).toBeNull();
    await userEvent.hover(finish);
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Base : 15/04/2026");
    await userEvent.unhover(finish);
    await waitFor(() => {
      expect(screen.queryByRole("tooltip")).toBeNull();
    });
    // A cell that does not differ shows no base to the pointer.
    await userEvent.hover(cellOf(DESIGN, "start"));
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("gives the sign and the text for the reader of the screen the class that excludes them from a selection [WF-IHM-0150-A]", () => {
    // jsdom applies no style and copies nothing: this proves the class, not the copy of the browser.
    render(planningGrid(true));
    const finish = cellOf(DESIGN, "finish");
    const spoken = finish.querySelector<HTMLElement>(".sr-only");
    expect(spoken).toHaveTextContent("Base : 15/04/2026");
    expect(spoken).toHaveClass("select-none");
    expect(within(finish).getByText("Δ")).toHaveClass("select-none");
  });

  it("gives the number of days of the finish in its column of difference, once chosen [WF-IHM-0150-A]", async () => {
    render(planningGrid(true));
    await userEvent.click(screen.getByRole("button", { name: "Colonnes" }));
    await userEvent.click(
      within(screen.getByRole("menu")).getByRole("menuitemcheckbox", { name: "Écart de la fin" }),
    );
    await userEvent.keyboard("{Escape}");
    expect(screen.getByRole("columnheader", { name: "Écart de la fin" })).toBeInTheDocument();
    expect(cellOf(DESIGN, "delta_finish")).toHaveTextContent("+2 j");
    expect(cellOf("Études de détail", "delta_finish")).toHaveTextContent("");
  });

  it("keeps the visibility of a column of difference with the settings of the grid, shown or not [WF-IHM-0150-A]", async () => {
    // Leur visibilité gardée avec les réglages de la grille : choisie, la colonne est enregistrée
    // comme connue et non masquée, et se retrouve choisie à la réouverture.
    const client = fakeClient({ [PREFERENCES]: "preferences" });
    server.client = client;
    const { unmount } = render(planningGrid(true));
    await userEvent.click(screen.getByRole("button", { name: "Colonnes" }));
    await userEvent.click(
      within(screen.getByRole("menu")).getByRole("menuitemcheckbox", { name: "Écart de la fin" }),
    );
    await userEvent.keyboard("{Escape}");
    await waitFor(() => {
      expect(client.calls.filter((call) => call.route === PREFERENCES)).toHaveLength(1);
    });
    const [call] = client.calls;
    const recorded = (call?.body as { grids: { planning: GridPreferences } }).grids.planning;
    expect(recorded.known_columns).toContain("delta_finish");
    expect(recorded.hidden_columns).toContain("delta_start");
    expect(recorded.hidden_columns).not.toContain("delta_finish");
    unmount();
    // Read again without a comparison, the column is not offered; with one, it is shown.
    const reopened = (comparing: boolean) => (
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <PlanningGrid
          nodes={projectNodes(compared, PLANNING_FIELDS, PLANNING_KINDS)}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{}}
          query={NO_QUERY}
          preferences={recorded}
          comparing={comparing}
        />
      </NextIntlClientProvider>
    );
    const second = render(reopened(false));
    expect(screen.queryByRole("columnheader", { name: "Écart de la fin" })).toBeNull();
    second.unmount();
    render(reopened(true));
    expect(screen.getByRole("columnheader", { name: "Écart de la fin" })).toBeInTheDocument();
  });

  it.each([
    {
      name: "planning",
      key: "planning",
      columns: PLANNING_GRID.columns,
      grid: (preferences: GridPreferences, comparing: boolean) => (
        <PlanningGrid
          nodes={projectNodes(compared, PLANNING_FIELDS, PLANNING_KINDS)}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{}}
          query={NO_QUERY}
          preferences={preferences}
          comparing={comparing}
        />
      ),
    },
    {
      name: "remaining to commit",
      key: "remaining",
      columns: REMAINING_GRID.columns,
      grid: (preferences: GridPreferences, comparing: boolean) => (
        <RemainingGrid
          nodes={projectNodes(comparison, REMAINING_FIELDS)}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{}}
          editable
          query={NO_QUERY}
          preferences={preferences}
          comparing={comparing}
        />
      ),
    },
  ])(
    "hides the columns of difference of the $name set before they existed, records them as known, and moves no other column [WF-IHM-0150-A]",
    async ({ key, columns, grid, name }) => {
      // Les réglages d'avant le lot : toutes les colonnes de la grille connues et affichées, aucune
      // colonne d'écart connue.
      const before = allShown(columns);
      expect(before.known_columns?.some((column) => column.startsWith("delta_"))).toBe(false);
      const client = fakeClient({ [PREFERENCES]: "preferences" });
      server.client = client;
      const wrap = (comparing: boolean) => (
        <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
          {grid(before, comparing)}
        </NextIntlClientProvider>
      );
      const alone = render(wrap(false));
      const headers = screen.getAllByRole("columnheader").map((header) => header.textContent);
      alone.unmount();
      render(wrap(true));
      // Offered, unknown to the account: hidden, whatever the account showed of the others.
      const offeredNow = await offered();
      const deltas = offeredNow.filter((label) => label.startsWith("Écart"));
      expect(deltas.length, name).toBeGreaterThan(0);
      const shown = screen.getAllByRole("columnheader").map((header) => header.textContent);
      expect(shown.filter((label) => label !== "Écart")).toEqual(headers);
      deltas.forEach((label) => {
        expect(screen.queryByRole("columnheader", { name: label })).toBeNull();
      });
      // The first choice the account makes records the columns of difference as known and hidden.
      const other = offeredNow.find((label) => !label.startsWith("Écart")) ?? "";
      await userEvent.click(screen.getByRole("button", { name: "Colonnes" }));
      await userEvent.click(
        within(screen.getByRole("menu")).getByRole("menuitemcheckbox", { name: other }),
      );
      await userEvent.keyboard("{Escape}");
      await waitFor(() => {
        expect(client.calls.filter((call) => call.route === PREFERENCES)).toHaveLength(1);
      });
      const [call] = client.calls;
      const recorded = (call?.body as { grids: Record<string, GridPreferences> }).grids[key];
      const deltaKeys = (recorded?.known_columns ?? []).filter((column) =>
        column.startsWith("delta_"),
      );
      expect(deltaKeys.length).toBe(deltas.length);
      expect(recorded?.known_columns).toEqual(expect.arrayContaining(keysOf(columns)));
      expect(recorded?.hidden_columns).toEqual(expect.arrayContaining(deltaKeys));
    },
  );

  it("holds a revision marked read only: no cell of the comparison is entered [WF-IHM-0150-A]", () => {
    // Une révision marquée comparée reste en lecture seule : la structure n'offre pas `edit_planning`.
    render(planningGrid(true, false));
    const cells = ["label", "description", "duration", "finish"].map((column) =>
      cellOf(DESIGN, column),
    );
    expect(cells.every((cell) => cell.getAttribute("aria-readonly") === "true")).toBe(true);
    // The same grid, entered, offers the entry of the label.
    cleanup();
    render(planningGrid(true));
    expect(cellOf(DESIGN, "label")).not.toHaveAttribute("aria-readonly");
  });
});

describe("the grid of the estimate on a comparison", () => {
  const nodes = projectNodes(comparison, ESTIMATE_FIELDS);

  it("marks a line removed at its place, and offers no entry on it [WF-IHM-0150-A]", async () => {
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <EstimateGrid
          filters={{}}
          reference={estimateReference()}
          editable
          tasksEditable
          nodes={nodes}
          structure={STRUCTURE}
          structureVersion={1}
          query={NO_QUERY}
          preferences={undefined}
          comparing
        />
      </NextIntlClientProvider>,
    );
    const removed = nodes.items.find((node) => node.difference === "removed");
    expect(removed).toBeDefined();
    const label = removed?.estimate_line?.label ?? "";
    const row = rowOf(label);
    expect(within(row).getByText("Retiré")).toBeInTheDocument();
    const cells = [...row.querySelectorAll("td")];
    expect(cells.every((cell) => cell.getAttribute("aria-readonly") === "true")).toBe(true);
    // Enter on its label opens no entry.
    const first = cells.find((cell) => cell.getAttribute("data-column") === "label");
    act(() => {
      first?.focus();
    });
    await userEvent.keyboard("{Enter}");
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("marks the cell of an amount that differs, and gives the amount of the base [WF-IHM-0150-A]", () => {
    // The offer v1.0 against the reference: the cabling line is re-estimated at the rates of 2026.
    const rows = projectNodes(example("comparison") as NodeList, ESTIMATE_FIELDS);
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <EstimateGrid
          filters={{}}
          reference={estimateReference()}
          editable
          tasksEditable
          nodes={rows}
          structure={STRUCTURE}
          structureVersion={1}
          query={NO_QUERY}
          preferences={undefined}
          comparing
        />
      </NextIntlClientProvider>,
    );
    const base = rows.items.find((node) => node.estimate_line?.label === CABLING)?.base;
    expect(base?.estimate_line?.reestimated_amount).toBe("9702.60");
    const amount = cellOf(CABLING, "reestimated_amount");
    expect(amount).toHaveTextContent("Base : 9 702,60");
    expect(within(amount).getByText("Δ")).toBeInTheDocument();
    // A cell the base does not name bears no mark.
    expect(within(cellOf(CABLING, "quantity")).queryByText("Δ")).toBeNull();
  });
});

describe("the grid of the remaining to commit on a comparison", () => {
  it("marks a line removed and holds it read only, and says a base that held no value [WF-IHM-0150-A]", () => {
    const nodes = projectNodes(comparison, REMAINING_FIELDS);
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <RemainingGrid
          nodes={nodes}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{}}
          editable
          query={NO_QUERY}
          preferences={undefined}
          comparing
        />
      </NextIntlClientProvider>,
    );
    const removed = nodes.items.find((node) => node.difference === "removed");
    const label = removed?.estimate_line?.label ?? "";
    const row = rowOf(label);
    expect(within(row).getByText("Retiré")).toBeInTheDocument();
    const cells = [...row.querySelectorAll("td")];
    expect(cells.every((cell) => cell.getAttribute("aria-readonly") === "true")).toBe(true);
    // The previous remaining to commit the base had none of: said, not left blank.
    expect(screen.getAllByText(/Base : aucune valeur/).length).toBeGreaterThan(0);
  });
});

// The bases and differences given by hand below are malformed or partial on purpose (#3781, #3795,
// #3798): the contract cannot carry what it forbids, only the well-formed ones come from the example.
describe("the base of a cell, read as the contract types it (#3781)", () => {
  type TaskBase = components["schemas"]["ComparedTaskFacet"];
  type Instant = components["schemas"]["WorkInstant"];
  type Duration = components["schemas"]["Duration"];
  const finish = comparedGrid(PLANNING_GRID, true).columns.find(
    (column) => column.key === "finish",
  );
  const design = projectNodes(compared, PLANNING_FIELDS, PLANNING_KINDS).items.find(
    (node) => node.task?.label === DESIGN,
  ) as PlanningNode;

  /** The base of the finish of the design file, as its cell says it, the base given. */
  function finishBase(base: unknown): string {
    // A base the contract would not give is the point of the test: it is cast, not invented whole.
    const row = { ...design, base } as PlanningNode;
    return renderToStaticMarkup(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        {finish?.base?.(row)}
      </NextIntlClientProvider>,
    );
  }

  it("reads the date of the base as the contract types it, and a base that held none as none", () => {
    expect(finishBase(PUSHED.base)).toBe("15/04/2026");
    expect(finishBase({ task: { finish: null } })).toBe("aucune valeur");
    // A base that does not hold the field: the cell does not differ.
    expect(finishBase({ task: { start: null } })).toBe("");
  });

  it("fails on a base malformed rather than say it held nothing", () => {
    // The finish of the base given as a bare date, the shape of `started_on`, not a work instant.
    expect(() => finishBase({ task: { finish: "2026-04-17" } })).toThrow(RangeError);
    expect(() => finishBase({ task: { finish: { hours: "8" } } })).toThrow(RangeError);
  });

  it.each([
    ["a date without its time", "instant", "finish", "2026-04-17"],
    ["a duration without its quantity", "duration", "duration", { unit: "days" }],
    [
      "a duration in a unit the catalogue lacks",
      "duration",
      "duration",
      { value: "3", unit: "fortnights" },
    ],
    ["a share without `is_computable`", "share", "physical_progress", {}],
    ["a mode the catalogue lacks", "mode", "scheduling_mode", "sometimes"],
    ["a mode that is a key of the prototype", "mode", "scheduling_mode", "constructor"],
    ["a mode that is the prototype itself", "mode", "scheduling_mode", "__proto__"],
    ["a progress the catalogue lacks", "progress", "progress", "nearly"],
    ["a text that is an object", "plain", "started_on", { date: "2026-04-17" }],
  ])("fails on %s, as the %s base of %s [WF-IHM-0150-A]", (_reason, _shown, key, value) => {
    const column = comparedGrid(PLANNING_GRID, true).columns.find((one) => one.key === key);
    const row = { ...design, base: { task: { [key]: value } } } as PlanningNode;
    expect(() =>
      renderToStaticMarkup(
        <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
          {column?.base?.(row)}
        </NextIntlClientProvider>,
      ),
    ).toThrow(RangeError);
  });

  it("fails on a share said computable without a value, rather than say it is not computable [WF-IHM-0150-A]", () => {
    // Chosen: the contract gives `null` when not computable, so `is_computable: true` and null is a
    // defect of the API, said by the failure and not hidden under « not computable ».
    const column = comparedGrid(PLANNING_GRID, true).columns.find(
      (one) => one.key === "physical_progress",
    );
    const row = {
      ...design,
      base: { task: { physical_progress: { is_computable: true, value: null } } },
    } as PlanningNode;
    expect(() =>
      renderToStaticMarkup(
        <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
          {column?.base?.(row)}
        </NextIntlClientProvider>,
      ),
    ).toThrow(RangeError);
  });

  describe("the difference of a cell (#3795)", () => {
    const deltaFinish = comparedGrid(PLANNING_GRID, true).columns.find(
      (column) => column.key === "delta_finish",
    );
    const deltaDuration = comparedGrid(PLANNING_GRID, true).columns.find(
      (column) => column.key === "delta_duration",
    );

    /** The difference of a task of the grid, as its cell says it, the differences given. */
    function said(column: typeof deltaFinish, deltas: unknown): string {
      const row = { ...design, deltas } as PlanningNode;
      return renderToStaticMarkup(
        <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
          {column?.render?.(row)}
        </NextIntlClientProvider>,
      );
    }

    it("reads the difference as the contract types it, and a difference left out as none [WF-IHM-0150-A]", () => {
      expect(said(deltaFinish, PUSHED.deltas)).toBe("+2 j");
      expect(said(deltaDuration, { task: { duration: { value: "2", unit: "d" } } })).toContain(
        "+2",
      );
      // Left out, null, or of no task: the cell does not differ.
      expect(said(deltaFinish, { task: {} })).toBe("");
      expect(said(deltaFinish, { task: { finish: null } })).toBe("");
      expect(said(deltaFinish, null)).toBe("");
    });

    it("keeps the total float column without a base, and has no difference column for it [WF-REV-0080-A, WF-IHM-0150-A]", () => {
      const grid = comparedGrid(PLANNING_GRID, true);
      const keys = grid.columns.map((column) => column.key);
      const column = grid.columns.find((candidate) => candidate.key === "total_float");
      expect(column).toBeDefined();
      expect(column?.base).toBeUndefined();
      expect(keys).toContain("delta_duration");
      expect(keys).not.toContain("delta_total_float");
    });

    it.each([
      ["days that are a text", deltaFinish, { task: { finish: "5" } }],
      ["days that are an object", deltaFinish, { task: { finish: { days: 5 } } }],
      ["a duration without its quantity", deltaDuration, { task: { duration: { unit: "d" } } }],
      ["a duration that is a number", deltaDuration, { task: { duration: 2 } }],
      [
        "a duration in a unit the catalogue lacks",
        deltaDuration,
        { task: { duration: { value: "2", unit: "fortnights" } } },
      ],
      [
        "a duration in a unit that is a key of the prototype",
        deltaDuration,
        {
          task: { duration: { value: "2", unit: "constructor" } },
        },
      ],
    ])(
      "fails on %s rather than say there is no difference [WF-IHM-0150-A]",
      (_reason, column, deltas) => {
        expect(() => said(column, deltas)).toThrow(RangeError);
      },
    );
  });

  it("names the fields a showing reads by the types of the contract", () => {
    // A field renamed or retyped in the contract leaves these, and the configuration of the base
    // of the columns fails to compile.
    expectTypeOf<FieldsOf<TaskBase, Instant>>().toEqualTypeOf<"start" | "finish">();
    expectTypeOf<FieldsOf<TaskBase, Duration>>().toEqualTypeOf<"duration" | "total_float">();
  });
});
