// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the tracker writes in the storage of the tab for an account, and wipes when the session of the
 * follow-up is found ended (#1180): the guard of its write, proved by a task followed after the wipe.
 */
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { BackgroundTask } from "@/api/problem";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { closeTasks, tasksRegion } from "@/test/task-panel";

import { OWNER_KEY } from "./session-end";
import { STORAGE_KEY } from "./storage";
import { POLL_INTERVAL } from "./task-entry";
import { TaskPanel, TasksButton, TaskTracker, useTrackTask } from "./task-tracker";

// The server of Next, as far as the tracker needs it: the fake back behind serverClient.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ refresh: vi.fn() }),
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions",
  useSearchParams: () => new URLSearchParams(),
}));

const TASK = "GET /tasks/{task_id}";

/** A task of the contract, by the name of its example. */
function task(name: string): BackgroundTask {
  return example(name) as BackgroundTask;
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** A screen that hands a task over to the tracker when the user presses its button. */
function Starting({
  given,
  label = "Lancer",
}: {
  readonly given: BackgroundTask;
  readonly label?: string;
}) {
  const track = useTrackTask();
  return (
    <main>
      <button
        type="button"
        onClick={() => {
          track(given);
        }}
      >
        {label}
      </button>
    </main>
  );
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

const ACCOUNT = "00000000-0000-4000-8000-0000000000a1";

/** The tracker of the shell for the account, around a page. */
function identified(page: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker accountId={ACCOUNT}>
        <TasksButton />
        <TaskPanel />
        {page}
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
  forgetMessages();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the storage of the tab kept by the tracker for an account", () => {
  it("wipes a task interrupted for want of a session, even for the account that reconnects (#1180) [WF-SEC-0020-A]", async () => {
    serve({ [TASK]: { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    const view = render(
      identified(
        <>
          <Starting given={task("task_mark_queued")} />
          <Starting given={task("task_import_queued")} label="Lancer un import" />
        </>,
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    await tick();
    expect(within(entries()).getByRole("link", { name: "Se connecter" })).toBeVisible();
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(window.sessionStorage.getItem(OWNER_KEY)).toBeNull();
    // A task followed after the stores were wiped is not written to them again: the tracker has no
    // owner to write for until the next load.
    closeTasks();
    await userEvent.click(screen.getByRole("button", { name: "Lancer un import" }));
    await tick();
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    view.unmount(); // the same account signs in again, the tab reloads: no task is followed on
    const client = serve({ [TASK]: "task_succeeded" });
    render(identified(null));
    await tick();
    expect(client.calls.filter((call) => call.route === TASK)).toEqual([]);
    expect(within(tasksRegion()).queryAllByRole("listitem")).toHaveLength(0);
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("writes the tasks followed on the first mount of an account, which keeps the stores as its own [WF-SEC-0020-A]", async () => {
    serve({ [TASK]: "task_running" });
    render(identified(<Starting given={task("task_mark_queued")} />));
    expect(window.sessionStorage.getItem(OWNER_KEY)).toBe(ACCOUNT);
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    await tick();
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toContain(task("task_mark_queued").task_id);
  });
});
