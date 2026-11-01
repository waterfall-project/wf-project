// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { fakeClient } from "@/test/fixtures";
import { tasksRegion } from "@/test/task-panel";

import { STORAGE_KEY } from "./storage";
import { POLL_INTERVAL } from "./task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "./task-tracker";

// The tasks found again after a reload; the rest of the tracker is in `task-tracker.dom.test.tsx`.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ refresh: vi.fn() }),
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions",
  useSearchParams: () => new URLSearchParams(),
}));

const MARKING = "01926f3a-7c00-7000-8000-000000000931";

/** The shell, as far as the panel of the tasks goes. */
function shell() {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker signedIn={false}>
        <header>
          <TasksButton />
        </header>
        <TaskPanel />
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** What the progress of the task says next to its bar. */
function progressText(): string | null | undefined {
  return within(tasksRegion()).getByRole("progressbar").nextElementSibling?.textContent;
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("a task found again after a reload", () => {
  it("shows no progress until a read says it, then shows it and keeps it [WF-IHM-0080-A]", async () => {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { key: MARKING, task_id: MARKING, kind: "revision_mark", status: "running", subject: "V2" },
      ]),
    );
    server.client = fakeClient({ "GET /tasks/{task_id}": ["task_running", "task_running"] });
    render(shell());

    const bar = within(tasksRegion()).getByRole("progressbar");
    expect(bar).not.toHaveAttribute("aria-valuenow");
    expect(progressText()).toBeUndefined();
    expect(within(tasksRegion()).queryByText(/\d\s*%/)).toBeNull();

    for (let read = 0; read < 2; read += 1) {
      await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
      expect(bar).toHaveAttribute("aria-valuenow", "40");
      expect(progressText()).toBe("40 %");
    }
  });
});
