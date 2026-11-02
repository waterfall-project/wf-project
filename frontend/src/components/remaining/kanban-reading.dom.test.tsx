// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { use, useLayoutEffect, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient, held } from "@/test/fixtures";

import { Kanban } from "./kanban";
import { columnsOf, type KanbanColumns, type StartableTasks } from "./kanban-cards";

// What the Kanban says once a gesture is answered: the sentence announced, and the card moved while
// the tasks are read anew. The fake back answers the example whatever was sent.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ refresh: vi.fn() }));

// The reading anew a gesture is followed by, which the router starts and the test holds: the screen
// that reads suspends on it, in the transition the router is called in, as the app router does.
const reading = vi.hoisted(() => ({
  start: undefined as ((until: Promise<unknown>) => void) | undefined,
}));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
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

/** The first cards of each column of an example, enough to try every gesture, few enough to be fast. */
function columnsOfExample(name: string): KanbanColumns {
  const all = columnsOf(example(name) as StartableTasks);
  return {
    not_started: all.not_started.slice(0, 4),
    started: all.started.slice(0, 4),
    completed: all.completed.slice(0, 4),
  };
}

/** Serve the fake back. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The part of the screen that waits for the reading anew, once the router started one. */
function Reader() {
  const [until, setUntil] = useState<Promise<unknown>>();
  useLayoutEffect(() => {
    reading.start = setUntil;
  }, []);
  if (until !== undefined) {
    use(until);
  }
  return null;
}

/** Hold the reading anew of each gesture until the test releases it; the reading started so far. */
function holdReadings() {
  const waits: ReturnType<typeof held>[] = [];
  router.refresh.mockImplementation(() => {
    const wait = held();
    waits.push(wait);
    reading.start?.(wait.until);
  });
  return waits;
}

/** Render the Kanban in French, as the shell hands its texts to a screen. */
function board(columns: KanbanColumns = columnsOfExample("startable_tasks")) {
  const tree = (shown: KanbanColumns) => (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <Kanban columns={shown} structure={STRUCTURE} remaining={REMAINING} />
      <Reader />
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

/** The live region of the board, where the moves are announced: not the marks of a card. */
function announcements(): HTMLElement {
  const found = screen.getAllByRole("status").find((each) => each.classList.contains("sr-only"));
  if (found === undefined) {
    throw new Error("no live region on the board");
  }
  return found;
}

/** The columns read once a task is started, at a version past the answer of the API. */
function readStarted(...labelsStarted: string[]): KanbanColumns {
  const read = columnsOfExample("startable_tasks");
  const tasks = read.not_started.filter((each) => labelsStarted.includes(each.label));
  if (tasks.length !== labelsStarted.length) {
    throw new Error("a task is missing from the example");
  }
  return {
    ...read,
    not_started: read.not_started.filter((each) => !tasks.includes(each)),
    started: [
      ...read.started,
      ...tasks.map((each) => ({ ...each, state: "started" as const, lock_version: 99 })),
    ],
  };
}

/** Start a task through its menu and its date form. */
async function start(label: string) {
  await choose(label, "Démarrer");
  await userEvent.click(within(card(label)).getByRole("button", { name: "Démarrer" }));
}

/** Choose a card by a click, open the menu of its gestures, and make one. */
async function choose(label: string, gesture: string | RegExp) {
  const user = userEvent.setup();
  await user.click(card(label));
  await user.click(
    within(card(label)).getByRole("button", { name: `Gestes de la tâche ${label}` }),
  );
  await user.click(await screen.findByRole("menuitem", { name: gesture }));
}

beforeEach(() => {
  router.refresh.mockReset();
  reading.start = undefined;
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 5, 3, 10, 0, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the Kanban once a gesture is answered", () => {
  it("announces a card that returns to the column it was in as it announced it the first time", async () => {
    // The fake back answers the milestone completed whatever was sent: reopened, the card is
    // answered into the same column again, and the same sentence is told.
    serve({ [PROGRESS]: "milestone_completed" });
    const { again } = board();
    await choose("Réception usine", /^Terminer/);
    await userEvent.click(
      within(card("Réception usine")).getByRole("button", { name: "Terminer" }),
    );
    const status = announcements();
    await waitFor(() => {
      expect(status).toHaveTextContent("Réception usine : colonne « Terminées ».");
    });
    const first = status.firstChild;
    const read = columnsOfExample("startable_tasks");
    const [milestone] = read.not_started.filter((each) => each.label === "Réception usine");
    if (milestone === undefined) {
      throw new Error("no milestone in the example");
    }
    again({
      ...read,
      not_started: read.not_started.filter((each) => each !== milestone),
      completed: [
        ...read.completed,
        {
          ...milestone,
          state: "completed",
          lock_version: 3,
          commands: [
            {
              command: "reopen",
              is_available: true,
              missing_conditions: [],
              progress: "not_started",
            },
          ],
        },
      ],
    });
    await choose("Réception usine", "Rouvrir");
    // The same sentence, told again, is a new node of the region: that is what is announced again.
    await waitFor(() => {
      expect(status.firstChild).not.toBe(first);
    });
    expect(status).toHaveTextContent("Réception usine : colonne « Terminées ».");
  });

  it("marks the card moved as updating, then as not up to date with a way to read again [WF-IHM-0090-A]", async () => {
    serve({ [PROGRESS]: "task_started" });
    const waits = holdReadings();
    const { again } = board();
    const label = "Montage des armoires sur site";
    await start(label);
    const moved = () => within(card(label));
    expect(await moved().findByText("Mise à jour…")).toBeInTheDocument();
    // The mark is told to assistive technology.
    expect(moved().getByRole("status")).toHaveTextContent("Mise à jour…");
    expect(moved().queryByRole("button", { name: "Réessayer" })).toBeNull();
    // No other card is marked.
    expect(screen.getAllByText("Mise à jour…")).toHaveLength(1);
    // The reading is over, and the tasks it brought do not hold the answer.
    waits[0]?.release();
    const retry = await moved().findByRole("button", { name: "Réessayer" });
    expect(moved().getByRole("status")).toHaveTextContent(/Non à jour/);
    expect(moved().queryByText("Mise à jour…")).toBeNull();
    expect(router.refresh).toHaveBeenCalledTimes(1);
    // Read again, the card is being updated anew, and the focus is on it, not lost with the button.
    // Started in the act, which waits for what the reading suspends on: a click by userEvent is
    // not awaited by its act, and React refuses the suspension there.
    await act(async () => {
      retry.click();
      await Promise.resolve();
    });
    expect(await moved().findByText("Mise à jour…")).toBeInTheDocument();
    expect(router.refresh).toHaveBeenCalledTimes(2);
    expect(card(label)).toHaveFocus();
    // The tasks read hold the answer: the card is no more marked.
    waits[1]?.release();
    await moved().findByRole("button", { name: "Réessayer" });
    again(readStarted(label));
    await waitFor(() => {
      expect(moved().queryByText(/Non à jour/)).toBeNull();
    });
    expect(moved().queryByText("Mise à jour…")).toBeNull();
    expect(labels("Démarrées")).toContain(label);
  });

  it("never says a card is not up to date when the columns arrive with the end of the reading [WF-IHM-0090-A]", async () => {
    // The model of the suspended reading is tried against this test only, with no e2e journey.
    serve({ [PROGRESS]: "task_started" });
    const waits = holdReadings();
    const { again } = board();
    const label = "Montage des armoires sur site";
    await start(label);
    const moved = () => within(card(label));
    expect(await moved().findByText("Mise à jour…")).toBeInTheDocument();
    expect(screen.queryByText(/Non à jour/)).toBeNull();
    await act(async () => {
      again(readStarted(label));
      waits[0]?.release();
      await Promise.resolve();
    });
    expect(screen.queryByText(/Non à jour/)).toBeNull();
    expect(moved().queryByText("Mise à jour…")).toBeNull();
    await waitFor(() => {
      expect(labels("Démarrées")).toContain(label);
    });
    expect(screen.queryByText(/Non à jour/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Réessayer" })).toBeNull();
  });

  it("marks as not up to date the card a reading does not reach while another is reached [WF-IHM-0090-A]", async () => {
    const reached = "Montage des armoires sur site";
    const missed = "Réception usine";
    serve({ [PROGRESS]: ["task_started", "milestone_completed"] });
    const waits = holdReadings();
    const { again } = board();
    await start(reached);
    await within(card(reached)).findByText("Mise à jour…");
    // The board writes nothing while a reading is under way: the second gesture waits for its end.
    waits[0]?.release();
    await within(card(reached)).findByRole("button", { name: "Réessayer" });
    await choose(missed, /^Terminer/);
    await userEvent.click(within(card(missed)).getByRole("button", { name: "Terminer" }));
    await within(card(missed)).findByText("Mise à jour…");
    // The reading brings the first card at the version answered, and not the second.
    await act(async () => {
      again(readStarted(reached));
      waits[1]?.release();
      await Promise.resolve();
    });
    await within(card(missed)).findByRole("button", { name: "Réessayer" });
    expect(within(card(missed)).getByText(/Non à jour/)).toBeInTheDocument();
    expect(within(card(reached)).queryByText(/Non à jour/)).toBeNull();
    expect(within(card(reached)).queryByText("Mise à jour…")).toBeNull();
  });
});

describe("the gestures of a card, commands of a menu", () => {
  /** Choose a card and open the menu of its gestures, by the keyboard on its first. */
  async function menuOf(label: string) {
    const user = userEvent.setup();
    await user.click(card(label));
    await user.click(
      within(card(label)).getByRole("button", { name: `Gestes de la tâche ${label}` }),
    );
    await user.keyboard("{ArrowDown}");
    return { user, menu: screen.getByRole("menu", { name: `Gestes de la tâche ${label}` }) };
  }

  const helps = CATALOGUES.fr.commands;

  it("says, in the tooltip of each gesture of a card not started, what it does, and, unavailable, what it lacks; the remaining to commit a link to the grid on the task [WF-IHM-0140-A]", async () => {
    // #1435: the gestures of a card are commands of a menu (`MenuCommand`), each with its help.
    serve({});
    board();
    const { user, menu } = await menuOf("Montage des armoires sur site");
    expect(within(menu).getByRole("menuitem", { name: "Démarrer" })).toHaveFocus();
    expect(await screen.findByRole("tooltip")).toHaveTextContent(helps.startTask.help);
    await user.keyboard("{ArrowDown}");
    expect(await screen.findByRole("tooltip", { name: helps.completeTask.help })).toBeVisible();
    // Unavailable, it is described by the conditions it lacks, said under its name.
    expect(within(menu).getByRole("menuitem", { name: /^Terminer/ })).toHaveAccessibleDescription(
      /^Conditions non remplies/,
    );
    await user.keyboard("{ArrowDown}");
    expect(await screen.findByRole("tooltip", { name: helps.enterRemaining.help })).toBeVisible();
    const entry = within(menu).getByRole("menuitem", { name: "Saisir le reste à engager" });
    expect(entry.tagName).toBe("A");
    expect(entry).toHaveAttribute(
      "href",
      `${REMAINING}?search=Montage+des+armoires+sur+site&progress=not_started%2Cstarted`,
    );
  });

  it("says, in the tooltip of the reopening of a card completed, what it does [WF-IHM-0140-A]", async () => {
    serve({});
    board();
    const { menu } = await menuOf("Études de détail");
    expect(within(menu).getByRole("menuitem", { name: "Rouvrir" })).toHaveFocus();
    expect(await screen.findByRole("tooltip")).toHaveTextContent(helps.reopenTask.help);
  });
});
