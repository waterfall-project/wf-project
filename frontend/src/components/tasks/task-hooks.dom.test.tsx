// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { BackgroundTask } from "@/api/problem";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";
import { tasksRegion } from "@/test/task-panel";

import { POLL_INTERVAL } from "./task-entry";
import {
  TaskPanel,
  TasksButton,
  TaskTracker,
  useTrackTask,
  useWhenTaskFails,
  useWhenTaskSucceeds,
} from "./task-tracker";
import type { Launch } from "./tracking";

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

/** A screen that starts a task, and waits for the way it ends with the hooks of the tracker. */
function Waiting({
  given,
  onSuccess,
  onFailure,
  launch,
}: {
  readonly given: BackgroundTask;
  readonly launch?: Launch;
  readonly onSuccess: () => void;
  readonly onFailure: () => void;
}) {
  const track = useTrackTask();
  useWhenTaskSucceeds(given.task_id, onSuccess);
  useWhenTaskFails(given.task_id, onFailure);
  return (
    <button
      type="button"
      onClick={() => {
        track(given, launch);
      }}
    >
      Lancer
    </button>
  );
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
  forgetMessages();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("what waits for the end of a task", () => {
  it.each([
    ["task_failed", 0, 1],
    ["task_succeeded", 1, 0],
  ] as const)(
    "runs, once, only the hook of the way the task ended: %s [WF-IHM-0080-A]",
    async (ended, successes, failures) => {
      server.client = fakeClient({ [TASK]: ended });
      const onSuccess = vi.fn();
      const onFailure = vi.fn();
      render(
        <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
          <TaskTracker signedIn={false} running={undefined}>
            <TaskPanel />
            <Waiting
              given={example("task_mark_queued") as BackgroundTask}
              onSuccess={onSuccess}
              onFailure={onFailure}
            />
          </TaskTracker>
        </NextIntlClientProvider>,
      );
      await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
      for (let turn = 0; turn < 3; turn += 1) {
        await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
      }
      expect(onSuccess).toHaveBeenCalledTimes(successes);
      expect(onFailure).toHaveBeenCalledTimes(failures);
    },
  );

  it("runs the hook of the success for the task named when its relaunch succeeds, once, and never that of the failure after it [WF-IHM-0080-A]", async () => {
    // The task fails (…955), the relaunch (…959) is handed over by the command and read succeeded.
    server.client = fakeClient({
      [TASK]: ["task_exit_mark_failed", "task_exit_mark_relaunched_succeeded"],
    });
    const onSuccess = vi.fn();
    const onFailure = vi.fn();
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <TaskTracker signedIn={false} running={undefined}>
          <TasksButton />
          <TaskPanel />
          <Waiting
            given={example("task_exit_mark_queued") as BackgroundTask}
            launch={{
              command: () =>
                Promise.resolve({
                  kind: "done",
                  data: example("task_exit_mark_relaunched") as BackgroundTask,
                }),
            }}
            onSuccess={onSuccess}
            onFailure={onFailure}
          />
        </TaskTracker>
      </NextIntlClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    expect(onFailure).toHaveBeenCalledTimes(1);
    expect(onSuccess).not.toHaveBeenCalled();

    await userEvent.click(within(tasksRegion()).getByRole("button", { name: /^Relancer/ }));
    for (let turn = 0; turn < 3; turn += 1) {
      await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    }
    expect(onSuccess).toHaveBeenCalledTimes(1);
  });
});
