// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { Kanban } from "./kanban";
import { cardOf, columnsOf, type KanbanColumns, type StartableTasks } from "./kanban-cards";

// The mark of the own lines still open on the card of the Kanban (WF-PLA-0040, WF-IHM-0070): the
// cards of a summary task come from the example `nodes_awaiting_own_lines`, whose nodes are those
// the Kanban lists (`KanbanTask` is a `Node`), and the mark is what the reading says of the task.
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

describe("the card of a task that awaits its own lines", () => {
  it("bears an icon and a text when the reading says it, and no other card does [WF-PLA-0040-A]", () => {
    // Une récapitulative dont toutes les subordonnées sont terminées et dont une ligne propre porte
    // un reste à engager de 500 est démarrée et signalée : la carte lit le signal, sans rien
    // déduire des subordonnées.
    const nodes = (
      example("nodes_awaiting_own_lines") as { items: components["schemas"]["Node"][] }
    ).items;
    const tasks = nodes.filter((node) => node.kind === "task").slice(0, 2);
    board({
      not_started: [],
      started: tasks.map((node) => cardOf(node, "started")),
      completed: [],
    });
    const mark = within(card("Études")).getByText(MARK);
    expect(mark).toBeVisible();
    expect(mark.closest("p")?.querySelector("svg")).not.toBeNull();
    expect(within(card("Études de détail")).queryByText(MARK)).toBeNull();
    expect(screen.getAllByText(MARK)).toHaveLength(1);
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
  });
});
