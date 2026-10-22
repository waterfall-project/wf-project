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
    const status = screen.getByRole("status");
    await waitFor(() => {
      expect(status).toHaveTextContent("Réception usine : colonne « Terminées ».");
    });
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
    // From here on, every change of the live region is a sentence told.
    const told: MutationRecord[] = [];
    const observer = new MutationObserver((records) => {
      told.push(...records);
    });
    observer.observe(status, { childList: true, characterData: true, subtree: true });
    await choose("Réception usine", "Rouvrir");
    await waitFor(() => {
      expect(told.length).toBeGreaterThan(0);
    });
    observer.disconnect();
    expect(status).toHaveTextContent("Réception usine : colonne « Terminées ».");
  });

  it("marks the card moved as being updated while the tasks are read anew, and as not up to date, with a way to read them again, when that reading is over without", async () => {
    serve({ [PROGRESS]: "task_started" });
    const waits = holdReadings();
    const { again } = board();
    await choose("Montage des armoires sur site", "Démarrer");
    await userEvent.click(
      within(card("Montage des armoires sur site")).getByRole("button", { name: "Démarrer" }),
    );
    const moved = () => within(card("Montage des armoires sur site"));
    expect(await moved().findByText("Mise à jour…")).toBeInTheDocument();
    expect(moved().queryByRole("button", { name: "Réessayer" })).toBeNull();
    // No other card is marked.
    expect(screen.getAllByText("Mise à jour…")).toHaveLength(1);
    // The reading is over, and the tasks it brought do not hold the answer.
    waits[0]?.release();
    const retry = await moved().findByRole("button", { name: "Réessayer" });
    expect(moved().getByText(/Non à jour/)).toBeInTheDocument();
    expect(moved().queryByText("Mise à jour…")).toBeNull();
    expect(router.refresh).toHaveBeenCalledTimes(1);
    // Read again, the card is being updated anew.
    // The reading is started in the act, which waits for what it suspends on.
    await act(async () => {
      retry.click();
      await Promise.resolve();
    });
    expect(await moved().findByText("Mise à jour…")).toBeInTheDocument();
    expect(router.refresh).toHaveBeenCalledTimes(2);
    // The tasks read hold the answer: the card is no more marked.
    const read = columnsOfExample("startable_tasks");
    const [task] = read.not_started.filter(
      (each) => each.label === "Montage des armoires sur site",
    );
    if (task === undefined) {
      throw new Error("no task in the example");
    }
    waits[1]?.release();
    await moved().findByRole("button", { name: "Réessayer" });
    again({
      ...read,
      not_started: read.not_started.filter((each) => each !== task),
      started: [...read.started, { ...task, state: "started", lock_version: 99 }],
    });
    await waitFor(() => {
      expect(moved().queryByText(/Non à jour/)).toBeNull();
    });
    expect(moved().queryByText("Mise à jour…")).toBeNull();
    expect(labels("Démarrées")).toContain("Montage des armoires sur site");
  });
});
