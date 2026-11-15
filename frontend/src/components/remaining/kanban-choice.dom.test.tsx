// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { Kanban } from "./kanban";
import { columnsOf, type KanbanColumns, type StartableTasks } from "./kanban-cards";

// The choice of a card and the date asked on it, split from `kanban.dom.test.tsx`: the cards are
// those the contract lists (`startable_tasks`), and the fake back keeps nothing — what a gesture
// sends is read in the calls it records.
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
      <Kanban
        columns={shown}
        structure={STRUCTURE}
        remaining={REMAINING}
        filters={{ text: "", ready: false }}
      />
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
  vi.setSystemTime(new Date(Date.UTC(2026, 5, 3, 10, 0, 0)));
});

afterEach(() => {
  vi.useRealTimers();
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
