// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { createEvent, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  held,
  type Problem,
} from "@/test/fixtures";

import { Kanban } from "./kanban";
import { columnsOf, type KanbanColumns, type StartableTasks } from "./kanban-cards";

// The gestures of the cards: the cards are those the contract lists (`startable_tasks`), the answers
// of the gestures its examples, and the fake back keeps nothing — it answers the example whatever
// was sent, so that what a gesture sends is read in the calls it records, and what the screen does
// with the answer in the card it shows.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ refresh: vi.fn() }));

// A gesture whose server action rejects, the API out of reach as `fetch` rejects in the browser.
const failing = vi.hoisted(() => ({ on: false }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("@/api/actions/nodes", async (original) => {
  const actual = await original<typeof import("@/api/actions/nodes")>();
  return {
    ...actual,
    setTaskProgress: (...asked: Parameters<typeof actual.setTaskProgress>) =>
      failing.on
        ? Promise.reject(new TypeError("Failed to fetch"))
        : actual.setTaskProgress(...asked),
  };
});
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/kanban",
  useSearchParams: () => new URLSearchParams(),
}));

const PROGRESS =
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/progress" as const;
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const REMAINING = `/projects/${STRUCTURE.project_id}/revisions/${STRUCTURE.revision_id}/remaining`;
const REFUSED = {
  problem: example("task_reopen_not_started_refused") as Problem & { status: 409 },
};

/** The first cards of each column of an example, enough to try every gesture, few enough to be fast. */
function columnsOfExample(name: string): KanbanColumns {
  const all = columnsOf(example(name) as StartableTasks);
  return {
    not_started: all.not_started.slice(0, 4),
    started: all.started.slice(0, 4),
    completed: all.completed.slice(0, 4),
  };
}

/** Serve the fake back, the calls of the progress held until `hold` settles when it is given. */
function serve(answers: FakeAnswers, hold?: Promise<unknown>): FakeClient {
  const client = fakeClient(answers, { hold: (route) => (route === PROGRESS ? hold : undefined) });
  server.client = client;
  return client;
}

/** Render the Kanban in French, as the shell hands its texts to a screen. */
function board(columns: KanbanColumns = columnsOfExample("startable_tasks")) {
  const tree = (shown: KanbanColumns) => (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <Kanban columns={shown} structure={STRUCTURE} remaining={REMAINING} />
    </NextIntlClientProvider>
  );
  const rendered = render(tree(columns));
  return {
    ...rendered,
    again: (shown: KanbanColumns) => {
      rendered.rerender(tree(shown));
    },
  };
}

/** A column of the Kanban, by its title. */
function column(name: string): HTMLElement {
  return screen.getByRole("region", { name });
}

/** The card of a task, by its label, wherever it is. */
function card(label: string): HTMLElement {
  const found = screen.getByText(label, { selector: "span" }).closest("li");
  if (found === null) {
    throw new Error(`no card for ${label}`);
  }
  return found;
}

/** The names of the cards of a column, in order. */
function labels(name: string): string[] {
  return within(column(name))
    .queryAllByRole("listitem")
    .map((each) => within(each).getByText(/./, { selector: "span.font-medium" }).textContent);
}

/** Choose a card by a click, and open the menu of its gestures. */
async function openMenu(label: string) {
  const user = userEvent.setup();
  await user.click(card(label));
  await user.click(
    within(card(label)).getByRole("button", { name: `Gestes de la tâche ${label}` }),
  );
  return user;
}

/** Make a gesture of the menu of a card. */
async function choose(label: string, gesture: string | RegExp) {
  const user = await openMenu(label);
  await user.click(await screen.findByRole("menuitem", { name: gesture }));
  return user;
}

/** The body of the gestures the fake back received. */
function written(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === PROGRESS).map((call) => call.body);
}

/** What a drag carries, as far as the Kanban reads and writes it. */
function dataTransfer() {
  return { setData: vi.fn(), effectAllowed: "", dropEffect: "" };
}

/** Fire an event of a drag on an element. */
function drag(type: "dragStart" | "dragOver" | "drop" | "dragEnd", target: HTMLElement) {
  const event = createEvent[type](target);
  const carried = dataTransfer();
  Object.defineProperty(event, "dataTransfer", { value: carried });
  fireEvent(target, event);
  return carried;
}

/** Drag a card to a column and drop it there. */
function dragTo(label: string, name: string) {
  drag("dragStart", card(label));
  drag("dragOver", column(name));
  drag("drop", column(name));
  drag("dragEnd", card(label));
}

beforeEach(() => {
  router.refresh.mockReset();
  failing.on = false;
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 5, 3, 10, 0, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the gestures of the cards of the Kanban", () => {
  it("completes a milestone without a line from the card, at the date entered, the day's being proposed, and the answer replaces the card in its column [WF-RAE-0030-A]", async () => {
    // Un jalon sans ligne de devis est terminé depuis le Kanban, à une date saisie.
    const client = serve({ [PROGRESS]: "milestone_completed" });
    board();
    expect(labels("Non démarrées")).toContain("Réception usine");

    await choose("Réception usine", /^Terminer/);
    // The date of the event is asked, the day's proposed, and nothing is written before it is given.
    const field = await within(card("Réception usine")).findByLabelText("Date de l’événement");
    expect(field).toHaveValue("2026-06-03");
    expect(field).toHaveFocus();
    expect(written(client)).toEqual([]);

    fireEvent.change(field, { target: { value: "2026-06-02" } });
    await userEvent.click(
      within(card("Réception usine")).getByRole("button", { name: "Terminer" }),
    );

    // The state the card says the gesture sends, the date entered, the version of the node read.
    await waitFor(() => {
      expect(written(client)).toEqual([
        { progress: "completed", occurred_on: "2026-06-02", lock_version: 1 },
      ]);
    });
    const call = client.calls.find((each) => each.route === PROGRESS);
    expect(call?.path).toBe(
      `/projects/${STRUCTURE.project_id}/revisions/${STRUCTURE.revision_id}/structures/${STRUCTURE.structure_id}/nodes/01926f3a-7c00-7000-8000-000000000556/progress`,
    );
    // The card the API answers is in the column of its new state, the date it was completed on it,
    // and the focus follows it; the screen reads the tasks anew.
    await waitFor(() => {
      expect(labels("Terminées")).toContain("Réception usine");
    });
    expect(labels("Non démarrées")).not.toContain("Réception usine");
    expect(card("Réception usine")).toHaveTextContent("Terminée le 03/06/2026");
    expect(card("Réception usine")).toHaveFocus();
    expect(router.refresh).toHaveBeenCalledTimes(1);
    // In the order of the plan: row 18 after row 7, the completed tasks being 2, 5, 6, 7.
    expect(labels("Terminées")).toEqual([
      "Études de détail",
      "Revue de conception",
      "Réception des études",
      "Dossier de conception",
      "Réception usine",
    ]);
  });

  it("offers each gesture as the card lists it: the completion of a task not started is unavailable and names why, the remaining to commit leads to the grid on that task [WF-RAE-0030-A]", async () => {
    // Le passage direct de non démarrée à terminée n'est possible que pour un jalon.
    serve({});
    board();
    await openMenu("Montage des armoires sur site");
    const menu = screen.getByRole("menu", {
      name: "Gestes de la tâche Montage des armoires sur site",
    });
    const entries = within(menu).getAllByRole("menuitem");
    // In the order of the API: start, complete, enter the remaining to commit; nothing it does not list.
    expect(entries.map((entry) => entry.textContent)).toEqual([
      "Démarrer",
      "TerminerConditions non remplies : la tâche est un jalon et tâche sans ligne hors provision.",
      "Saisir le reste à engager",
    ]);
    expect(entries[0]).not.toHaveAttribute("aria-disabled");
    expect(entries[1]).toHaveAttribute("aria-disabled", "true");
    expect(entries[2]).toHaveAttribute(
      "href",
      `${REMAINING}?search=Montage+des+armoires+sur+site&progress=not_started%2Cstarted`,
    );
  });

  it("makes the board one stop of Tab, the menu button only on the card chosen, and Enter on the chosen card opens the menu [WF-IHM-0100-A]", async () => {
    serve({});
    board();
    const user = userEvent.setup();
    const label = "Montage des armoires sur site";
    // One stop of Tab for the whole board, and the arrows go from card to card.
    expect(document.querySelectorAll("li[tabindex='0']")).toHaveLength(1);
    card(label).focus();
    await user.keyboard("{ArrowDown}");
    expect(card(label)).not.toHaveFocus();
    await user.keyboard("{ArrowUp}");
    expect(card(label)).toHaveFocus();
    const button = await within(card(label)).findByRole("button", {
      name: `Gestes de la tâche ${label}`,
    });
    expect(button).toHaveAttribute("aria-haspopup", "menu");
    await user.keyboard("{Enter}");
    expect(
      await screen.findByRole("menu", { name: `Gestes de la tâche ${label}` }),
    ).toBeInTheDocument();
  });

  describe("the keyboard on the board [WF-IHM-0100-A]", () => {
    /** The card holding the one stop of Tab is the one the test says it is. */
    function expectStop(label: string) {
      expect(document.querySelector("li[tabindex='0']")).toBe(card(label));
    }

    it("reaches every card of the three columns from the first, by the keyboard alone [WF-IHM-0100-A]", async () => {
      serve({});
      const columns = columnsOfExample("startable_tasks");
      board(columns);
      const user = userEvent.setup();
      const names = (state: keyof KanbanColumns) => columns[state].map((each) => each.label);
      // The walk means nothing over an empty column: the three hold cards.
      for (const state of ["not_started", "started", "completed"] as const) {
        expect(names(state).length).toBeGreaterThan(0);
      }
      const first = names("not_started")[0] ?? "";
      expect(document.querySelector("li[tabindex='0']")).toBe(card(first));
      card(first).focus();
      const reached = new Set<string>();
      for (const [index, state] of (["not_started", "started", "completed"] as const).entries()) {
        const listed = names(state);
        if (index > 0) {
          await user.keyboard("{ArrowRight}");
        }
        for (const [place, label] of listed.entries()) {
          if (place > 0) {
            await user.keyboard("{ArrowDown}");
          }
          expect(card(label)).toHaveFocus();
          expectStop(label);
          reached.add(label);
        }
        // End goes to the last card, Home back to the first, from where the next column starts.
        await user.keyboard("{End}");
        expect(card(listed.at(-1) ?? "")).toHaveFocus();
        expectStop(listed.at(-1) ?? "");
        await user.keyboard("{Home}");
        expect(card(listed[0] ?? "")).toHaveFocus();
        expectStop(listed[0] ?? "");
      }
      expect(reached.size).toBe(
        names("not_started").length + names("started").length + names("completed").length,
      );
      // Sideways from the first card of the last column: the first of the one before.
      await user.keyboard("{ArrowLeft}");
      expect(card(names("started")[0] ?? "")).toHaveFocus();
      expectStop(names("started")[0] ?? "");
    });

    it.each([
      ["{ContextMenu}", "the menu key"],
      ["{Shift>}{F10}{/Shift}", "Shift+F10"],
    ])("opens the menu of the card with %s", async (keys) => {
      serve({});
      board();
      const user = userEvent.setup();
      const label = "Montage des armoires sur site";
      card(label).focus();
      await user.keyboard(keys);
      expect(
        await screen.findByRole("menu", { name: `Gestes de la tâche ${label}` }),
      ).toBeInTheDocument();
    });

    it("brings the focus back to the card when the menu closes with Escape, so that the arrows go on", async () => {
      serve({});
      const columns = columnsOfExample("startable_tasks");
      board(columns);
      const user = userEvent.setup();
      const label = "Montage des armoires sur site";
      card(label).focus();
      await user.keyboard("{Enter}");
      await screen.findByRole("menu");
      await user.keyboard("{Escape}");
      await waitFor(() => {
        expect(screen.queryByRole("menu")).not.toBeInTheDocument();
      });
      expect(card(label)).toHaveFocus();
      await user.keyboard("{ArrowDown}");
      expect(card(label)).not.toHaveFocus();
      expect(document.activeElement?.tagName).toBe("LI");
      expect(document.querySelector("li[tabindex='0']")).toBe(document.activeElement);
    });

    it("describes every card by the help of the board, which says that Enter opens the menu of its gestures [WF-IHM-0100-A]", () => {
      serve({});
      board();
      const help = card("Montage des armoires sur site").getAttribute("aria-describedby");
      expect(help).not.toBeNull();
      const text = document.getElementById(help ?? "")?.textContent ?? "";
      expect(text).toContain("Entrée : ouvrir le menu de ses gestes");
      expect(text).toContain("Maj + flèche droite ou gauche");
      expect(card("Pupitres opérateurs")).toHaveAccessibleDescription(text);
    });

    it("leaves Space alone on a card that lists no gesture: no menu opens, the key is not captured [WF-IHM-0100-A]", () => {
      serve({});
      const columns = columnsOfExample("startable_tasks");
      const bare = columns.completed.map((each, index) =>
        index === 0 ? { ...each, commands: [] } : each,
      );
      board({ ...columns, completed: bare });
      const target = card(bare[0]?.label ?? "");
      target.focus();
      // fireEvent returns false when the default was prevented.
      expect(fireEvent.keyDown(target, { key: " " })).toBe(true);
      expect(fireEvent.keyDown(target, { key: "Enter" })).toBe(true);
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("does not bring the focus back to the card when the menu is left by a click outside it [WF-IHM-0100-A]", async () => {
      serve({});
      board();
      const label = "Montage des armoires sur site";
      card(label).focus();
      await userEvent.keyboard("{Enter}");
      await screen.findByRole("menu");
      fireEvent.pointerDown(document.body);
      await waitFor(() => {
        expect(screen.queryByRole("menu")).not.toBeInTheDocument();
      });
      expect(card(label)).not.toHaveFocus();
      // The menu being modal, the focus goes back to its button, not to the card.
      expect(
        within(card(label)).getByRole("button", { name: `Gestes de la tâche ${label}` }),
      ).toHaveFocus();
    });

    it("gives the stop of Tab back to the first card when the card chosen leaves the reading", async () => {
      serve({});
      const columns = columnsOfExample("startable_tasks");
      const rendered = board(columns);
      const user = userEvent.setup();
      const first = columns.not_started[0]?.label ?? "";
      const second = columns.not_started[1]?.label ?? "";
      await user.click(card(second));
      expectStop(second);
      rendered.again({
        ...columns,
        not_started: columns.not_started.filter((each) => each.label !== second),
      });
      expect(document.querySelectorAll("li[tabindex='0']")).toHaveLength(1);
      expectStop(first);
    });
  });

  it("starts a task not started at the date entered, and the answer carries it to the started ones [WF-RAE-0030-A]", async () => {
    const client = serve({ [PROGRESS]: "task_started" });
    board();
    await choose("Montage des armoires sur site", "Démarrer");
    expect(
      await within(card("Montage des armoires sur site")).findByLabelText("Date de l’événement"),
    ).toHaveValue("2026-06-03");
    await userEvent.click(
      within(card("Montage des armoires sur site")).getByRole("button", { name: "Démarrer" }),
    );
    await waitFor(() => {
      expect(labels("Démarrées")).toContain("Montage des armoires sur site");
    });
    expect(written(client)).toEqual([
      { progress: "started", occurred_on: "2026-06-03", lock_version: 1 },
    ]);
    expect(card("Montage des armoires sur site")).toHaveFocus();
  });

  it("completes a task started without a line from the Kanban, as its card lists it [WF-RAE-0030-A]", async () => {
    // Une tâche feuille démarrée sans ligne de devis est terminée depuis le Kanban. The fake back
    // answers the example of another task: the card stays, and the request is what is proven.
    const client = serve({ [PROGRESS]: "milestone_completed" });
    board();
    await choose("Pupitres opérateurs", /^Terminer/);
    await userEvent.click(
      within(card("Pupitres opérateurs")).getByRole("button", { name: "Terminer" }),
    );
    await waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(written(client)[0]).toMatchObject({ progress: "completed", occurred_on: "2026-06-03" });
    // Its card lists the completion available, and the remaining to commit is not offered: it has no line.
    expect(columnsOfExample("startable_tasks").started[0]?.commands.map((c) => c.command)).toEqual([
      "complete",
    ]);
  });

  it("offers no way back to not started for a task started, in its menu [WF-RAE-0030-A]", async () => {
    // Aucune commande ne fait passer une tâche démarrée à l'état non démarré.
    const client = serve({ [PROGRESS]: "task_started" });
    board();
    expect(labels("Démarrées")).toContain("Câblage des armoires");
    await openMenu("Câblage des armoires");
    const names = within(screen.getByRole("menu"))
      .getAllByRole("menuitem")
      .map((entry) => entry.textContent);
    expect(names.join("|")).not.toMatch(/Rouvrir|Démarrer/);
    expect(written(client)).toEqual([]);
  });

  it("says on the card that no gesture leads a task started to not started, dropped or carried by the keys, and writes nothing [WF-RAE-0030-A]", async () => {
    // Aucune commande ne fait passer une tâche démarrée à l'état non démarré.
    const client = serve({ [PROGRESS]: "task_started" });
    board();
    const user = userEvent.setup();
    dragTo("Câblage des armoires", "Non démarrées");
    expect(within(card("Câblage des armoires")).getByRole("alert").textContent).toBe(
      "Aucun geste ne mène cette tâche vers la colonne « Non démarrées ».",
    );
    // The same by the keys, Shift and the left arrow.
    await user.click(card("Câblage des armoires"));
    await user.keyboard("{Shift>}{ArrowLeft}{/Shift}");
    expect(within(card("Câblage des armoires")).getByRole("alert")).toBeVisible();
    expect(written(client)).toEqual([]);
    expect(labels("Démarrées")).toContain("Câblage des armoires");
  });

  it("says on the card why a gesture a drop asks is unavailable, and writes nothing [WF-IHM-0090-A]", () => {
    const client = serve({});
    board();
    // The completion of a task not started lacks conditions: dropped on the completed ones, it says so.
    dragTo("Montage des armoires sur site", "Terminées");
    expect(within(card("Montage des armoires sur site")).getByRole("alert").textContent).toBe(
      "« Terminer » est indisponible. Conditions non remplies : la tâche est un jalon et tâche sans ligne hors provision.",
    );
    expect(client.calls.filter((each) => each.route === PROGRESS)).toEqual([]);
    expect(
      within(card("Montage des armoires sur site")).queryByLabelText("Date de l’événement"),
    ).toBeNull();
  });

  it("carries a card dropped on a column by the gesture it lists, which asks its date first, and the focus follows the card [WF-RAE-0030-A] [WF-IHM-0100-A]", async () => {
    const client = serve({ [PROGRESS]: "task_started" });
    board();
    drag("dragStart", card("Montage des armoires sur site"));
    // Only a column the card has an available gesture to is marked as a place to drop it.
    expect(column("Démarrées").className).toContain("outline-dashed");
    expect(column("Terminées").className).not.toContain("outline-dashed");
    drag("dragOver", column("Démarrées"));
    drag("drop", column("Démarrées"));
    drag("dragEnd", card("Montage des armoires sur site"));
    const field = await within(card("Montage des armoires sur site")).findByLabelText(
      "Date de l’événement",
    );
    expect(field).toHaveFocus();
    expect(written(client)).toEqual([]);
    await userEvent.keyboard("{Enter}");
    await waitFor(() => {
      expect(labels("Démarrées")).toContain("Montage des armoires sur site");
    });
    expect(written(client)).toEqual([
      { progress: "started", occurred_on: "2026-06-03", lock_version: 1 },
    ]);
    expect(card("Montage des armoires sur site")).toHaveFocus();
    expect(column("Démarrées").className).not.toContain("outline-dashed");
  });

  it("makes a card draggable only when it lists a gesture that sends a state, and never while one is written [WF-IHM-0100-A]", async () => {
    const wait = held();
    serve({ [PROGRESS]: "task_started" }, wait.until);
    const columns = columnsOfExample("startable_tasks");
    const bare = columns.completed.map((each, index) =>
      index === 0 ? { ...each, commands: [] } : each,
    );
    board({ ...columns, completed: bare });
    expect(card(bare[0]?.label ?? "")).toHaveAttribute("draggable", "false");
    expect(card("Pupitres opérateurs")).toHaveAttribute("draggable", "true");
    await choose("Montage des armoires sur site", "Démarrer");
    await userEvent.click(
      within(card("Montage des armoires sur site")).getByRole("button", { name: "Démarrer" }),
    );
    await waitFor(() => {
      expect(card("Pupitres opérateurs")).toHaveAttribute("draggable", "false");
    });
    wait.release();
    await waitFor(() => {
      expect(card("Pupitres opérateurs")).toHaveAttribute("draggable", "true");
    });
  });

  it("chooses the card dragged, which a drag with no click on it leaves unchosen, and the focus follows it to its column [WF-IHM-0100-A]", async () => {
    serve({ [PROGRESS]: "task_started" });
    board();
    await userEvent.click(card("Pupitres opérateurs"));
    expect(card("Pupitres opérateurs")).toHaveAttribute("aria-current", "true");
    dragTo("Montage des armoires sur site", "Démarrées");
    const field = await within(card("Montage des armoires sur site")).findByLabelText(
      "Date de l’événement",
    );
    expect(card("Pupitres opérateurs")).not.toHaveAttribute("aria-current", "true");
    await userEvent.type(field, "{Enter}");
    await waitFor(() => {
      expect(labels("Démarrées")).toContain("Montage des armoires sur site");
    });
    expect(card("Montage des armoires sur site")).toHaveFocus();
    expect(card("Montage des armoires sur site")).toHaveAttribute("aria-current", "true");
  });

  it("does nothing for a card dropped while a gesture is written [WF-IHM-0100-A]", async () => {
    const wait = held();
    const client = serve({ [PROGRESS]: "task_started" }, wait.until);
    board();
    await choose("Montage des armoires sur site", "Démarrer");
    await userEvent.click(
      within(card("Montage des armoires sur site")).getByRole("button", { name: "Démarrer" }),
    );
    await waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    dragTo("Mise en service", "Démarrées");
    expect(within(card("Mise en service")).queryByLabelText("Date de l’événement")).toBeNull();
    expect(within(card("Mise en service")).queryByRole("alert")).toBeNull();
    expect(written(client)).toHaveLength(1);
    wait.release();
    await waitFor(() => {
      expect(labels("Démarrées")).toContain("Montage des armoires sur site");
    });
  });

  it("is not draggable when it asks its date, nor when it lists the remaining to commit alone [WF-IHM-0100-A]", async () => {
    serve({});
    const columns = columnsOfExample("startable_tasks");
    const only = columns.not_started.map((each) =>
      each.label === "Mise en service"
        ? { ...each, commands: each.commands.filter((one) => one.command === "enter_remaining") }
        : each,
    );
    board({ ...columns, not_started: only });
    const alone = card("Mise en service");
    expect(alone).toHaveAttribute("draggable", "false");
    await userEvent.click(card("Montage des armoires sur site"));
    expect(card("Montage des armoires sur site")).toHaveAttribute("draggable", "true");
    await userEvent.keyboard("{Shift>}{ArrowRight}{/Shift}");
    await within(card("Montage des armoires sur site")).findByLabelText("Date de l’événement");
    expect(card("Montage des armoires sur site")).toHaveAttribute("draggable", "false");
  });

  it("keeps the date asked on a card when another is dropped or carried, and says so on that other [WF-IHM-0100-A]", async () => {
    const client = serve({ [PROGRESS]: "task_started" });
    board();
    const user = userEvent.setup();
    await user.click(card("Montage des armoires sur site"));
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}");
    const field = await within(card("Montage des armoires sur site")).findByLabelText(
      "Date de l’événement",
    );
    fireEvent.change(field, { target: { value: "2026-06-01" } });
    const sentence =
      "Une date est déjà demandée sur une autre tâche : validez-la ou abandonnez-la avant de demander ce geste.";
    dragTo("Mise en service", "Démarrées");
    expect(within(card("Mise en service")).getByRole("alert").textContent).toBe(sentence);
    expect(within(card("Mise en service")).queryByLabelText("Date de l’événement")).toBeNull();
    expect(
      within(card("Montage des armoires sur site")).getByLabelText("Date de l’événement"),
    ).toHaveValue("2026-06-01");
    // The same by the keys.
    await user.click(card("Mise en service"));
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}");
    expect(within(card("Mise en service")).getByRole("alert").textContent).toBe(sentence);
    expect(
      within(card("Montage des armoires sur site")).getByLabelText("Date de l’événement"),
    ).toHaveValue("2026-06-01");
    expect(written(client)).toEqual([]);
  });

  it("asks the date of a card when the card that asked its own has left the reading [WF-IHM-0100-A]", async () => {
    serve({ [PROGRESS]: "task_started" });
    const columns = columnsOfExample("startable_tasks");
    const { again } = board(columns);
    const user = userEvent.setup();
    await user.click(card("Montage des armoires sur site"));
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}");
    await within(card("Montage des armoires sur site")).findByLabelText("Date de l’événement");
    again({
      ...columns,
      not_started: columns.not_started.filter(
        (each) => each.label !== "Montage des armoires sur site",
      ),
    });
    dragTo("Mise en service", "Démarrées");
    expect(
      await within(card("Mise en service")).findByLabelText("Date de l’événement"),
    ).toBeInTheDocument();
  });

  it("carries a card by a type of its own, not as text [WF-IHM-0100-A]", () => {
    serve({ [PROGRESS]: "task_started" });
    board();
    const carried = drag("dragStart", card("Mise en service"));
    expect(carried.setData).toHaveBeenCalledWith(
      "application/x-waterfall-card",
      expect.any(String),
    );
    expect(carried.setData).not.toHaveBeenCalledWith("text/plain", expect.anything());
  });

  it("reopens a milestone completed to not started and any other task to started, as the card says it [WF-RAE-0030-A]", async () => {
    // Aucune commande ne fait passer une tâche démarrée à l'état non démarré : seul un jalon
    // terminé revient à non démarré.
    const client = serve({ [PROGRESS]: ["milestone_reopened", "task_reopened"] });
    board();
    await choose("Réception des études", "Rouvrir");
    await waitFor(() => {
      expect(labels("Non démarrées")).toContain("Réception des études");
    });
    expect(written(client)[0]).toEqual({ progress: "not_started", lock_version: 1 });
    // A task that is not a milestone reopens to started.
    await choose("Études de détail", "Rouvrir");
    await waitFor(() => {
      expect(labels("Démarrées")).toContain("Études de détail");
    });
    expect(written(client)[1]).toEqual({ progress: "started", lock_version: 1 });
    expect(card("Études de détail")).toHaveFocus();
  });

  it("tells the refusal of the API on the card, which stays where it was, and lets it be dismissed [WF-IHM-0090-A]", async () => {
    serve({ [PROGRESS]: REFUSED });
    board();
    await choose("Études de détail", "Rouvrir");
    const alert = await within(card("Études de détail")).findByRole("alert");
    expect(alert).toBeVisible();
    expect(labels("Terminées")).toContain("Études de détail");
    expect(labels("Démarrées")).not.toContain("Études de détail");
    expect(card("Études de détail")).toHaveFocus();
    await userEvent.click(
      within(card("Études de détail")).getByRole("button", { name: "Fermer l’avis" }),
    );
    expect(within(card("Études de détail")).queryByRole("alert")).toBeNull();
    expect(card("Études de détail")).toHaveFocus();
  });

  it("tells on the card an answer that does not say where the task is, moves nothing and announces nothing, and reads the tasks anew", async () => {
    // The answer of another task: it holds no node for the card written.
    const client = serve({ [PROGRESS]: "milestone_completed" });
    board();
    await choose("Montage des armoires sur site", "Démarrer");
    await userEvent.click(
      within(card("Montage des armoires sur site")).getByRole("button", { name: "Démarrer" }),
    );
    const alert = await within(card("Montage des armoires sur site")).findByRole("alert");
    expect(alert).toHaveTextContent(/ne dit pas dans quelle colonne/);
    expect(written(client)).toHaveLength(1);
    expect(labels("Non démarrées")).toContain("Montage des armoires sur site");
    expect(labels("Démarrées")).not.toContain("Montage des armoires sur site");
    expect(card("Montage des armoires sur site")).toHaveFocus();
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("tells on the card a gesture whose server action rejected, which stays where it was", async () => {
    failing.on = true;
    serve({});
    board();
    await choose("Études de détail", "Rouvrir");
    const alert = await within(card("Études de détail")).findByRole("alert");
    expect(alert).toBeVisible();
    expect(labels("Terminées")).toContain("Études de détail");
    expect(card("Études de détail")).toHaveFocus();
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });

  it("reads the tasks anew when the API refuses a gesture for the state of the task [WF-IHM-0090-A]", async () => {
    serve({ [PROGRESS]: REFUSED });
    board();
    await choose("Études de détail", "Rouvrir");
    await within(card("Études de détail")).findByRole("alert");
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("reads the tasks anew when the API refuses a gesture for a version past, and tells it on the card [WF-IHM-0090-A]", async () => {
    // The twin of the 409: the node changed since the card was read.
    serve({ [PROGRESS]: { problem: { code: "STALE_LOCK_VERSION", status: 412 } } });
    board();
    await choose("Études de détail", "Rouvrir");
    await within(card("Études de détail")).findByRole("alert");
    expect(router.refresh).toHaveBeenCalledTimes(1);
    expect(labels("Terminées")).toContain("Études de détail");
  });

  it("forgets an answer once the tasks read hold its version, which a reading at an older version does not bring back", async () => {
    serve({ [PROGRESS]: "milestone_completed" });
    const { again } = board();
    await choose("Réception usine", /^Terminer/);
    await userEvent.click(
      within(card("Réception usine")).getByRole("button", { name: "Terminer" }),
    );
    await waitFor(() => {
      expect(labels("Terminées")).toContain("Réception usine");
    });
    const old = columnsOfExample("startable_tasks");
    const [milestone] = old.not_started.filter((each) => each.label === "Réception usine");
    if (milestone === undefined) {
      throw new Error("no milestone in the example");
    }
    // The tasks are read at the version answered: the card read is the one shown.
    again({
      ...old,
      not_started: old.not_started.filter((each) => each !== milestone),
      completed: [...old.completed, { ...milestone, state: "completed", lock_version: 3 }],
    });
    expect(labels("Terminées")).toContain("Réception usine");
    // A reading at a lower version — the node is not started again there — is shown as it is read.
    again(old);
    expect(labels("Non démarrées")).toContain("Réception usine");
    expect(labels("Terminées")).not.toContain("Réception usine");
  });

  it("shows an unavailable gesture in the menu with the conditions it lacks, and does nothing when it is chosen [WF-IHM-0090-A]", async () => {
    const client = serve({});
    board();
    const user = await openMenu("Montage des armoires sur site");
    const menu = screen.getByRole("menu", {
      name: "Gestes de la tâche Montage des armoires sur site",
    });
    // The completion of this task cannot be made now: it is shown, with what is lacking.
    const completion = within(menu).getByRole("menuitem", { name: /^Terminer/ });
    expect(completion).toHaveAttribute("aria-disabled", "true");
    expect(completion).toHaveTextContent(
      "Conditions non remplies : la tâche est un jalon et tâche sans ligne hors provision.",
    );
    // Secondary: a gesture the card does not list is not in the menu at all.
    expect(within(menu).queryByRole("menuitem", { name: /^Rouvrir/ })).toBeNull();
    await user.click(completion);
    expect(
      within(card("Montage des armoires sur site")).queryByLabelText("Date de l’événement"),
    ).toBeNull();
    expect(written(client)).toEqual([]);
  });

  it("signals a milestone to complete by a text and an icon once its predecessors are completed, and it stays not started [WF-RAE-0030-A]", () => {
    // Un jalon dont tous les prédécesseurs sont terminés est signalé et reste non démarré tant que
    // personne ne le termine.
    serve({});
    board(columnsOfExample("startable_tasks_milestone"));
    const mark = within(card("Réception usine")).getByText(
      "Ses prédécesseurs sont terminés : jalon à terminer.",
    );
    expect(mark).toBeVisible();
    expect(mark.querySelector("svg")).not.toBeNull();
    expect(labels("Non démarrées")).toContain("Réception usine");
    // The tasks whose predecessors are not completed are not signalled.
    expect(
      within(card("Montage des armoires sur site")).queryByText(/jalon à terminer/),
    ).toBeNull();
  });

  it("asks nothing of the card while a gesture is written, and keeps the date asked for the card it was asked of", async () => {
    const wait = held();
    const client = serve({ [PROGRESS]: "task_started" }, wait.until);
    board();
    await choose("Montage des armoires sur site", "Démarrer");
    await userEvent.click(
      within(card("Montage des armoires sur site")).getByRole("button", { name: "Démarrer" }),
    );
    await waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(card("Montage des armoires sur site")).toHaveAttribute("aria-busy", "true");
    // Another gesture waits: its entry in the menu is unavailable, and nothing more is written.
    const user = await openMenu("Pupitres opérateurs");
    const entry = await screen.findByRole("menuitem", { name: /^Terminer/ });
    expect(entry).toHaveAttribute("aria-disabled", "true");
    await user.click(entry);
    await user.keyboard("{Escape}");
    expect(within(card("Pupitres opérateurs")).queryByLabelText("Date de l’événement")).toBeNull();
    expect(written(client)).toHaveLength(1);
    await user.click(card("Pupitres opérateurs"));
    wait.release();
    await waitFor(() => {
      expect(labels("Démarrées")).toContain("Montage des armoires sur site");
    });
    expect(card("Montage des armoires sur site")).not.toHaveAttribute("aria-busy", "true");
    // The card chosen meanwhile keeps the choice and the focus: the answer brings neither back.
    expect(card("Pupitres opérateurs")).toHaveAttribute("aria-current", "true");
    expect(card("Pupitres opérateurs")).toHaveFocus();
  });

  it("lets the cards read since win over the answers, by the version of the node", async () => {
    serve({ [PROGRESS]: "milestone_completed" });
    const { again } = board();
    await choose("Réception usine", /^Terminer/);
    await userEvent.click(
      within(card("Réception usine")).getByRole("button", { name: "Terminer" }),
    );
    await waitFor(() => {
      expect(labels("Terminées")).toContain("Réception usine");
    });
    // The tasks read again before the write is seen: the answer, a later version, stays.
    again(columnsOfExample("startable_tasks"));
    expect(labels("Terminées")).toContain("Réception usine");
    expect(labels("Non démarrées")).not.toContain("Réception usine");
    // Read once the write is seen — the same node, at the version answered, with its gestures —: the
    // card read replaces the answer, and lists what the API lists for it.
    const read = columnsOfExample("startable_tasks");
    const [milestone] = read.not_started.filter((each) => each.label === "Réception usine");
    if (milestone === undefined) {
      throw new Error("no milestone in the example");
    }
    const reopened = {
      ...read,
      not_started: read.not_started.filter((each) => each !== milestone),
      completed: [
        ...read.completed,
        {
          ...milestone,
          state: "completed" as const,
          lock_version: 3,
          completed_on: "2026-06-03",
          commands: [
            {
              command: "reopen" as const,
              is_available: true,
              missing_conditions: [],
              progress: "not_started" as const,
            },
          ],
        },
      ],
    };
    again(reopened);
    await userEvent.click(card("Réception usine"));
    await userEvent.click(
      within(card("Réception usine")).getByRole("button", {
        name: "Gestes de la tâche Réception usine",
      }),
    );
    expect(await screen.findByRole("menuitem", { name: "Rouvrir" })).toBeVisible();
  });
});

describe("the choice of a card", () => {
  it("chooses a card by a click, and one only, and offers the menu of that card alone", async () => {
    serve({});
    board();
    const user = userEvent.setup();
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    await user.click(card("Pupitres opérateurs"));
    expect(card("Pupitres opérateurs")).toHaveAttribute("aria-current", "true");
    expect(card("Réception usine")).not.toHaveAttribute("aria-current");
    await user.click(card("Réception usine"));
    expect(card("Réception usine")).toHaveAttribute("aria-current", "true");
    expect(card("Pupitres opérateurs")).not.toHaveAttribute("aria-current");
    // Its menu only is offered, and no other card has a button.
    expect(screen.getAllByRole("button")).toHaveLength(1);
  });

  it("gives the date up with Escape, writing nothing, and writes it with Enter", async () => {
    const client = serve({ [PROGRESS]: "task_started" });
    board();
    const user = await openMenu("Montage des armoires sur site");
    await user.click(await screen.findByRole("menuitem", { name: "Démarrer" }));
    const field = await within(card("Montage des armoires sur site")).findByLabelText(
      "Date de l’événement",
    );
    expect(field).toHaveFocus();
    // Escape gives the card up and the focus back to it, writing nothing.
    await user.keyboard("{Escape}");
    expect(
      within(card("Montage des armoires sur site")).queryByLabelText("Date de l’événement"),
    ).toBeNull();
    expect(card("Montage des armoires sur site")).toHaveFocus();
    expect(written(client)).toEqual([]);
    // Asked again, the Enter of the form writes it.
    await user.click(
      within(card("Montage des armoires sur site")).getByRole("button", {
        name: "Gestes de la tâche Montage des armoires sur site",
      }),
    );
    await user.click(await screen.findByRole("menuitem", { name: "Démarrer" }));
    await within(card("Montage des armoires sur site")).findByLabelText("Date de l’événement");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(labels("Démarrées")).toContain("Montage des armoires sur site");
    });
    expect(written(client)).toEqual([
      { progress: "started", occurred_on: "2026-06-03", lock_version: 1 },
    ]);
    expect(card("Montage des armoires sur site")).toHaveFocus();
  });

  it("carries a card to the neighbouring column by Shift and a sideways arrow, the equivalent of the drag, and asks the date first [WF-IHM-0100-A]", async () => {
    const client = serve({ [PROGRESS]: "task_started" });
    board();
    const user = userEvent.setup();
    await user.click(card("Montage des armoires sur site"));
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}");
    const field = await within(card("Montage des armoires sur site")).findByLabelText(
      "Date de l’événement",
    );
    expect(field).toHaveFocus();
    // Escape gives the card up and the focus back to it, writing nothing.
    await user.keyboard("{Escape}");
    expect(
      within(card("Montage des armoires sur site")).queryByLabelText("Date de l’événement"),
    ).toBeNull();
    expect(card("Montage des armoires sur site")).toHaveFocus();
    expect(written(client)).toEqual([]);
    // Asked again, the Enter of the form writes it.
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}{Enter}");
    await waitFor(() => {
      expect(labels("Démarrées")).toContain("Montage des armoires sur site");
    });
    expect(written(client)).toEqual([
      { progress: "started", occurred_on: "2026-06-03", lock_version: 1 },
    ]);
    expect(card("Montage des armoires sur site")).toHaveFocus();
  });

  it("asks for a date before it writes: an empty one is refused on the field", async () => {
    const client = serve({});
    board();
    await choose("Pupitres opérateurs", /^Terminer/);
    const field = await within(card("Pupitres opérateurs")).findByLabelText("Date de l’événement");
    fireEvent.change(field, { target: { value: "" } });
    await userEvent.click(
      within(card("Pupitres opérateurs")).getByRole("button", { name: "Terminer" }),
    );
    expect(within(card("Pupitres opérateurs")).getByRole("alert")).toHaveTextContent(
      "Saisissez la date de l’événement.",
    );
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(written(client)).toEqual([]);
  });

  it("is accessible with a card chosen and the date asked on it", async () => {
    serve({});
    const { container } = board();
    await choose("Pupitres opérateurs", /^Terminer/);
    await expectAccessible(container);
  });
});
