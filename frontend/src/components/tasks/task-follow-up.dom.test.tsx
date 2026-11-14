// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { BackgroundTask } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { tasksButton, tasksRegion } from "@/test/task-panel";

import { POLL_INTERVAL } from "./task-entry";
import { TaskPanel, TasksButton, TaskTracker, useTrackTask } from "./task-tracker";

// The follow-up of a task until it has ended, and the screen read anew at its end (#3103); the rest
// of the tracker is in `task-tracker.dom.test.tsx`. The server of Next, as far as the tracker needs
// it, and its router, whose refresh reads the screen anew.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => `/projects/${PROJECT}/revisions`,
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const TASK = "GET /tasks/{task_id}";
// The address of the document, which a test that moves to another screen gives back.
const SHOWN = window.location.href;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** A task of the contract, by the name of its example. */
function task(name: string): BackgroundTask {
  return example(name) as BackgroundTask;
}

/** A screen that hands a task over to the tracker when its button is pressed. */
function Starting({ given }: { readonly given: BackgroundTask }) {
  const track = useTrackTask();
  return (
    <button
      type="button"
      onClick={() => {
        track(given);
      }}
    >
      Lancer
    </button>
  );
}

/** Render the shell, as far as the tracker goes, with a screen that starts a task, and start it. */
async function started(given: BackgroundTask) {
  render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <header>
          <TasksButton />
        </header>
        <TaskPanel />
        <Starting given={given} />
      </TaskTracker>
    </NextIntlClientProvider>,
  );
  await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
}

/** Let the time of one read go by, and the read be answered. */
async function tick(times = 1) {
  for (let turn = 0; turn < times; turn += 1) {
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
  }
}

/** The tasks the panel lists. */
function entries() {
  return within(tasksRegion()).getByRole("list");
}

/** The ends the log reads out, each in its sentences. */
function ends(): (string | null)[][] {
  return [...screen.getByRole("log").children].map((end) =>
    [...end.children].map((sentence) => sentence.textContent),
  );
}

/** The paths the tracker asked the API. */
function reads(client: FakeClient): string[] {
  return client.calls.filter((call) => call.route === TASK).map((call) => call.path);
}

beforeEach(() => {
  router.refresh.mockClear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
});

afterEach(() => {
  window.history.replaceState(null, "", SHOWN);
  vi.useRealTimers();
});

describe("the follow-up of a task, and the screen read anew at its end", () => {
  it("offers to reload the screen once a task has succeeded, and closes the panel on the screen read anew", async () => {
    serve({ [TASK]: "task_succeeded" });
    await started(task("task_mark_queued"));
    await tick();
    const reload = within(entries()).getByRole("button", { name: "Recharger l’écran" });
    // The screen it was started from, read anew by itself once (#3103), and on demand.
    await tick(2);
    expect(router.refresh).toHaveBeenCalledOnce();
    await userEvent.click(reload);
    expect(router.refresh).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(tasksButton()).toHaveFocus();
  });

  it("keeps reading a task found where it stood, until it has ended: the follow-up stopped of 2026-11-13 (#3103) [WF-IHM-0080-A]", async () => {
    // An export read at +2 s and +5 s, the same both times, then never again, though it succeeded
    // at +8 s. A read that finds the task where it stood leaves the entry as it was (#180), and the
    // next read waited for a new entry.
    const client = serve({
      [TASK]: ["task_running", "task_running", "task_running", "task_succeeded"],
    });
    await started(task("task_mark_queued"));
    await tick(3);
    expect(within(entries()).getByText("En cours")).toBeVisible();
    expect(reads(client)).toHaveLength(3);
    await tick();
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision."]]);
    await tick(3);
    expect(reads(client)).toHaveLength(4);
  });

  it("keeps reading a task read as it was handed over (#3103) [WF-IHM-0080-A]", async () => {
    // Handed over running and read running: the first export of 2026-11-13, read once, never again.
    const client = serve({ [TASK]: ["task_running", "task_succeeded"] });
    await started(task("task_running"));
    await tick();
    expect(reads(client)).toHaveLength(1);
    await tick();
    expect(reads(client)).toHaveLength(2);
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision."]]);
  });

  it("reads anew by itself the screen of the project a task started from, at its end, a failure too (#3103) [WF-IHM-0080-A]", async () => {
    serve({ [TASK]: ["task_running", "task_failed"] });
    window.history.replaceState(null, "", `/projects/${PROJECT}/revisions`);
    await started(task("task_mark_queued"));
    // Gone to another screen of the same project: read anew at the end of the task, once.
    window.history.replaceState(null, "", `/projects/${PROJECT}/exchanges?view=imports`);
    await tick();
    expect(router.refresh).not.toHaveBeenCalled();
    await tick();
    expect(within(entries()).getByText("Échouée")).toBeVisible();
    expect(router.refresh).toHaveBeenCalledOnce();
    await tick(2);
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("reads nothing anew on the screen of another project [WF-IHM-0080-A]", async () => {
    serve({ [TASK]: ["task_running", "task_succeeded"] });
    window.history.replaceState(null, "", `/projects/${PROJECT}/revisions`);
    await started(task("task_mark_queued"));
    window.history.replaceState(
      null,
      "",
      "/projects/01926f3a-7c00-7000-8000-000000000002/revisions",
    );
    await tick(2);
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision."]]);
    expect(router.refresh).not.toHaveBeenCalled();
  });
});
