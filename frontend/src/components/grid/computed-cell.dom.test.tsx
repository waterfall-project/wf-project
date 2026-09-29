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
const estimate = example("nodes_estimate") as NodeList;
const planning = example("nodes_planning") as NodeList;

/** Render a grid of a structure on an answer, in a language. */
function renderGrid(grid: "estimate" | "planning", locale: Locale = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      {grid === "estimate" ? (
        <EstimateGrid nodes={estimate} query={NO_QUERY} preferences={undefined} />
      ) : (
        <PlanningGrid nodes={planning} query={NO_QUERY} preferences={undefined} />
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

/** The texts of the paragraphs of the refusal, and the rows it names. */
function said(dialog: HTMLElement) {
  return {
    paragraphs: [...dialog.querySelectorAll("p")].map((paragraph) => paragraph.textContent),
    rows: within(dialog)
      .queryAllByRole("listitem")
      .map((item) => ({
        text: item.textContent,
        nature: within(item).getByRole("img").getAttribute("aria-label"),
      })),
  };
}

beforeEach(() => {
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});

afterEach(() => {
  vi.restoreAllMocks();
});

// Number, label, quantity, hours, unit disbursement, budgeted, re-estimated.
const QUANTITY = 2;
const HOURS = 3;
const DISBURSEMENT = 4;
const BUDGETED = 5;
const REESTIMATED = 6;
// Number, label, mode, duration, start, finish, progress, float, predecessors.
const DURATION = 3;
const START = 4;
const FINISH = 5;
const PROGRESS = 6;

describe("a value of a grid the server computes", () => {
  it("is not entered in a line of labour, and does not look like its effort in hours [WF-IHM-0030-A]", async () => {
    renderGrid("estimate");
    const labour = "Raccordement des borniers";
    const hours = cell(labour, HOURS);
    const amount = cell(labour, BUDGETED);
    // The effort is entered: its value alone, on the background of the page.
    expect(hours).toHaveTextContent(/^12,5$/);
    expect(within(hours).queryByRole("button")).toBeNull();
    expect(within(hours).queryByRole("img")).toBeNull();
    expect(hours).toHaveClass("bg-background");
    // The amount is computed: shaded, marked Σ and named so, whatever the colour.
    expect(amount).toHaveClass("bg-muted");
    const mark = within(amount).getByRole("button", { name: /^Calculé 1\s000,00$/ });
    expect(within(mark).getByRole("img", { name: "Calculé" })).toBeInTheDocument();
    expect(within(cell(labour, REESTIMATED)).getByRole("button")).toHaveAccessibleName(
      /^Calculé 1\s000,00$/,
    );

    // A try to enter it is refused, beside it, naming what it depends on; nothing opens to type.
    await userEvent.click(mark);
    expect(said(refusal())).toEqual({
      paragraphs: [
        "Valeur calculée",
        "Budgété ne se saisit pas\u00a0: Waterfall calcule cette valeur.",
        "Le montant d’une ligne de main-d’œuvre est le produit de sa quantité, de sa charge et du taux horaire de sa catégorie pour l’année de référence, projeté sur son année de consommation.",
        "Le montant budgété est celui que la révision de référence a fixé.",
      ],
      rows: [],
    });
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("spinbutton")).toBeNull();
  });

  it("refuses to change the finish date of a summary task, naming its subordinates [WF-IHM-0030-A]", async () => {
    renderGrid("planning");
    const finish = within(cell("Études", FINISH)).getByRole("button", {
      name: /^Calculé 24\/04\/2026$/,
    });
    expect(finish).toHaveAttribute("aria-haspopup", "dialog");
    expect(finish).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(finish);
    const dialog = refusal();
    expect(said(dialog)).toEqual({
      paragraphs: [
        "Valeur calculée",
        "Fin ne se saisit pas\u00a0: Waterfall calcule cette valeur.",
        "Une tâche récapitulative tient ses dates, sa durée et son avancement de ses subordonnées.",
        "Elle dépend de\u00a0:",
      ],
      rows: [
        { text: "2Études de détail", nature: "Tâche" },
        { text: "3Pupitres opérateurs", nature: "Tâche" },
        { text: "4Revue de conception", nature: "Tâche" },
        { text: "5Réception des études", nature: "Jalon" },
      ],
    });
    expect(within(dialog).getByRole("list", { name: "Elle dépend de\u00a0:" })).toBeInTheDocument();
    expect(within(cell("Études", FINISH)).getByRole("button")).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    await expectAccessible(document.body);
  });

  it("is refused from the keyboard as from the pointer, and gives the focus back to its cell", async () => {
    renderGrid("planning");
    const start = within(cell("Études", START)).getByRole("button");
    start.focus();
    await userEvent.keyboard("{Enter}");
    expect(refusal()).toHaveTextContent(/^Valeur calculéeDébut ne se saisit pas/);
    expect(document.activeElement).not.toBe(document.body);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    const trigger = within(cell("Études", START)).getByRole("button");
    expect(trigger).toHaveFocus();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    // Pressed again, it opens again: the refusal is the same.
    await userEvent.keyboard(" ");
    expect(refusal()).toHaveTextContent(/Début ne se saisit pas/);
  });

  it("is read row by row: the dates of a task in manual mode are entered, those of the others computed", () => {
    renderGrid("planning");
    for (const position of [DURATION, START, FINISH, PROGRESS]) {
      expect(within(cell("Études", position)).queryByRole("button")).not.toBeNull();
      expect(within(cell("Pupitres opérateurs", position)).queryByRole("button")).toBeNull();
    }
    // A task in automatic mode computes its dates, and enters its duration and its progress.
    expect(within(cell("Revue de conception", START)).queryByRole("button")).not.toBeNull();
    expect(within(cell("Revue de conception", FINISH)).queryByRole("button")).not.toBeNull();
    expect(within(cell("Revue de conception", DURATION)).queryByRole("button")).toBeNull();
    expect(within(cell("Revue de conception", PROGRESS)).queryByRole("button")).toBeNull();
    expect(cell("Revue de conception", DURATION)).toHaveClass("bg-background");
  });

  it("marks the quantity and the unit disbursement of a provision, which come from its risk", async () => {
    renderGrid("estimate");
    const provision = "Provision — risque de reprise du câblage";
    for (const position of [QUANTITY, DISBURSEMENT]) {
      expect(cell(provision, position)).toHaveClass("bg-muted");
      expect(within(cell("Borniers", position)).queryByRole("button")).toBeNull();
    }
    expect(within(cell(provision, HOURS)).queryByRole("button")).toBeNull();
    await userEvent.click(within(cell(provision, QUANTITY)).getByRole("button"));
    expect(said(refusal()).paragraphs.slice(1)).toEqual([
      "Qté ne se saisit pas\u00a0: Waterfall calcule cette valeur.",
      "Une ligne de provision tient ses grandeurs de son risque\u00a0: sa gravité pondérée par sa probabilité.",
    ]);
  });

  it("names what the amount of a task depends on: the lines it bears", async () => {
    renderGrid("estimate");
    await userEvent.click(within(cell("Câblage des armoires", REESTIMATED)).getByRole("button"));
    expect(said(refusal()).rows).toEqual([
      { text: "3Raccordement des borniers", nature: "Ligne de main-d’œuvre" },
      { text: "4Borniers", nature: "Ligne de débours" },
      { text: "5Provision — risque de reprise du câblage", nature: "Ligne de provision" },
    ]);
  });

  it("is refused in English too", async () => {
    renderGrid("planning", "en");
    await userEvent.click(
      within(cell("Études", FINISH)).getByRole("button", { name: /^Computed/ }),
    );
    expect(said(refusal("Computed value")).paragraphs).toEqual([
      "Computed value",
      "Finish cannot be entered: Waterfall computes this value.",
      "A summary task takes its dates, its duration and its progress from its subtasks.",
      "It depends on:",
    ]);
  });
});
