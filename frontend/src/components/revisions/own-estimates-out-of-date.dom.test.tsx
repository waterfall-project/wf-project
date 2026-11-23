// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { BackgroundTask } from "@/api/problem";
import { forgetMessages } from "@/components/notices/message-history";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker, useTrackTask } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";

import { OwnEstimatesOutOfDate } from "./own-estimates-out-of-date";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r",
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

/** A marking handed to the tracker, whose failure the screen names the risks of. */
function Marking() {
  const track = useTrackTask();
  const [started, setStarted] = useState<string>();
  return (
    <>
      <button
        type="button"
        onClick={() => {
          const task = example("task_mark_queued") as BackgroundTask;
          track(task, { subject: "v1" });
          setStarted(task.task_id);
        }}
      >
        Marquer
      </button>
      <OwnEstimatesOutOfDate taskId={started} projectId={PROJECT} revisionId={REVISION} />
    </>
  );
}

function marking() {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <Marking />
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  sessionStorage.clear();
  forgetMessages();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("le marquage dont la tâche échoue pour des devis propres [US-3140] [WF-RIS-0070-A]", () => {
  it("nomme les risques et mène au détail de chacun, où se lit le compte rendu de sa mise à jour", async () => {
    server.client = fakeClient({ "GET /tasks/{task_id}": ["task_mark_own_estimates_failed"] });
    render(marking());
    await act(async () => {
      screen.getByRole("button", { name: "Marquer" }).click();
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL);
    });
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    const named = await screen.findByRole("alert");
    expect(within(named).getByText(/Risque de reprise du câblage/)).toBeVisible();
    expect(named).toHaveTextContent(/rien n’a été écrit/);
    const link = within(named).getByRole("link", {
      name: "Lire le compte rendu de « Risque de reprise du câblage »",
    });
    expect(link).toHaveAttribute(
      "href",
      `/projects/${PROJECT}/revisions/${REVISION}/risks?risk=01926f3a-7c00-7000-8000-000000000751`,
    );
  });

  it("ne dit rien d'une tâche qui échoue pour un autre motif", async () => {
    server.client = fakeClient({ "GET /tasks/{task_id}": ["task_failed"] });
    render(marking());
    await act(async () => {
      screen.getByRole("button", { name: "Marquer" }).click();
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL);
    });
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    expect(screen.queryByRole("link", { name: /Lire le compte rendu/ })).toBeNull();
  });
});
