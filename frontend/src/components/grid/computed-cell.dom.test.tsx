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
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
  unreachable,
} from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { DenseGrid } from "./dense-grid";
import { ESTIMATE_GRID } from "./estimate";
import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined };
const DEPENDENCIES =
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/dependencies";
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const STRUCTURE_PATH = `/projects/${STRUCTURE.project_id}/revisions/${STRUCTURE.revision_id}/structures/${STRUCTURE.structure_id}`;
const PENDING = "Lecture de ce dont elle dépend…";
const estimate = example("nodes_estimate") as NodeList;
const planning = example("nodes_planning") as NodeList;

/** The answer of the planning read anew, the summary « Études » changed since: a new version. */
function withSummaryChanged(): NodeList {
  const read = structuredClone(planning);
  const [summary] = read.items;
  return summary === undefined
    ? read
    : {
        ...read,
        items: [{ ...summary, lock_version: summary.lock_version + 1 }, ...read.items.slice(1)],
      };
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, hold?: Promise<unknown>, held = 0): FakeClient {
  const client = fakeClient(
    { "PATCH /me/preferences": "preferences", ...answers },
    { hold: (route, index) => (route === DEPENDENCIES && index === held ? hold : undefined) },
  );
  server.client = client;
  return client;
}

/** The grid of the planning on an answer, in French. */
function planningOf(nodes: NodeList) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid nodes={nodes} structure={STRUCTURE} query={NO_QUERY} preferences={undefined} />
    </NextIntlClientProvider>
  );
}

/** Render a grid of a structure on an answer, in a language. */
function renderGrid(grid: "estimate" | "planning", locale: Locale = "fr", nodes?: NodeList) {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      {grid === "estimate" ? (
        <EstimateGrid
          filters={{}}
          reference={estimateReference()}
          editable
          tasksEditable
          nodes={nodes ?? estimate}
          structure={STRUCTURE}
          structureVersion={1}
          query={NO_QUERY}
          preferences={undefined}
        />
      ) : (
        <PlanningGrid
          nodes={nodes ?? planning}
          structure={STRUCTURE}
          query={NO_QUERY}
          preferences={undefined}
        />
      )}
    </NextIntlClientProvider>,
  );
}

/** The cells of the row of a label, among the rows of the grid. */
function cellsOf(label: string): HTMLElement[] {
  const row = screen
    .getAllByRole("row")
    .find((candidate) => candidate.querySelectorAll("td")[1]?.textContent === label);
  return [...(row?.querySelectorAll("td") ?? [])];
}

/** A cell of the row of a label, by its position: number, label, then the columns. */
function cell(label: string, position: number): HTMLElement {
  const found = cellsOf(label)[position];
  if (found === undefined) {
    throw new Error(`no cell ${position.toString()} in the row of ${label}`);
  }
  return found;
}

/** The refusal shown beside a cell. */
function refusal(name = "Valeur calculée"): HTMLElement {
  return screen.getByRole("dialog", { name });
}

/** The texts of the paragraphs of the refusal, once the server has answered, and its rows. */
async function said(name?: string) {
  const dialog = refusal(name);
  await vi.waitFor(() => {
    expect(within(dialog).getByRole("status")).toHaveAttribute("aria-busy", "false");
  });
  return {
    paragraphs: [...dialog.querySelectorAll("p")].map((paragraph) => paragraph.textContent),
    rows: within(dialog)
      .queryAllByRole("listitem")
      .map((item) => item.textContent),
  };
}

/** The calls of the fake back that asked what a value depends on: the node, and the field. */
function asked(client: FakeClient) {
  return client.calls
    .filter((call) => call.route === DEPENDENCIES)
    .map((call) => [call.path, call.query.get("field")]);
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});

afterEach(() => {
  vi.restoreAllMocks();
});

// Number, label, category, role, quantity, hours, unit disbursement, amount at the year of
// reference, amount corrected for inflation.
const QUANTITY = 4;
const HOURS = 5;
const DISBURSEMENT = 6;
const REFERENCE = 10;
const INFLATED = 11;
// Number, label, mode, duration, start, finish, progress, float, predecessors.
const DURATION = 3;
const START = 4;
const FINISH = 5;
const PROGRESS = 6;
const FLOAT = 7;

describe("a value of a grid the server computes", () => {
  it("is not entered in a line of labour, does not look like its effort in hours, and is refused naming what it depends on [WF-IHM-0030-A]", async () => {
    const client = serve({ [DEPENDENCIES]: "dependencies_labour" });
    renderGrid("estimate");
    const labour = "Raccordement des borniers";
    const hours = cell(labour, HOURS);
    const amount = cell(labour, REFERENCE);
    // The effort is entered: its value alone, on the background of the page.
    expect(hours).toHaveTextContent(/^12,5$/);
    expect(hours).not.toHaveAttribute("aria-haspopup");
    expect(within(hours).queryByRole("img")).toBeNull();
    expect(hours).toHaveClass("bg-background");
    // The amount is computed: shaded, marked Σ and named so, whatever the colour.
    expect(amount).toHaveClass("bg-muted");
    expect(amount).toHaveAccessibleName(/^Calculé 1\s000,00$/);
    expect(within(amount).getByRole("img", { name: "Calculé" })).toBeInTheDocument();
    expect(cell(labour, INFLATED)).toHaveAccessibleName(/^Calculé 1\s000,00$/);

    // A try to enter it is refused, beside it, naming what the server says it depends on;
    // nothing opens to type.
    await userEvent.click(amount);
    expect(await said()).toEqual({
      paragraphs: [
        "Valeur calculée",
        "Montant (année de réf.) ne se saisit pas : Waterfall calcule cette valeur.",
        "Le montant d’une ligne de main-d’œuvre est le produit de sa quantité, de sa charge et du taux horaire de sa catégorie pour l’année de référence.",
      ],
      rows: [],
    });
    expect(asked(client)).toEqual([
      [
        `${STRUCTURE_PATH}/nodes/01926f3a-7c00-7000-8000-000000000553/dependencies`,
        "estimate_line.base_amount",
      ],
    ]);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("spinbutton")).toBeNull();
  });

  it("refuses to change the finish date of a summary task, naming its subordinates [WF-IHM-0030-A]", async () => {
    const client = serve({ [DEPENDENCIES]: "dependencies_summary" });
    renderGrid("planning");
    const finish = cell("Études", FINISH);
    expect(finish).toHaveAccessibleName(/^Calculé 24\/04\/2026$/);
    expect(finish).toHaveAttribute("aria-haspopup", "dialog");
    expect(finish).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(finish);
    expect(await said()).toEqual({
      paragraphs: [
        "Valeur calculée",
        "Fin ne se saisit pas : Waterfall calcule cette valeur.",
        "Une tâche récapitulative tient ses dates, sa durée et son avancement de ses subordonnées.",
        "Elle dépend de :",
      ],
      rows: [
        "2Études de détail",
        "4Pupitres opérateurs",
        "5Revue de conception",
        "6Réception des études",
        "7Dossier de conception",
      ],
    });
    expect(asked(client)).toEqual([
      [`${STRUCTURE_PATH}/nodes/01926f3a-7c00-7000-8000-000000000521/dependencies`, "task.finish"],
    ]);
    expect(within(refusal()).getByRole("list", { name: "Elle dépend de :" })).toBeInTheDocument();
    expect(cell("Études", FINISH)).toHaveAttribute("aria-expanded", "true");
    await expectAccessible(document.body);
  });

  it("names the subordinates the grid does not show, under a search or a filter [WF-IHM-0030-A]", async () => {
    serve({ [DEPENDENCIES]: "dependencies_summary" });
    // What a search on « Études » answers: the summary and the studies, not the other tasks.
    renderGrid("planning", "fr", {
      ...planning,
      items: planning.items.filter((node) => node.task?.label.startsWith("Études") === true),
    });
    expect(cellsOf("Revue de conception")).toEqual([]);
    await userEvent.click(cell("Études", FINISH));
    expect((await said()).rows).toEqual([
      "2Études de détail",
      "4Pupitres opérateurs",
      "5Revue de conception",
      "6Réception des études",
      "7Dossier de conception",
    ]);
  });

  it("says it is reading what the value depends on until the server answers, in one live region", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    serve(
      { [DEPENDENCIES]: "dependencies_summary" },
      new Promise((resolve) => {
        answer = resolve;
      }),
    );
    renderGrid("planning");
    await userEvent.click(cell("Études", FINISH));
    const region = within(refusal()).getByRole("status");
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toHaveAttribute("aria-busy", "true");
    expect(region).toHaveTextContent(PENDING);
    expect(within(refusal()).queryByRole("list")).toBeNull();
    await expectAccessible(document.body);
    answer();
    // The same region, which now holds what the server said.
    expect(await within(region).findByRole("list")).toBeInTheDocument();
    expect(region).toHaveAttribute("aria-busy", "false");
    expect(region).not.toHaveTextContent(PENDING);
    expect(within(refusal()).getAllByRole("status")).toEqual([region]);
  });

  it("asks nothing of a page read anew while closed, and asks afresh once reopened, the rows it names having moved", async () => {
    const client = serve({
      [DEPENDENCIES]: ["dependencies_summary", "dependencies_summary_moved"],
    });
    const { rerender } = renderGrid("planning");
    await userEvent.click(cell("Études", FINISH));
    expect((await said()).rows[0]).toBe("2Études de détail");
    await userEvent.keyboard("{Escape}");
    // A line inserted above the subordinates: they move down a row, the summary unchanged.
    const read = structuredClone(planning);
    rerender(
      planningOf({
        ...read,
        items: read.items.map((node) =>
          node.level === 2 ? { ...node, row_number: node.row_number + 1 } : node,
        ),
      }),
    );
    expect(asked(client)).toHaveLength(1);
    await userEvent.click(cell("Études", FINISH));
    expect((await said()).rows).toEqual([
      "3Études de détail",
      "5Pupitres opérateurs",
      "6Revue de conception",
      "7Réception des études",
      "8Dossier de conception",
    ]);
    expect(asked(client)).toHaveLength(2);
  });

  it("asks again, at the next opening, what the API could not say", async () => {
    const client = serve({ [DEPENDENCIES]: "dependencies_summary" });
    server.client = unreachable();
    renderGrid("planning");
    await userEvent.click(cell("Études", FINISH));
    expect(await within(refusal()).findByRole("alert")).toHaveTextContent(
      "Le service est injoignable",
    );
    await userEvent.keyboard("{Escape}");
    server.client = client;
    await userEvent.click(cell("Études", FINISH));
    expect((await said()).rows).toHaveLength(5);
    expect(within(refusal()).queryByRole("alert")).toBeNull();
    expect(asked(client)).toHaveLength(1);
  });

  it("asks afresh for a row read in another version, never showing the answer before", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    const client = serve(
      { [DEPENDENCIES]: ["dependencies_labour", "dependencies_summary"] },
      new Promise((resolve) => {
        answer = resolve;
      }),
      1,
    );
    const { rerender } = renderGrid("planning");
    await userEvent.click(cell("Études", FINISH));
    expect(
      await within(refusal()).findByText(/^Le montant d’une ligne de main-d’œuvre/),
    ).toBeInTheDocument();
    rerender(planningOf(withSummaryChanged()));
    expect(within(refusal()).getByRole("status")).toHaveTextContent(PENDING);
    expect(within(refusal()).queryByText(/^Le montant d’une ligne de main-d’œuvre/)).toBeNull();
    answer();
    expect(await within(refusal()).findByRole("list")).toBeInTheDocument();
    expect(asked(client)).toHaveLength(2);
  });

  it("drops an answer to a question changed meanwhile", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    serve(
      { [DEPENDENCIES]: ["dependencies_labour", "dependencies_summary"] },
      new Promise((resolve) => {
        answer = resolve;
      }),
    );
    const { rerender } = renderGrid("planning");
    await userEvent.click(cell("Études", FINISH));
    rerender(planningOf(withSummaryChanged()));
    answer();
    const { paragraphs } = await said();
    expect(paragraphs).not.toContain(
      "Le montant d’une ligne de main-d’œuvre est le produit de sa quantité, de sa charge et du taux horaire de sa catégorie pour l’année de référence.",
    );
    expect(paragraphs).toContain(
      "Une tâche récapitulative tient ses dates, sa durée et son avancement de ses subordonnées.",
    );
  });

  it("is refused from the keyboard as from the pointer, and gives the focus back to its cell", async () => {
    const client = serve({ [DEPENDENCIES]: "dependencies_summary" });
    renderGrid("planning");
    const start = cell("Études", START);
    start.focus();
    await userEvent.keyboard("{Enter}");
    expect(refusal()).toHaveTextContent(/^Valeur calculéeDébut ne se saisit pas/);
    expect(document.activeElement).not.toBe(document.body);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(start).toHaveFocus();
    expect(start).toHaveAttribute("aria-expanded", "false");
    // Pressed again, it opens again: the refusal is the same, and the server is not asked again.
    await userEvent.keyboard(" ");
    expect(refusal()).toHaveTextContent(/Début ne se saisit pas/);
    await said();
    expect(asked(client)).toHaveLength(1);
  });

  it("is read row by row: the dates of a task in manual mode are entered, those of the others computed", () => {
    serve();
    renderGrid("planning");
    for (const position of [DURATION, START, FINISH, PROGRESS]) {
      expect(cell("Études", position)).toHaveAttribute("aria-haspopup", "dialog");
      expect(cell("Pupitres opérateurs", position)).not.toHaveAttribute("aria-haspopup");
    }
    // A task in automatic mode computes its dates, and enters its duration and its progress.
    expect(cell("Revue de conception", START)).toHaveAttribute("aria-haspopup", "dialog");
    expect(cell("Revue de conception", FINISH)).toHaveAttribute("aria-haspopup", "dialog");
    expect(cell("Revue de conception", DURATION)).not.toHaveAttribute("aria-haspopup");
    expect(cell("Revue de conception", PROGRESS)).not.toHaveAttribute("aria-haspopup");
    expect(cell("Revue de conception", DURATION)).toHaveClass("bg-background");
  });

  it("marks the quantity and the unit disbursement of a provision, which come from its risk", async () => {
    const client = serve({ [DEPENDENCIES]: "dependencies_provision" });
    renderGrid("estimate");
    const provision = "Provision — risque de reprise du câblage";
    for (const position of [QUANTITY, DISBURSEMENT]) {
      expect(cell(provision, position)).toHaveClass("bg-muted");
      expect(cell("Borniers", position)).not.toHaveAttribute("aria-haspopup");
    }
    expect(cell(provision, HOURS)).not.toHaveAttribute("aria-haspopup");
    await userEvent.click(cell(provision, QUANTITY));
    expect((await said()).paragraphs.slice(1)).toEqual([
      "Qté ne se saisit pas : Waterfall calcule cette valeur.",
      "Une ligne de provision tient ses grandeurs de son risque : sa gravité pondérée par sa probabilité.",
    ]);
    expect(asked(client).map(([, field]) => field)).toEqual(["estimate_line.quantity"]);
  });

  it("names what the amount of a task depends on: the lines it bears", async () => {
    const client = serve({ [DEPENDENCIES]: "dependencies_task_amount" });
    renderGrid("estimate");
    await userEvent.click(cell("Câblage des armoires", REFERENCE));
    expect((await said()).rows).toEqual([
      "10Raccordement des borniers",
      "11Borniers",
      "12Provision — risque de reprise du câblage",
    ]);
    expect(asked(client).map(([, field]) => field)).toEqual(["task.base_amount"]);
  });

  it("says a task in manual mode bears no float", async () => {
    const client = serve({ [DEPENDENCIES]: "dependencies_manual_float" });
    renderGrid("planning");
    await userEvent.click(cell("Pupitres opérateurs", FLOAT));
    expect((await said()).paragraphs.slice(1)).toEqual([
      "Marge ne se saisit pas : Waterfall calcule cette valeur.",
      "Une tâche en mode manuel ne porte pas de marge.",
    ]);
    expect(asked(client).map(([, field]) => field)).toEqual(["task.total_float"]);
  });

  it("tells a refusal of the server as every screen does", async () => {
    serve({ [DEPENDENCIES]: { problem: { code: "NOT_FOUND", status: 404 } } });
    renderGrid("planning");
    await userEvent.click(cell("Études", FINISH));
    expect(await within(refusal()).findByRole("alert")).toHaveTextContent(
      /^Introuvable.+cet élément n’existe pas, ou vous n’y avez pas accès\.$/,
    );
    expect(within(refusal()).getByRole("status")).toHaveAttribute("aria-busy", "false");
    await expectAccessible(document.body);
  });

  it("tells the refusal of a field the server does not compute for the node", async () => {
    const problem = example("dependencies_entered") as Problem & { readonly status: 422 };
    serve({ [DEPENDENCIES]: { problem } });
    renderGrid("planning");
    await userEvent.click(cell("Études", FINISH));
    expect(await within(refusal()).findByRole("alert")).toHaveTextContent(
      /^Les données saisies ne sont pas valides\.$/,
    );
  });

  it("says the API is out of reach when the API does not answer", async () => {
    serve();
    renderGrid("planning");
    server.client = unreachable();
    await userEvent.click(cell("Études", FINISH));
    expect(await within(refusal()).findByRole("alert")).toHaveTextContent(
      "Le service est injoignable",
    );
  });

  it("says the API is out of reach when the server does not answer at all", async () => {
    serve();
    renderGrid("planning");
    server.client = undefined;
    await userEvent.click(cell("Études", FINISH));
    expect(await within(refusal()).findByRole("alert")).toHaveTextContent(
      "Le service est injoignable",
    );
  });

  it("says no more than that the value is computed, in a grid that cannot ask the server", async () => {
    serve();
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <DenseGrid
          config={ESTIMATE_GRID}
          rows={estimate.items}
          totals={estimate.totals}
          totalsCaption={() => "Total"}
          query={NO_QUERY}
          preferences={undefined}
        />
      </NextIntlClientProvider>,
    );
    await userEvent.click(cell("Borniers", REFERENCE));
    expect([...refusal().querySelectorAll("p")].map((p) => p.textContent)).toEqual([
      "Valeur calculée",
      "Montant (année de réf.) ne se saisit pas : Waterfall calcule cette valeur.",
    ]);
  });

  it("is refused in English too", async () => {
    serve({ [DEPENDENCIES]: "dependencies_summary" });
    renderGrid("planning", "en");
    expect(cell("Études", FINISH)).toHaveAccessibleName(/^Computed/);
    await userEvent.click(cell("Études", FINISH));
    expect((await said("Computed value")).paragraphs).toEqual([
      "Computed value",
      "Finish cannot be entered: Waterfall computes this value.",
      "A summary task takes its dates, its duration and its progress from its subtasks.",
      "It depends on:",
    ]);
  });
});
