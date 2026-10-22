// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

  it("tells the refusal of the API on the card, which stays where it was, and lets it be dismissed", async () => {
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

  it("reads the tasks anew when the API refuses a gesture for the state of the task", async () => {
    serve({ [PROGRESS]: REFUSED });
    board();
    await choose("Études de détail", "Rouvrir");
    await within(card("Études de détail")).findByRole("alert");
    expect(router.refresh).toHaveBeenCalledTimes(1);
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
