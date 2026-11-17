// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { ApiClient } from "@/api/client";
import { example, fakeClient } from "@/test/fixtures";
import { PREFERENCES } from "@/test/grid-preferences";
import { estimateReference } from "@/test/reference";

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

// The planning of the witness: the design file, whose finish the base put five days earlier.
const planning = example("nodes_planning") as NodeList;
const DESIGN = "Dossier de conception";
const CABLING = "Câblage sur site";
const PUSHED = {
  base: { task: { finish: { date: "2026-04-17", hours: "8" } } },
  deltas: { task: { finish: 5 } },
};
const compared: NodeList = {
  ...planning,
  items: planning.items.map((node) =>
    node.task?.label === DESIGN
      ? { ...node, difference: "modified", changes: ["dates"], ...PUSHED }
      : ({
          ...node,
          difference: "unchanged",
          changes: [],
          base: null,
          deltas: null,
        } as typeof node),
  ),
};

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
    expect(finish).toHaveTextContent("Base : 17/04/2026");
    // The cells that do not differ bear no mark.
    expect(within(cellOf(DESIGN, "start")).queryByText("Δ")).toBeNull();
    // The focus of the keyboard shows the date of the base.
    expect(screen.queryByRole("tooltip")).toBeNull();
    act(() => {
      finish.focus();
    });
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Base : 17/04/2026");
    act(() => {
      finish.blur();
    });
    await waitFor(() => {
      expect(screen.queryByRole("tooltip")).toBeNull();
    });
  });

  it("gives the number of days of the finish in its column of difference, once chosen [WF-IHM-0150-A]", async () => {
    render(planningGrid(true));
    await userEvent.click(screen.getByRole("button", { name: "Colonnes" }));
    await userEvent.click(
      within(screen.getByRole("menu")).getByRole("menuitemcheckbox", { name: "Écart de la fin" }),
    );
    await userEvent.keyboard("{Escape}");
    expect(screen.getByRole("columnheader", { name: "Écart de la fin" })).toBeInTheDocument();
    expect(cellOf(DESIGN, "delta_finish")).toHaveTextContent("+5 j");
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
