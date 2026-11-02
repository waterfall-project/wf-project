// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import type { KanbanFilters } from "./address";
import { Kanban } from "./kanban";
import { columnsOf, type KanbanColumns, type StartableTasks } from "./kanban-cards";

// The filters of the Kanban (US-0730): the cards are those the contract lists (`startable_tasks_
// milestone`, whose only task ready is a milestone), the filters those the address names, which the
// page reads and the Kanban is given; the fake router records the addresses the bar writes.
const router = vi.hoisted(() => ({ refresh: vi.fn(), replace: vi.fn(), push: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/kanban",
  useSearchParams: () => new URLSearchParams("subproject_id=s"),
}));

const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const NONE: KanbanFilters = { text: "", ready: false };

/**
 * The first cards of each column of the example, one task more made ready — the example has the
 * milestone alone — to try the mark on a task that is not one.
 */
function columns(): KanbanColumns {
  const all = columnsOf(example("startable_tasks_milestone") as StartableTasks);
  return {
    not_started: all.not_started
      .slice(0, 4)
      .map((card) =>
        card.label === "Mise en service" ? { ...card, predecessors_completed: true } : card,
      ),
    started: all.started.slice(0, 4),
    completed: all.completed.slice(0, 4),
  };
}

/** Render the Kanban in French under the filters given; `again` renders it under others. */
function board(filters: KanbanFilters = NONE) {
  const tree = (read: KanbanFilters) => (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <Kanban
        columns={columns()}
        structure={STRUCTURE}
        remaining="/projects/p/revisions/r/remaining"
        filters={read}
      />
    </NextIntlClientProvider>
  );
  const rendered = render(tree(filters));
  return {
    ...rendered,
    again: (read: KanbanFilters) => {
      rendered.rerender(tree(read));
    },
  };
}

/** The names of the cards of a column, in order. */
function labels(name: string): string[] {
  return within(screen.getByRole("region", { name }))
    .queryAllByRole("listitem")
    .map((each) => within(each).getByText(/./, { selector: "span.font-medium" }).textContent);
}

/** The card of a task, by its label. */
function card(label: string): HTMLElement {
  const found = screen.getByText(label, { selector: "span" }).closest("li");
  if (found === null) {
    throw new Error(`no card for ${label}`);
  }
  return found;
}

beforeEach(() => {
  router.replace.mockReset();
  router.push.mockReset();
});

describe("the filters of the Kanban", () => {
  it("narrows the three columns to the label searched, whatever the case and the accents [WF-RAE-0030-A]", () => {
    board({ text: "ETUDES", ready: false });
    expect(labels("Terminées")).toEqual(["Études de détail", "Réception des études"]);
    expect(labels("Non démarrées")).toEqual([]);
    expect(labels("Démarrées")).toEqual([]);
    expect(screen.getAllByText("Aucune tâche ne correspond.")).toHaveLength(2);
  });

  it("keeps among the tasks not started those the API says are ready, and leaves the other columns as they are [WF-RAE-0030-A]", () => {
    board({ text: "", ready: true });
    expect(labels("Non démarrées")).toEqual(["Réception usine", "Mise en service"]);
    expect(labels("Démarrées")).toHaveLength(4);
    expect(labels("Terminées")).toHaveLength(4);
  });

  it("combines the label and the tasks ready, the label narrowing the other columns too [WF-RAE-0030-A]", () => {
    board({ text: "mise", ready: true });
    expect(labels("Non démarrées")).toEqual(["Mise en service"]);
    expect(labels("Démarrées")).toEqual([]);
  });

  it("says in the name of a column how many of its cards are shown, and says nothing of one that shows all [WF-RAE-0030-A]", () => {
    board({ text: "", ready: true });
    expect(screen.getByRole("heading", { name: "Non démarrées 2 sur 4" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Démarrées" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Terminées" })).toBeInTheDocument();
  });

  it("counts the cards a label hides in every column [WF-RAE-0030-A]", () => {
    board({ text: "études", ready: false });
    expect(screen.getByRole("heading", { name: "Terminées 2 sur 4" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Non démarrées 0 sur 4" })).toBeInTheDocument();
  });

  it("shows every card again once the address names no filter [WF-RAE-0030-A]", () => {
    const { again } = board({ text: "études", ready: true });
    again(NONE);
    expect(labels("Non démarrées")).toHaveLength(4);
    expect(screen.getByRole("heading", { name: "Non démarrées" })).toBeInTheDocument();
  });
});

describe("the mark of a task ready to start", () => {
  it("is on every task not started the API says is ready, by an icon and a text, the filter or none [WF-IHM-0070-A]", () => {
    const { again } = board();
    expect(within(card("Mise en service")).getByText("Prête à démarrer")).toBeVisible();
    expect(within(card("Mise en service")).queryByText(/jalon à terminer/)).toBeNull();
    expect(
      within(card("Montage des armoires sur site")).queryByText("Prête à démarrer"),
    ).toBeNull();
    // A task started is not marked.
    expect(within(card("Pupitres opérateurs")).queryByText("Prête à démarrer")).toBeNull();
    again({ text: "", ready: true });
    expect(within(card("Mise en service")).getByText("Prête à démarrer")).toBeVisible();
  });

  it("sits beside the mark of the milestone, which does not change [WF-RAE-0030-A]", () => {
    board();
    const milestone = within(card("Réception usine"));
    expect(milestone.getByText("Prête à démarrer")).toBeVisible();
    expect(milestone.getByText(/jalon à terminer/)).toBeVisible();
  });

  it("is lisible without colour: a text, and an icon that is decoration [WF-IHM-0070-A]", () => {
    board();
    const mark = within(card("Mise en service")).getByText("Prête à démarrer");
    expect(mark.closest("p")?.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("passes the accessibility rules with its filters [WF-IHM-0070-A]", async () => {
    const { container } = board({ text: "mise", ready: true });
    await expectAccessible(container);
  });
});

describe("the choice of a card under a filter", () => {
  it("is lost when a filter hides the card, the stop of Tab going to the first card shown of its column [WF-RAE-0030-A]", async () => {
    const user = userEvent.setup();
    const { again } = board();
    await user.click(card("Montage des armoires sur site"));
    expect(card("Montage des armoires sur site")).toHaveAttribute("aria-current", "true");
    again({ text: "", ready: true });
    expect(screen.queryByRole("listitem", { current: true })).toBeNull();
    expect(card("Réception usine")).toHaveAttribute("tabindex", "0");
    expect(card("Mise en service")).toHaveAttribute("tabindex", "-1");
    // Lifting the filter does not bring the choice back.
    again(NONE);
    expect(screen.queryByRole("listitem", { current: true })).toBeNull();
    expect(card("Réception usine")).toHaveAttribute("tabindex", "0");
  });

  it("keeps the choice of a card the filter shows, and leads the arrows over the cards shown alone [WF-IHM-0100-A]", async () => {
    const user = userEvent.setup();
    board({ text: "", ready: true });
    await user.click(card("Réception usine"));
    await user.keyboard("{ArrowDown}");
    expect(card("Mise en service")).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(card("Mise en service")).toHaveFocus();
  });
});

describe("the bar of the filters", () => {
  it("writes the label searched in the address, the rest of it kept, replacing the entry of the history [WF-RAE-0030-A]", async () => {
    const user = userEvent.setup();
    board();
    await user.type(screen.getByRole("searchbox", { name: "Rechercher une tâche" }), "mise{Enter}");
    expect(router.replace).toHaveBeenCalledWith(
      "/projects/p/revisions/r/kanban?subproject_id=s&q=mise",
      {
        scroll: false,
      },
    );
    expect(router.push).not.toHaveBeenCalled();
  });

  it("writes the tasks ready in the address, and lifts them [WF-RAE-0030-A]", async () => {
    const user = userEvent.setup();
    const { again } = board();
    await user.click(screen.getByRole("checkbox", { name: "Tâches prêtes" }));
    expect(router.replace).toHaveBeenLastCalledWith(
      "/projects/p/revisions/r/kanban?subproject_id=s&ready=1",
      { scroll: false },
    );
    again({ text: "", ready: true });
    await user.click(screen.getByRole("checkbox", { name: "Tâches prêtes" }));
    expect(router.replace).toHaveBeenLastCalledWith(
      "/projects/p/revisions/r/kanban?subproject_id=s",
      {
        scroll: false,
      },
    );
  });

  it("shows the label and the box the address holds [WF-RAE-0030-A]", () => {
    board({ text: "mise", ready: true });
    expect(screen.getByRole("searchbox", { name: "Rechercher une tâche" })).toHaveValue("mise");
    expect(screen.getByRole("checkbox", { name: "Tâches prêtes" })).toBeChecked();
  });
});
