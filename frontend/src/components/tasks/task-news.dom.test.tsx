// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { BackgroundTask } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";
import { tasksButton } from "@/test/task-panel";

import { POLL_INTERVAL } from "./task-entry";
import { EndCards } from "./end-cards";
import { TaskPanel, TasksButton, TaskTracker, useTrackTask } from "./task-tracker";

// No requirement covers the closing of this line: it is the author's decision (#1179), so the tests
// below cite no identifier of requirement.
// The line under the bar that says the last task handed over, or whose follow-up was interrupted,
// and its button of closing, decided by the author on 2026-10-20 (#1179); a success or a failure is
// said by its card alone (#3292, the author on 2026-11-14); the rest of the tracker is in
// `task-tracker.dom.test.tsx`. The server of Next, as far as the tracker needs it.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ refresh: vi.fn() }),
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions",
  useSearchParams: () => new URLSearchParams(),
}));

/** A screen that hands a task of the contract over to the tracker when its button is pressed. */
function Starting({ name }: { readonly name: string }) {
  const track = useTrackTask();
  return (
    <button
      type="button"
      onClick={() => {
        track(example(name) as BackgroundTask);
      }}
    >
      Lancer
    </button>
  );
}

/** The shell, as far as the line goes: the tracker, the button of the bar, its panel, the page. */
function shell(name: string) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker signedIn={false}>
        <header>
          <TasksButton />
        </header>
        <TaskPanel />
        <Starting name={name} />
        <EndCards />
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

describe("the line under the bar", () => {
  it("closes by its button, from the keyboard, the task followed still and the focus on the button of the bar", async () => {
    server.client = fakeClient({ "GET /tasks/{task_id}": "task_running" });
    render(shell("task_mark_queued"));
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    const line = "Tâche lancée : Marquage d’une révision.";
    expect(screen.getByText(line)).toBeVisible();
    screen.getByRole("button", { name: "Fermer la ligne de la tâche" }).focus();
    await userEvent.keyboard("{Enter}");
    expect(screen.queryByText(line)).toBeNull();
    expect(tasksButton()).toHaveFocus();
    expect(tasksButton()).toHaveAccessibleName("Tâches et messages\u00A0: 1 tâche suivie");
  });

  it("is replaced by the next task, once closed as before", async () => {
    server.client = fakeClient({ "GET /tasks/{task_id}": "task_running" });
    const view = render(shell("task_mark_queued"));
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    await userEvent.click(screen.getByRole("button", { name: "Fermer la ligne de la tâche" }));
    expect(screen.queryByText(/^Tâche lancée/)).toBeNull();
    view.rerender(shell("task_import_queued"));
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    expect(screen.getByText(/^Tâche lancée : Application d’un import/)).toBeVisible();
  });

  describe("once the task has ended", () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      window.sessionStorage.clear();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it.each([
      ["task_succeeded", "Tâche terminée : Marquage d’une révision."],
      ["task_failed", "Tâche échouée : Marquage d’une révision."],
    ] as const)(
      "says nothing of an end its card says, %s, and closes the line of the task handed over (#3292)",
      async (answer, sentence) => {
        server.client = fakeClient({ "GET /tasks/{task_id}": answer });
        render(shell("task_mark_queued"));
        await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
        expect(screen.getByText("Tâche lancée : Marquage d’une révision.")).toBeVisible();
        await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
        // The card says it, and stays; the line is gone, its button with it.
        const cards = screen.getByRole("region", { name: "Aboutissements des tâches" });
        expect(within(cards).getByRole("group")).toHaveTextContent(sentence);
        expect(screen.queryByRole("button", { name: "Fermer la ligne de la tâche" })).toBeNull();
        expect(screen.queryByText(/^Tâche lancée/)).toBeNull();
        // The task is followed still, in the panel.
        expect(tasksButton()).toHaveAccessibleName(/1 tâche suivie/);
      },
    );

    it("says a follow-up interrupted, which has no card, and closes by its button, the focus on the button of the bar", async () => {
      server.client = fakeClient({
        "GET /tasks/{task_id}": { problem: { code: "NOT_FOUND", status: 404 } },
      });
      render(shell("task_mark_queued"));
      await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
      await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
      const close = screen.getByRole("button", { name: "Fermer la ligne de la tâche" });
      expect(close.parentElement).toHaveTextContent("Suivi interrompu : Marquage d’une révision.");
      expect(screen.queryByRole("group")).toBeNull();
      close.focus();
      await userEvent.keyboard("{Enter}");
      expect(screen.queryByRole("button", { name: "Fermer la ligne de la tâche" })).toBeNull();
      expect(tasksButton()).toHaveFocus();
    });
  });
});
