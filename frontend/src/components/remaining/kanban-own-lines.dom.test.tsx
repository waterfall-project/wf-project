// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { createEvent, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";

import { Kanban } from "./kanban";
import { columnsOf, type KanbanColumns, type StartableTasks } from "./kanban-cards";

// The card of a summary task that awaits its own lines (WF-PLA-0040, WF-IHM-0070): the Kanban lists
// it in the column started (#1851), and the cards here are those of the example
// `startable_tasks_awaiting_own_lines` of `listStartableTasks`, read as the service answers it. The
// mark is what the reading says of the task, and the gestures of the card are what the reading
// lists: the screen deduces nothing from the subordinates nor from the nature of the task.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ refresh: vi.fn(), replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/kanban",
  useSearchParams: () => new URLSearchParams(),
}));

const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const MARK = "Lignes propres ouvertes";
const PROGRESS =
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/progress" as const;

/** The columns of the example of the Kanban that lists the summary task, as the service answers it. */
function awaiting(): KanbanColumns {
  const all = columnsOf(example("startable_tasks_awaiting_own_lines") as StartableTasks);
  // The summary task and the first cards of each column: enough to try it, few enough to be fast.
  return {
    not_started: all.not_started.slice(0, 4),
    started: all.started.slice(0, 4),
    completed: all.completed.slice(0, 4),
  };
}

/** Render the Kanban in French on some columns. */
function board(columns: KanbanColumns) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <Kanban
        columns={columns}
        structure={STRUCTURE}
        remaining="/projects/p/revisions/r/remaining"
        filters={{ text: "", ready: false }}
      />
    </NextIntlClientProvider>,
  );
}

/** The card of a task, by its label. */
function card(label: string): HTMLElement {
  const found = screen.getByText(label, { selector: "span" }).closest("li");
  if (found === null) {
    throw new Error(`no card for ${label}`);
  }
  return found;
}

/** A column of the Kanban, by its title. */
function column(name: string): HTMLElement {
  return screen.getByRole("region", { name });
}

/** Fire an event of a drag on an element. */
function drag(type: "dragStart" | "dragOver" | "drop" | "dragEnd", target: HTMLElement) {
  const event = createEvent[type](target);
  Object.defineProperty(event, "dataTransfer", {
    value: { setData: vi.fn(), effectAllowed: "", dropEffect: "" },
  });
  fireEvent(target, event);
}

describe("the card of a task that awaits its own lines", () => {
  it("is listed in the column started and bears an icon and a text, no other card of the example does [WF-PLA-0040-A]", () => {
    // Une récapitulative dont toutes les subordonnées sont terminées et dont une ligne propre porte
    // un reste à engager de 500 est démarrée et signalée : la colonne démarrée la liste avec sa
    // facette, la carte lit le signal sans rien déduire des subordonnées.
    board(columnsOf(example("startable_tasks_awaiting_own_lines") as StartableTasks));
    const mark = within(card("Études")).getByText(MARK);
    expect(within(column("Démarrées")).getByText(MARK)).toBe(mark);
    expect(mark).toBeVisible();
    expect(mark.closest("p")?.querySelector("svg")).not.toBeNull();
    expect(within(card("Études de détail")).queryByText(MARK)).toBeNull();
    expect(screen.getAllByText(MARK)).toHaveLength(1);
  });

  it("offers the entry of the remaining to commit, the completion unavailable for want of a task without lines, and neither start nor reopening [WF-PLA-0040-A]", async () => {
    // La carte offre enter_remaining, disponible, et complete, indisponible faute de
    // task_without_lines ; ni start ni reopen : le front ne déduit rien des subordonnées.
    board(awaiting());
    const user = userEvent.setup();
    await user.click(card("Études"));
    await user.click(
      within(card("Études")).getByRole("button", { name: "Gestes de la tâche Études" }),
    );
    const menu = screen.getByRole("menu", { name: "Gestes de la tâche Études" });
    const entries = within(menu).getAllByRole("menuitem");
    expect(entries.map((entry) => entry.textContent)).toEqual([
      expect.stringMatching(
        /^TerminerCondition non remplie\u00A0: tâche sans ligne hors provision\./,
      ),
      "Saisir le reste à engager",
    ]);
    expect(entries[0]).toHaveAttribute("aria-disabled", "true");
    expect(entries[1]).not.toHaveAttribute("aria-disabled");
    expect(entries[1]).toHaveAttribute("href", expect.stringContaining("/remaining?"));
  });

  it("refuses the drop in the column completed by the gesture the card lists, not by the nature of the task, and writes nothing [WF-PLA-0040-A]", () => {
    // Le dépôt suit available_commands : complete est indisponible, la carte le dit et rien n'est
    // écrit ; la colonne n'est pas proposée comme lieu de dépôt.
    const client = fakeClient({});
    server.client = client;
    board(awaiting());
    drag("dragStart", card("Études"));
    expect(column("Terminées")).not.toHaveClass("outline-dashed");
    drag("dragOver", column("Terminées"));
    drag("drop", column("Terminées"));
    drag("dragEnd", card("Études"));
    expect(within(card("Études")).getByRole("alert").textContent).toMatch(
      /^«\u00A0Terminer\u00A0» est indisponible\. Condition non remplie\u00A0: tâche sans ligne hors provision\./,
    );
    expect(client.calls.filter((each) => each.route === PROGRESS)).toEqual([]);
    // Aucun geste ne mène la carte vers la colonne des non démarrées.
    drag("dragStart", card("Études"));
    drag("drop", column("Non démarrées"));
    drag("dragEnd", card("Études"));
    expect(within(card("Études")).getByRole("alert").textContent).toContain("Aucun geste");
    expect(client.calls.filter((each) => each.route === PROGRESS)).toEqual([]);
  });

  it("is marked on no card of the example of the Kanban, whose reading says it of none [WF-PLA-0040-A]", () => {
    // Une récapitulative dont la seule ligne propre est une provision est terminée et n'est pas
    // signalée : une tâche que la lecture ne dit pas en attente de ses lignes propres ne l'est pas.
    const all = columnsOf(example("startable_tasks") as StartableTasks);
    board({
      not_started: all.not_started.slice(0, 4),
      started: all.started.slice(0, 4),
      completed: all.completed.slice(0, 4),
    });
    expect(screen.queryByText(MARK)).toBeNull();
    // Des cartes bien rendues, pour qu'un rendu vide ne fasse pas passer le test.
    expect(screen.getAllByRole("listitem").length).toBeGreaterThan(0);
  });
});
