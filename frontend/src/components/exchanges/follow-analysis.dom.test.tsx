// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { type ReactNode, useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker, useTrackTask } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, fakeClient } from "@/test/fixtures";

import { FileDrop } from "./file-drop";
import { ImportReport } from "./import-report";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => `/projects/${PROJECT}`,
  useSearchParams: () => new URLSearchParams(),
}));

type Import = components["schemas"]["ImportDetail"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const START = `/projects/${PROJECT}`;
const RULE = "PUT /projects/{project_id}/imports/{import_id}/duration-rule";
const UPLOAD = "POST /file-uploads";
const OPEN = "POST /projects/{project_id}/imports";
const TASK = "GET /tasks/{task_id}";

/** A screen within the shell that follows the tasks, which outlives the screens. */
function shell(screenOf: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>{screenOf}</main>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** A task the shell follows, as it restores those of the session: the screen then reads it. */
function Followed({ task }: { readonly task?: Import["task"] | undefined }) {
  const track = useTrackTask();
  useEffect(() => {
    if (task) {
      track(task, { subject: "planning.xml" });
    }
  }, [task, track]);
  return null;
}

const report = (entry: Import) => <ImportReport projectId={PROJECT} entry={entry} start={START} />;

/** Let the poll of the task run until it has ended. */
async function pollToItsEnd() {
  for (let turn = 0; turn < 3; turn += 1) {
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
  }
}

function serve(answers: FakeAnswers): void {
  server.client = fakeClient(answers);
}

beforeEach(() => {
  window.history.replaceState(null, "", START);
  router.push.mockClear();
  router.refresh.mockClear();
  window.sessionStorage.clear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the end of the analysis of an import, followed from the import the screen reads", () => {
  it("reads the screen anew at the end of a new analysis, the screen left and come back to meanwhile [WF-INTF-0080-A]", async () => {
    serve({
      [RULE]: { example: "import_duration_rule_set", status: 202 },
      [TASK]: "task_import_succeeded",
    });
    const gapped = example("import_planning_calendar_gap") as Import;
    const analysing = example("import_duration_rule_set") as Import;
    const view = render(shell(report(gapped)));
    await userEvent.click(screen.getByRole("radio", { name: /^Garder les dates/ }));
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    // Another screen, then the import again, read analysing, as the page reads it.
    view.rerender(shell(<p>Ailleurs</p>));
    view.rerender(shell(report(analysing)));
    await pollToItsEnd();
    expect(router.refresh).toHaveBeenCalledTimes(2);
  });

  it("reads the screen anew at the end of an analysis the shell took back and the screen finds running, as after a reload [WF-INTF-0080-A]", async () => {
    serve({
      [RULE]: { example: "import_duration_rule_set", status: 202 },
      [TASK]: "task_import_succeeded",
    });
    const gapped = example("import_planning_calendar_gap") as Import;
    const view = render(shell(report(gapped)));
    await userEvent.click(screen.getByRole("radio", { name: /^Garder les dates/ }));
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    view.unmount();
    // A cold mount: the shell restores the task, the screen is read with the import analysing.
    render(shell(report(example("import_duration_rule_set") as Import)));
    await pollToItsEnd();
    expect(router.refresh).toHaveBeenCalledTimes(2);
  });

  it("reads the screen anew at the end of an analysis that failed, the import read analysing as after a reload [WF-INTF-0080-A]", async () => {
    serve({
      [RULE]: { example: "import_duration_rule_set", status: 202 },
      [TASK]: "task_import_analysis_failed",
    });
    const gapped = example("import_planning_calendar_gap") as Import;
    const view = render(shell(report(gapped)));
    await userEvent.click(screen.getByRole("radio", { name: /^Garder les dates/ }));
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    view.unmount();
    render(shell(report(example("import_duration_rule_set") as Import)));
    await pollToItsEnd();
    expect(router.refresh).toHaveBeenCalledTimes(2);
  });

  it("follows the task the screen reads in place of the one a 202 handed over, and reads the screen anew once for each [WF-INTF-0080-A]", async () => {
    serve({
      [RULE]: { example: "import_duration_rule_set", status: 202 },
      [TASK]: "task_import_succeeded",
    });
    const gapped = example("import_planning_calendar_gap") as Import;
    const analysing = example("import_duration_rule_set") as Import;
    const other = {
      ...analysing,
      task: { ...analysing.task, task_id: "01926f3a-7c00-7000-8000-000000000927" },
    } as Import;
    const read = (entry: Import, task?: Import["task"]) => (
      <>
        <Followed task={task} />
        {report(entry)}
      </>
    );
    const view = render(shell(read(gapped)));
    await userEvent.click(screen.getByRole("radio", { name: /^Garder les dates/ }));
    await pollToItsEnd();
    // The first analysis has ended and was read: one for the answer, one for its end.
    expect(router.refresh).toHaveBeenCalledTimes(2);
    // A 409 reads the screen anew: the import analysing under another task, which ends in turn.
    // The tree keeps its shape, so that the screen is not mounted anew: its state is kept.
    view.rerender(shell(read(other, other.task)));
    await pollToItsEnd();
    expect(router.refresh).toHaveBeenCalledTimes(3);
    // The import is analysed: the first task, read already, is not followed again.
    view.rerender(shell(read(gapped)));
    await pollToItsEnd();
    expect(router.refresh).toHaveBeenCalledTimes(3);
  });

  it("reads the screen anew at the end of the analysis of an import just opened, the zone gone meanwhile [WF-ARC-0090-A]", async () => {
    serve({
      [UPLOAD]: { example: "file_upload", status: 201 },
      [OPEN]: { example: "import_analysing", status: 202 },
      [TASK]: "task_import_succeeded",
    });
    const view = render(shell(<FileDrop projectId={PROJECT} start={START} />));
    fireEvent.drop(screen.getByRole("group"), {
      dataTransfer: { files: [new File(["<Project/>"], "planning.xml", { type: "text/xml" })] },
    });
    await waitFor(() => {
      expect(router.push).toHaveBeenCalled();
    });
    // The report is shown, the import read analysing: the zone is no longer there.
    view.rerender(shell(report(example("import_analysing") as Import)));
    expect(within(screen.getByRole("main")).queryByRole("group", { name: /dépôt/ })).toBeNull();
    await pollToItsEnd();
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });
});
