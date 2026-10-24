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
import { tasksButton, tasksRegion } from "@/test/task-panel";

import { POLL_INTERVAL } from "./task-entry";
import { TaskPanel, TasksButton, TaskTracker, useTrackTask } from "./task-tracker";

// No requirement covers the closing of this line: it is the author's decision (#1179), so the tests
// below cite no identifier of requirement.
// The line under the bar that says the last task handed over or ended, and its button of closing,
// decided by the author on 2026-10-20 (#1179); the rest of the tracker is in
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
    expect(tasksButton()).toHaveAccessibleName("Tâches et messages : 1 tâche suivie");
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

    it("closes by its button, from the keyboard, the task followed still, succeeded, and the focus on the button of the bar", async () => {
      server.client = fakeClient({ "GET /tasks/{task_id}": "task_succeeded" });
      render(shell("task_mark_queued"));
      await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
      await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
      const close = screen.getByRole("button", { name: "Fermer la ligne de la tâche" });
      expect(close.parentElement).toHaveTextContent("Tâche terminée : Marquage d’une révision.");
      screen.getByRole("button", { name: "Fermer la ligne de la tâche" }).focus();
      await userEvent.keyboard("{Enter}");
      expect(screen.queryByRole("button", { name: "Fermer la ligne de la tâche" })).toBeNull();
      expect(tasksButton()).toHaveFocus();
      expect(within(tasksRegion()).getByText("Réussie")).toBeVisible();
    });
  });
});
