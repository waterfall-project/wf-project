// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example, fakeClient } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";
import { formatPercent } from "@/i18n/format";

import { DenseGrid } from "./dense-grid";
import { ESTIMATE_GRID } from "./estimate";
import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import { PLANNING_GRID, PLANNING_SORT_COLUMNS } from "./planning";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The server of Next, as far as the grid needs it, as for the grid of the estimate.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const PATHNAME = "/projects/p/revisions/r/planning";

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(),
}));
// The one dense grid, watched: each screen hands it its configuration.
vi.mock("./dense-grid", async (original) => {
  const actual = await original<typeof import("./dense-grid")>();
  return { ...actual, DenseGrid: vi.fn(actual.DenseGrid) };
});

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined };
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const NBSP = " ";
const planning = example("nodes_planning") as NodeList;
// The float of the design file, which has no successor: to the end of the whole structure, as
// the example says it (#400) — the core incrusted in the thousand tasks, it follows them (#376).
const FILE_FLOAT =
  planning.items.find((node) => node.task?.label === "Dossier de conception")?.task?.total_float
    ?.value ?? "";

/** The position of a column among the cells of a row, the number of the row first. */
function at(key: string): number {
  return 1 + PLANNING_GRID.columns.findIndex((column) => column.key === key);
}

/** Render the grid of the planning on an answer, in a language. */
function renderPlanning(nodes: NodeList = planning, locale: Locale = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={STRUCTURE}
        filters={{}}
        query={NO_QUERY}
        preferences={undefined}
      />
    </NextIntlClientProvider>,
  );
}

/** The rows of the answer rendered, between the header and the totals. */
function bodyRows(): HTMLElement[] {
  return screen.getAllByRole("row").slice(1, -1);
}

/** The texts a cell shows: its text, without the names its icons show on hover. */
function shown(cell: Element): string {
  const copy = cell.cloneNode(true) as Element;
  copy.querySelectorAll("title").forEach((title) => {
    title.remove();
  });
  return copy.textContent;
}

/** The texts the cells of a row show. */
function texts(row: HTMLElement | undefined): string[] {
  return [...(row?.querySelectorAll("td, th") ?? [])].map(shown);
}

/** The cells of the row of a label. */
function cellsOf(label: string): HTMLElement[] {
  const row = bodyRows().find((candidate) => texts(candidate)[1] === label);
  return [...(row?.querySelectorAll("td") ?? [])];
}

/** The names of the icons a cell holds. */
function iconNames(cell: HTMLElement | undefined): (string | null)[] {
  return cell === undefined
    ? []
    : within(cell)
        .queryAllByRole("img")
        .map((icon) => icon.getAttribute("aria-label"));
}

beforeEach(() => {
  router.push.mockReset();
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the grids of the planning and of the estimate", () => {
  it("are two configurations of the one dense grid, not two components", () => {
    const estimate = example("nodes_estimate") as NodeList;
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <PlanningGrid
          nodes={planning}
          structure={STRUCTURE}
          filters={{}}
          query={NO_QUERY}
          preferences={undefined}
        />
        <EstimateGrid
          filters={{}}
          reference={estimateReference()}
          editable
          tasksEditable
          nodes={estimate}
          structure={STRUCTURE}
          structureVersion={1}
          query={NO_QUERY}
          preferences={undefined}
        />
      </NextIntlClientProvider>,
    );
    // Each screen renders the same component, each with its own configuration.
    const configs = vi.mocked(DenseGrid).mock.calls.map(([props]) => props.config.key);
    expect(new Set(configs)).toEqual(new Set([PLANNING_GRID.key, ESTIMATE_GRID.key]));
    expect(PLANNING_GRID.key).not.toBe(ESTIMATE_GRID.key);
    // Both are the same grid: numbered, the tree and the label pinned first, the search and
    // the choice of the columns above; they differ by their columns.
    for (const name of ["Grille de planning", "Grille de devis"]) {
      const grid = screen.getByRole("treegrid", { name });
      expect(within(grid).getByRole("columnheader", { name: "N°" })).toBeInTheDocument();
      expect(within(grid).getByRole("columnheader", { name: "Libellé" })).toBeInTheDocument();
    }
    expect(screen.getAllByRole("search")).toHaveLength(2);
    const planningGrid = screen.getByRole("treegrid", { name: "Grille de planning" });
    expect(within(planningGrid).queryByRole("columnheader", { name: /Budgété/ })).toBeNull();
    expect(
      within(planningGrid).getByRole("columnheader", { name: "Calculé Marge" }),
    ).toBeInTheDocument();
  });
});

describe("the grid of the planning", () => {
  it("shows each task of the answer, in its order: its number, label, description, duration, dates, physical progress, float and predecessors", () => {
    renderPlanning();
    const days = (count: string) => `${count}${NBSP}j`;
    const full = formatPercent("1", "fr");
    // The numbers are those of the whole structure: the line of row 3, which the planning does
    // not render, keeps its own. A lag keeps its unit: a week is not written in days.
    // The description, which no task of the witness bears; the physical progress of the summary
    // alone; the Gantt last, a drawing.
    expect(bodyRows().map(texts)).toEqual([
      ["1", "Études", "", "", days("40"), "02/03/2026", "24/04/2026", "", full, "", "", ""],
      [
        "2",
        "Études de détail",
        "",
        "",
        days("30"),
        "02/03/2026",
        "10/04/2026",
        "",
        "",
        days("0"),
        "",
        "",
      ],
      [
        "4",
        "Pupitres opérateurs",
        "",
        "",
        days("40"),
        "02/03/2026",
        "24/04/2026",
        "",
        "",
        "",
        "",
        "",
      ],
      [
        "5",
        "Revue de conception",
        "",
        "",
        days("10"),
        "13/04/2026",
        "24/04/2026",
        "",
        "",
        days("0"),
        "2",
        "",
      ],
      [
        "6",
        "Réception des études",
        "",
        "",
        days("0"),
        "24/04/2026",
        "24/04/2026",
        "",
        "",
        days("0"),
        `5;4DD+1${NBSP}sem`,
        "",
      ],
      [
        "7",
        "Dossier de conception",
        "",
        "",
        days("5"),
        "09/04/2026",
        "15/04/2026",
        "",
        "",
        days(FILE_FLOAT.replace(".", ",")),
        `2FD-${days("2")}`,
        "",
      ],
    ]);
    expect(texts(screen.getAllByRole("row").at(-1))[1]).toBe("Total — 6 tâches");
  });

  it("marks the three sorts of task, the scheduling mode and the progress by icons named for them", () => {
    renderPlanning();
    const icons = (label: string) => cellsOf(label).map((cell) => iconNames(cell));
    // Nature, mode and progress — the progress of a summary computed from its subordinates, and
    // marked so.
    const studies = icons("Études");
    expect([studies[at("label")], studies[at("scheduling_mode")], studies[at("progress")]]).toEqual(
      [["Tâche récapitulative"], ["Automatique"], ["Calculé", "Démarrée"]],
    );
    expect(icons("Pupitres opérateurs")[at("scheduling_mode")]).toEqual(["Manuel"]);
    expect(icons("Études de détail")[at("progress")]).toEqual(["Terminée"]);
    expect(icons("Réception des études")[at("label")]).toEqual(["Jalon"]);
    expect(icons("Réception des études")[at("progress")]).toEqual(["Terminée"]);
    expect(icons("Dossier de conception")[at("label")]).toEqual(["Tâche"]);
    // Each shows its name on hover too, to whoever does not read the icon.
    const manual = cellsOf("Pupitres opérateurs")[at("scheduling_mode")];
    expect(within(manual ?? document.body).getByTitle("Manuel")).toBeInTheDocument();
    const completed = cellsOf("Études de détail")[at("progress")];
    expect(within(completed ?? document.body).getByTitle("Terminée")).toBeInTheDocument();
  });

  it("marks the float of a task on the critical path by an icon and bold type, never by a colour alone", () => {
    renderPlanning();
    const float = (label: string) => cellsOf(label)[at("total_float")];
    // The float is computed in every task: its cell bears the mark of a computed value first.
    for (const critical of ["Études de détail", "Revue de conception", "Réception des études"]) {
      expect(iconNames(float(critical))).toEqual(["Calculé", "Chemin critique"]);
      expect(float(critical)?.querySelector(".font-semibold")).not.toBeNull();
      expect(within(float(critical) ?? document.body).getByTitle("Chemin critique")).toBeVisible();
    }
    // A task with a float, and one in manual mode, which bears none: no mark.
    for (const off of ["Dossier de conception", "Pupitres opérateurs"]) {
      expect(iconNames(float(off))).toEqual(["Calculé"]);
      expect(float(off)?.querySelector(".font-semibold")).toBeNull();
    }
  });

  it("names the icon columns in their headers, and asks the server for their sort", async () => {
    renderPlanning();
    const grid = screen.getByRole("treegrid", { name: "Grille de planning" });
    // Each named by its heading, which shows on hover too.
    for (const name of ["Mode de planification", "Avancement"]) {
      const header = within(grid).getByRole("columnheader", { name });
      expect(within(header).getByTitle(name)).toBeInTheDocument();
    }
    await userEvent.click(
      within(within(grid).getByRole("columnheader", { name: "Mode de planification" })).getByRole(
        "button",
      ),
    );
    expect(router.push).toHaveBeenCalledWith(`${PATHNAME}?sort_by=scheduling_mode&sort_order=asc`, {
      scroll: false,
    });
  });

  it("sorts each of its columns by the column of the contract of the same name, whose value it reads", () => {
    // Each but the Gantt, which draws the row and sorts nothing.
    expect(PLANNING_SORT_COLUMNS).toEqual(
      PLANNING_GRID.columns.map((column) => column.key).filter((key) => key !== "gantt"),
    );
    // The predecessors, which their cell renders, give an accessor to the sort alone.
    const milestone = planning.items[4];
    const columns = PLANNING_GRID.columns.filter(
      (column) => !["predecessors", "gantt"].includes(column.key),
    );
    expect(milestone === undefined ? [] : columns.map((c) => c.value(milestone))).toEqual([
      "Réception des études",
      undefined,
      "automatic",
      "0",
      "2026-04-24",
      "2026-04-24",
      "completed",
      undefined,
      "0",
    ]);
  });

  it("says the physical progress of a summary not computable, and why, in the cell itself", () => {
    // What the API would answer of the studies without any amount budgeted in their subtree.
    renderPlanning({
      ...planning,
      items: planning.items.map((node) =>
        node.task?.is_summary === true
          ? {
              ...node,
              task: {
                ...node.task,
                physical_progress: {
                  is_computable: false,
                  value: null,
                  reason: "no_budgeted_amount" as const,
                },
              },
            }
          : node,
      ),
    });
    const cell = cellsOf("Études")[at("physical_progress")];
    expect(cell?.textContent).toBe(
      "Non calculable — Aucun montant budgété dans le sous-arbre de la tâche.",
    );
    expect(cell?.querySelector("[title]")).toBeNull();
  });

  it("names a predecessor the answer does not hold by the number the API gives it", () => {
    // What a search retaining the review but not the studies it follows would answer.
    renderPlanning({
      ...planning,
      items: planning.items.filter((node) => node.task?.label !== "Études de détail"),
    });
    expect(
      texts(bodyRows().find((row) => texts(row)[1] === "Revue de conception"))[at("predecessors")],
    ).toBe("2");
  });

  it("writes each lag in its unit, in months, and a lead in weeks", () => {
    // What the API would answer of the dossier linked to its two predecessors otherwise.
    const [studies, review] = [planning.items[1], planning.items[3]];
    const links = [
      { node: studies, lag: { value: "2", unit: "mo" as const } },
      { node: review, lag: { value: "-1", unit: "w" as const } },
    ].flatMap(({ node, lag }) =>
      node === undefined
        ? []
        : [
            {
              predecessor_node_id: node.node_id,
              predecessor_row_number: node.row_number,
              link_type: "start_to_start" as const,
              lag,
            },
          ],
    );
    const linked = {
      ...planning,
      items: planning.items.map((node) =>
        node.task?.label === "Dossier de conception" ? { ...node, predecessors: links } : node,
      ),
    };
    const { unmount } = renderPlanning(linked);
    const dossier = () =>
      texts(bodyRows().find((row) => texts(row)[1] === "Dossier de conception"));
    expect(dossier()[at("predecessors")]).toBe(`2DD+2${NBSP}m;5DD-1${NBSP}sem`);
    unmount();
    renderPlanning(linked, "en");
    expect(dossier()[at("predecessors")]).toBe(`2SS+2${NBSP}mo;5SS-1${NBSP}wk`);
  });

  it("shows its figures, units and links in English too", () => {
    renderPlanning(planning, "en");
    expect(texts(bodyRows()[4])).toEqual([
      "6",
      "Réception des études",
      "",
      "",
      `0${NBSP}d`,
      "24/04/2026",
      "24/04/2026",
      "",
      "",
      `0${NBSP}d`,
      `5;4SS+1${NBSP}wk`,
      "",
    ]);
    expect(texts(bodyRows()[5])).toEqual([
      "7",
      "Dossier de conception",
      "",
      "",
      `5${NBSP}d`,
      "09/04/2026",
      "15/04/2026",
      "",
      "",
      `${FILE_FLOAT}${NBSP}d`,
      `2FS-2${NBSP}d`,
      "",
    ]);
    expect(iconNames(cellsOf("Revue de conception")[at("total_float")])).toEqual([
      "Computed",
      "Critical path",
    ]);
  });

  it("is accessible", async () => {
    const { container } = renderPlanning();
    await expectAccessible(container);
  });
});
