// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
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
  unreachable,
} from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import type { GridQuery } from "./query";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined };
const LINE =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line";
const TASK =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task";
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const NODES = `/projects/${STRUCTURE.project_id}/revisions/${STRUCTURE.revision_id}/structures/${STRUCTURE.structure_id}/nodes`;
// The categories and the roles of the examples, by identifier.
const COMMISSIONING = "01926f3a-7c00-7000-8000-000000000405";
const COMMISSIONING_TECHNICIAN = "01926f3a-7c00-7000-8000-000000000452";
const AUTOMATION_ENGINEER = "01926f3a-7c00-7000-8000-000000000453";
// The rows of the estimate, by their index: the summary, the task « Câblage des armoires », its
// line of labour « Raccordement des borniers », its disbursement « Borniers », its provision,
// whose quantity and unit disbursement the server computes, the milestone.
const TASK_ROW = 1;
const LABOUR = 2;
const DISBURSEMENT = 3;
const PROVISION = 4;
const MILESTONE = 5;
const estimate = example("nodes_estimate") as NodeList;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, hold?: Promise<unknown>): FakeClient {
  const client = fakeClient(
    { [LINE]: "estimate_line_updated", [TASK]: "task_renamed", ...answers },
    { hold: () => hold },
  );
  server.client = client;
  return client;
}

/** The grid of the estimate on an answer, in a language, open to entry or not. */
function grid(
  locale: Locale = "fr",
  nodes: NodeList = estimate,
  editable = true,
  tasksEditable = true,
) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <EstimateGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        reference={estimateReference()}
        editable={editable}
        tasksEditable={tasksEditable}
        query={NO_QUERY}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The cell of a row, by its index among the rows of the answer, and of a column, by its key. */
function cell(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("grid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** The writes the grid sent: the node, and what was written. */
function written(client: FakeClient, route = LINE) {
  return client.calls
    .filter((call) => call.route === route)
    .map((call) => ({ path: call.path, body: call.body }));
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the keyboard of a grid", () => {
  it("enters a whole line of the estimate without the pointer — label, category, role, quantity, effort —, and the last cell validated places the cursor on the next row [WF-IHM-0040-A]", async () => {
    const client = serve();
    render(grid());
    cell(0, "label").focus();
    await userEvent.keyboard("{ArrowDown}{ArrowDown}");
    expect(cell(LABOUR, "label")).toHaveFocus();

    // A character typed opens the entry with it; Tab validates it and goes along the row.
    await userEvent.keyboard("Raccordement et repérage{Tab}");
    expect(cell(LABOUR, "cost_category")).toHaveFocus();
    // The category and the role are chosen from their lists, by the first letters of a name: a
    // letter typed on the cell opens its list at the first choice it starts.
    await userEvent.keyboard("M");
    const categories = screen.getByRole("combobox", { name: "Catégorie" });
    expect(categories).toHaveFocus();
    expect(categories).toHaveValue(COMMISSIONING);
    await userEvent.keyboard("{Tab}{Enter}");
    const roles = screen.getByRole("combobox", { name: "Rôle" });
    expect(roles).toHaveValue("01926f3a-7c00-7000-8000-000000000451");
    await userEvent.keyboard("Technicien");
    expect(roles).toHaveValue(COMMISSIONING_TECHNICIAN);
    await userEvent.keyboard("{Tab}2{Tab}15{Enter}");

    // The row below, at the cell the row was started from.
    expect(cell(DISBURSEMENT, "label")).toHaveFocus();
    expect(screen.queryByRole("textbox")).toBeNull();
    // Each cell left alone, the second and the next carrying the version the server answered.
    const node = `${NODES}/01926f3a-7c00-7000-8000-000000000523/estimate-line`;
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(5);
    });
    const bodies = written(client).map(({ path, body }) => {
      expect(path).toBe(node);
      return body;
    });
    expect(bodies).toMatchObject([
      { label: "Raccordement et repérage", lock_version: 1 },
      { cost_category_id: COMMISSIONING, lock_version: 2 },
      { resource_role_id: COMMISSIONING_TECHNICIAN, lock_version: 2 },
      { quantity: "2", lock_version: 2 },
      { hours: "15", lock_version: 2 },
    ]);
    // Each write carries the cell entered and the version read, nothing else (#178).
    expect(bodies[0]).toEqual({ label: "Raccordement et repérage", lock_version: 1 });
    // The row the server answered takes the place of what was typed: its effort, its amount.
    await vi.waitFor(() => {
      expect(cell(LABOUR, "hours")).toHaveTextContent(/^14$/);
    });
    expect(cell(LABOUR, "label")).toHaveTextContent("Raccordement des borniers");
    expect(cell(LABOUR, "reestimated_amount")).toHaveTextContent(/1\s120,00$/);
    expect(cell(LABOUR, "budgeted_amount")).toHaveTextContent(/1\s000,00$/);
  });

  it("renames a task by its own operation, and shows the label the server answered", async () => {
    const client = serve();
    render(grid());
    cell(TASK_ROW, "label").focus();
    await userEvent.keyboard("{F2}");
    const field = screen.getByRole("textbox", { name: "Libellé" });
    expect(field).toHaveValue("Câblage des armoires");
    await userEvent.keyboard(" et repérage{Enter}");
    await vi.waitFor(() => {
      expect(cell(TASK_ROW, "label")).toHaveTextContent("Câblage et repérage des armoires");
    });
    expect(written(client, TASK)).toEqual([
      {
        path: `${NODES}/01926f3a-7c00-7000-8000-000000000522/task`,
        body: { label: "Câblage des armoires et repérage", lock_version: 1 },
      },
    ]);
    expect(cell(LABOUR, "label")).toHaveFocus();
  });

  it("leaves the label of a task to the planning, where the revision does not let the caller enter it", async () => {
    serve();
    render(grid("fr", estimate, true, false));
    cell(TASK_ROW, "label").focus();
    await userEvent.keyboard("{F2}");
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(cell(TASK_ROW, "label")).toHaveAttribute("aria-readonly", "true");
    await userEvent.keyboard("{ArrowDown}{F2}");
    expect(screen.getByRole("textbox", { name: "Libellé" })).toHaveFocus();
  });

  it("renames a task again, from the version it holds, after a refusal", async () => {
    const client = serve({
      [TASK]: [{ problem: { code: "STALE_LOCK_VERSION", status: 412 } }, "task_renamed"],
    });
    render(grid());
    cell(TASK_ROW, "label").focus();
    await userEvent.keyboard("{F2} bis{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(/modifié cette donnée/);
    expect(cell(TASK_ROW, "label")).toHaveTextContent("Câblage des armoires");
    await userEvent.keyboard("{ArrowUp}{F2} et repérage{Enter}");
    await vi.waitFor(() => {
      expect(cell(TASK_ROW, "label")).toHaveTextContent("Câblage et repérage des armoires");
    });
    expect(written(client, TASK).map(({ body }) => body)).toEqual([
      { label: "Câblage des armoires bis", lock_version: 1 },
      { label: "Câblage des armoires et repérage", lock_version: 1 },
    ]);
  });

  it("offers the active choices alone, and keeps a deactivated one a line bears", async () => {
    const client = serve();
    const read = structuredClone(estimate);
    const labour = read.items[LABOUR]?.estimate_line;
    if (labour !== undefined && labour !== null) {
      labour.resource_role_id = AUTOMATION_ENGINEER;
    }
    render(grid("fr", read));
    expect(cell(LABOUR, "resource_role")).toHaveTextContent("Automaticien");
    // Another line: the deactivated role is not offered.
    cell(DISBURSEMENT, "resource_role").focus();
    await userEvent.keyboard("{Enter}");
    const offered = within(screen.getByRole("combobox", { name: "Rôle" }))
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(offered).toEqual(["Aucun", "Ingénieur électricien", "Technicien de mise en service"]);
    // The line that bears it: shown, offered, kept.
    await userEvent.keyboard("{Escape}{ArrowUp}{Enter}");
    expect(screen.getByRole("combobox", { name: "Rôle" })).toHaveValue(AUTOMATION_ENGINEER);
    await userEvent.keyboard("{Tab}");
    expect(written(client)).toEqual([]);
  });

  it("writes no role once « Aucun » is chosen", async () => {
    const client = serve();
    render(grid());
    cell(LABOUR, "resource_role").focus();
    await userEvent.keyboard("{Enter}Aucun");
    expect(screen.getByRole("combobox", { name: "Rôle" })).toHaveValue("");
    await userEvent.keyboard("{Tab}");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(written(client)[0]?.body).toMatchObject({ resource_role_id: null });
  });

  it("shows an identifier the list does not know as unknown, and offers no entry for it", async () => {
    serve();
    const read = structuredClone(estimate);
    const labour = read.items[LABOUR]?.estimate_line;
    if (labour !== undefined && labour !== null) {
      labour.cost_category_id = "01926f3a-7c00-7000-8000-000000009999";
    }
    render(grid("fr", read));
    expect(cell(LABOUR, "cost_category")).toHaveTextContent("Référence inconnue");
    expect(cell(LABOUR, "cost_category")).toHaveAttribute("aria-readonly", "true");
    cell(LABOUR, "cost_category").focus();
    await userEvent.keyboard("{Enter}M");
    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("leaves a cell at its value before when its entry under way is abandoned [WF-IHM-0040-A]", async () => {
    const client = serve();
    render(grid());
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("99");
    expect(screen.getByRole("textbox", { name: "Charge (h)" })).toHaveValue("99");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(cell(LABOUR, "hours")).toHaveTextContent(/^12,5$/);
    expect(cell(LABOUR, "hours")).toHaveFocus();
    // Entered as it is — the decimal of the language —, changed, abandoned.
    await userEvent.keyboard("{F2}");
    expect(screen.getByRole("textbox", { name: "Charge (h)" })).toHaveValue("12,5");
    await userEvent.keyboard("0{Escape}");
    expect(cell(LABOUR, "hours")).toHaveTextContent(/^12,5$/);
    // A choice changed in its list, abandoned.
    await userEvent.keyboard("{Home}{ArrowRight}{ArrowRight}{Enter}Mise");
    expect(screen.getByRole("combobox", { name: "Catégorie" })).toHaveValue(COMMISSIONING);
    await userEvent.keyboard("{Escape}");
    expect(cell(LABOUR, "cost_category")).toHaveTextContent("Ingénierie électrique");
    expect(written(client)).toEqual([]);
  });

  it("traverses the computed cells without entering them [WF-IHM-0040-A]", async () => {
    const client = serve();
    render(grid());
    cell(PROVISION, "label").focus();
    // Along the row of the provision: its quantity and its unit disbursement are computed. Its role
    // and its effort are offered, the node not saying which fields its line takes (#194).
    await userEvent.keyboard("{Enter}{Tab}");
    expect(cell(PROVISION, "cost_category")).toHaveFocus();
    await userEvent.keyboard("{Enter}{Tab}");
    expect(cell(PROVISION, "resource_role")).toHaveFocus();
    await userEvent.keyboard("{Enter}{Tab}");
    expect(cell(PROVISION, "hours")).toHaveFocus();
    await userEvent.keyboard("{Enter}{Shift>}{Tab}{/Shift}");
    expect(cell(PROVISION, "resource_role")).toHaveFocus();
    await userEvent.keyboard("{Enter}{Tab}");
    expect(cell(PROVISION, "hours")).toHaveFocus();
    await userEvent.keyboard("{Enter}{Tab}");
    // Nothing more to enter along the row: the next row, at the cell it was started from.
    expect(cell(MILESTONE, "label")).toHaveFocus();
    // Nothing was changed, nothing written.
    expect(written(client)).toEqual([]);

    // The arrows stop on a computed cell, which opens no entry: a try is refused.
    await userEvent.keyboard("{ArrowUp}{Home}{ArrowRight}{ArrowRight}{ArrowRight}{ArrowRight}");
    expect(cell(PROVISION, "quantity")).toHaveFocus();
    expect(cell(PROVISION, "quantity")).toHaveAttribute("aria-readonly", "true");
    expect(screen.queryByRole("textbox")).toBeNull();
    await userEvent.keyboard("5");
    expect(screen.getByRole("dialog", { name: "Valeur calculée" })).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("takes a quantity with a comma in French, and writes the exact decimal of the contract", async () => {
    const client = serve();
    render(grid());
    cell(DISBURSEMENT, "quantity").focus();
    await userEvent.keyboard("1 234,5{Enter}");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(written(client)[0]?.body).toMatchObject({ quantity: "1234.5" });
  });

  it("takes an amount with a point in English, and writes the exact decimal of the contract", async () => {
    const client = serve();
    render(grid("en"));
    cell(DISBURSEMENT, "unit_disbursement").focus();
    await userEvent.keyboard("{F2}");
    expect(screen.getByRole("textbox", { name: "Unit disbursement" })).toHaveValue("1234.56");
    await userEvent.keyboard("{Control>}a{/Control}1,250.5{Enter}");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(written(client)[0]?.body).toMatchObject({ unit_disbursement: "1250.5" });
  });

  it("keeps open an entry that holds no number of the language, and says so", async () => {
    const client = serve();
    render(grid());
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("12.5{Enter}");
    const field = screen.getByRole("textbox", { name: "Charge (h)" });
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAccessibleDescription(
      "Ce n’est pas un nombre : saisissez-le comme 1 234,5.",
    );
    await expectAccessible(document.body);
    // An amount keeps two decimals at most.
    await userEvent.keyboard("{Escape}{ArrowRight}");
    await userEvent.keyboard("3,456{Enter}");
    expect(screen.getByRole("textbox", { name: "Débours unit." })).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    // Left elsewhere, it is abandoned.
    await userEvent.click(cell(0, "label"));
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(written(client)).toEqual([]);
  });

  it("empties an effort by an entry left blank", async () => {
    const client = serve();
    render(grid());
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("{F2}{Control>}a{/Control}{Backspace}{Enter}");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(written(client)[0]?.body).toMatchObject({ hours: null });
  });

  it("is accessible while a cell is entered", async () => {
    serve();
    render(grid());
    cell(LABOUR, "label").focus();
    await userEvent.keyboard("{F2}");
    expect(screen.getByRole("textbox", { name: "Libellé" })).toHaveFocus();
    await expectAccessible(document.body);
    await userEvent.keyboard("{Escape}{ArrowRight}{Enter}");
    expect(screen.getByRole("combobox", { name: "Catégorie" })).toHaveFocus();
    await expectAccessible(document.body);
  });

  it("shows what was validated until the server answers, then the row it answered", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    serve(
      {},
      new Promise((resolve) => {
        answer = resolve;
      }),
    );
    render(grid());
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("15{Enter}");
    expect(cell(LABOUR, "hours")).toHaveTextContent(/^15$/);
    expect(cell(LABOUR, "hours")).toHaveAttribute("aria-busy", "true");
    answer();
    await vi.waitFor(() => {
      expect(cell(LABOUR, "hours")).toHaveTextContent(/^14$/);
    });
    expect(cell(LABOUR, "hours")).not.toHaveAttribute("aria-busy");
  });
});

describe("a write the server refuses", () => {
  it("offers to reload a line changed since it was read, the cell left as it was", async () => {
    serve({ [LINE]: { problem: { code: "STALE_LOCK_VERSION", status: 412 } } });
    render(grid());
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("15{Enter}");
    const alert = await screen.findByRole("alert");
    expect(within(alert).getByRole("button", { name: "Recharger" })).toBeInTheDocument();
    expect(cell(LABOUR, "hours")).toHaveTextContent(/^12,5$/);
    await userEvent.click(within(alert).getByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalled();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("explains a conflict, and says the API is out of reach", async () => {
    serve({ [LINE]: { problem: { code: "REVISION_MARKED", status: 409 } } });
    const { rerender } = render(grid());
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("15{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(/marquée/);
    server.client = unreachable();
    rerender(grid());
    cell(LABOUR, "quantity").focus();
    await userEvent.keyboard("3{Enter}");
    await vi.waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Le service est injoignable");
    });
    expect(cell(LABOUR, "quantity")).toHaveTextContent(/^1$/);
  });

  it("drops an answer that comes once the page has been read anew", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    serve(
      { [LINE]: { problem: { code: "STALE_LOCK_VERSION", status: 412 } } },
      new Promise((resolve) => {
        answer = resolve;
      }),
    );
    const { rerender } = render(grid());
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("15{Enter}");
    // A sort, a search, a reload: the page reads the structure anew before the server answers.
    rerender(grid("fr", structuredClone(estimate)));
    expect(cell(LABOUR, "hours")).toHaveTextContent(/^12,5$/);
    await act(async () => {
      answer();
      await Promise.resolve();
    });
    expect(screen.queryByRole("alert")).toBeNull();
    expect(cell(LABOUR, "hours")).toHaveTextContent(/^12,5$/);
  });
});

describe("an entry refused before it leaves", () => {
  it("says a label may be neither blank nor longer than the contract takes", async () => {
    const client = serve();
    render(grid());
    cell(LABOUR, "label").focus();
    await userEvent.keyboard("{F2}");
    const field = screen.getByRole("textbox", { name: "Libellé" });
    expect(field).toHaveAttribute("maxlength", "300");
    await userEvent.keyboard("{Control>}a{/Control}{Backspace} {Enter}");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAccessibleDescription("Cette cellule ne peut pas rester vide.");
    expect(written(client)).toEqual([]);
  });

  it("says a quantity may not be emptied, and an amount keeps two decimals at most", async () => {
    const client = serve();
    render(grid());
    cell(DISBURSEMENT, "quantity").focus();
    await userEvent.keyboard("{F2}{Control>}a{/Control}{Backspace}{Enter}");
    expect(screen.getByRole("textbox", { name: "Qté" })).toHaveAccessibleDescription(
      "Cette cellule ne peut pas rester vide.",
    );
    await userEvent.keyboard("{Escape}{ArrowRight}{ArrowRight}");
    await userEvent.keyboard("3,456{Enter}");
    expect(screen.getByRole("textbox", { name: "Débours unit." })).toHaveAccessibleDescription(
      "Un montant a deux décimales au plus : saisissez-le comme 1\u202f234,56.",
    );
    expect(written(client)).toEqual([]);
  });

  it("validates nothing when the window is left, the field keeping the focus of its document", async () => {
    const client = serve();
    render(grid());
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("15");
    const field = screen.getByRole("textbox", { name: "Charge (h)" });
    expect(field).toHaveFocus();
    fireEvent.blur(field);
    expect(screen.getByRole("textbox", { name: "Charge (h)" })).toHaveValue("15");
    expect(written(client)).toEqual([]);
  });

  it("follows its row, by its identity, when the page reads the rows anew in another order", async () => {
    serve();
    const { rerender } = render(grid());
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("15");
    // The same rows, read anew and sorted otherwise: the line of labour last.
    const read = structuredClone(estimate);
    const labour = read.items.splice(LABOUR, 1);
    rerender(grid("fr", { ...read, items: [...read.items, ...labour] }));
    const last = read.items.length;
    expect(within(cell(last, "hours")).getByRole("textbox", { name: "Charge (h)" })).toHaveValue(
      "15",
    );
  });
});

describe("a write the server answers otherwise", () => {
  it("keeps a refusal told when a later write succeeds", async () => {
    serve({
      [LINE]: [{ problem: { code: "STALE_LOCK_VERSION", status: 412 } }, "estimate_line_updated"],
    });
    render(grid());
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("15{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(/modifié cette donnée/);
    cell(LABOUR, "quantity").focus();
    await userEvent.keyboard("3{Enter}");
    await vi.waitFor(() => {
      expect(cell(LABOUR, "hours")).toHaveTextContent(/^14$/);
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/modifié cette donnée/);
  });

  it("tells an answer about another row as a failure of the service, the row left as it was", async () => {
    // The fake back answers the line of labour, whatever line is written.
    serve();
    render(grid());
    cell(DISBURSEMENT, "quantity").focus();
    await userEvent.keyboard("3{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(/inattendue|erreur/i);
    expect(cell(DISBURSEMENT, "quantity")).toHaveTextContent(/^1$/);
    expect(cell(LABOUR, "hours")).toHaveTextContent(/^12,5$/);
  });
});

describe("a grid the revision does not let the caller enter", () => {
  it("offers no entry: a digit opens no field, every cell read only, nothing written", async () => {
    const client = serve();
    render(grid("fr", estimate, false));
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("{Enter}5{F2}");
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(cell(LABOUR, "hours")).toHaveAttribute("aria-readonly", "true");
    expect(
      [...screen.getByRole("grid").querySelectorAll("td[data-column]")].every(
        (element) => element.getAttribute("aria-readonly") === "true",
      ),
    ).toBe(true);
    expect(written(client)).toEqual([]);
  });
});
