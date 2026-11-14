// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, fakeClient, type Problem } from "@/test/fixtures";
import { tasksRegion } from "@/test/task-panel";

import { ImportReport } from "./import-report";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => `/projects/${PROJECT}/revisions/${REVISION}/exchanges`,
  useSearchParams: () => new URLSearchParams(),
}));

type Import = components["schemas"]["ImportDetail"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const GAP_IMPORT = "01926f3a-7c00-7000-8000-000000000a1d";
const START = `/projects/${PROJECT}/revisions/${REVISION}/exchanges?as_of=2026-05-31`;
const RULE = "PUT /projects/{project_id}/imports/{import_id}/duration-rule";
const TASK = "GET /tasks/{task_id}";
const ABANDON = "DELETE /projects/{project_id}/imports/{import_id}";

/** The report of an import within the shell that follows the tasks. */
function shell(entry: Import) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>
          <ImportReport projectId={PROJECT} entry={entry} start={START} />
        </main>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** Render the report of an import within the shell that follows the tasks. */
function open(entry: Import, answers: FakeAnswers = {}) {
  const client = fakeClient(answers);
  server.client = client;
  const { rerender } = render(shell(entry));
  return Object.assign(client, {
    rerender: (next: Import) => {
      rerender(shell(next));
    },
  });
}

const gapped = () => example("import_planning_calendar_gap") as Import;
const KEEP_DURATIONS = () => screen.getByRole("radio", { name: /^Garder les durées/ });
const KEEP_DATES = () => screen.getByRole("radio", { name: /^Garder les dates/ });

beforeEach(() => {
  window.history.replaceState(null, "", `${START}&import=${GAP_IMPORT}`);
  router.push.mockClear();
  router.refresh.mockClear();
  window.sessionStorage.clear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the report of an import in calendar gap", () => {
  it("says the days of the file and of the installation, names each task on another calendar, and says the calendar of the file ignored [WF-INTF-0080-A] [WF-INTF-0040-A]", () => {
    open(gapped());
    expect(screen.getByText(/diffèrent de celles de l’installation/)).toBeVisible();
    const days = screen.getByRole("table", {
      name: "Heures par jour du fichier et de l’installation",
    });
    const monday = within(days)
      .getAllByRole("row")
      .map((row) => row.textContent)
      .find((text) => text.startsWith("Lundi"));
    // The working times of the file, and the hours per day on either side.
    expect(monday).toBe("Lundi08:00–12:00 et 13:00–16:0078");
    const tasks = screen.getByRole("table", {
      name: "Tâches dont le calendrier propre diffère de leur calendrier Waterfall",
    });
    expect(within(tasks).getAllByRole("row")).toHaveLength(2);
    expect(tasks).toHaveTextContent("FabricationAtelier");
    expect(tasks).not.toHaveTextContent("Études");
    expect(tasks).not.toHaveTextContent("Recette");
    expect(screen.getByText(/Le calendrier du fichier est ignoré/)).toBeVisible();
  });

  it("offers the choice with « Garder les durées » by default, before the application [WF-INTF-0080-A] [WF-PLA-0160-A]", () => {
    open(gapped());
    expect(KEEP_DURATIONS()).toBeChecked();
    expect(KEEP_DATES()).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Appliquer l’import" })).toBeVisible();
  });

  it("offers no choice for a report without a calendar gap, a file Waterfall exported [WF-PLA-0160-A]", () => {
    open(example("import_analysed") as Import);
    expect(screen.queryByRole("radio")).toBeNull();
    expect(screen.queryByText(/Écart de calendrier/)).toBeNull();
  });

  it("analyses again under the other rule: the task is followed and the screen read anew at once, then at its end [WF-INTF-0080-A]", async () => {
    const client = open(gapped(), {
      [RULE]: { example: "import_duration_rule_set", status: 202 },
      [TASK]: "task_import_succeeded",
    });
    await userEvent.click(KEEP_DATES());
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    expect(client.calls[0]?.route).toBe(RULE);
    expect(client.calls[0]?.body).toEqual({ duration_rule: "keep_dates" });
    expect(client.calls[0]?.path).toBe(`/projects/${PROJECT}/imports/${GAP_IMPORT}/duration-rule`);
    expect(within(tasksRegion()).getByText(/Analyse d’un import/)).toBeVisible();
    for (let turn = 0; turn < 3; turn += 1) {
      await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    }
    expect(router.refresh).toHaveBeenCalledTimes(2);
  });

  it("reads the screen again too when the new analysis fails [WF-INTF-0080-A]", async () => {
    open(gapped(), {
      [RULE]: { example: "import_duration_rule_set", status: 202 },
      [TASK]: "task_import_analysis_failed",
    });
    await userEvent.click(KEEP_DATES());
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    for (let turn = 0; turn < 3; turn += 1) {
      await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    }
    expect(router.refresh).toHaveBeenCalledTimes(2);
  });

  it("reads the screen again when the API answers that the rule is already the report's (200), which may be stale [WF-INTF-0080-A]", async () => {
    const client = open(gapped(), {
      [RULE]: { example: "import_planning_other_constants", status: 200 },
    });
    await userEvent.click(KEEP_DATES());
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    expect(client.calls).toHaveLength(1);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("reads the import again and tells the refusal when it awaits no decision any more, or has no gap [WF-INTF-0080-A]", async () => {
    open(gapped(), {
      [RULE]: { problem: example("import_duration_rule_applied") as Problem & { status: 409 } },
    });
    await userEvent.click(KEEP_DATES());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Condition non remplie : import en attente de décision",
    );
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("keeps the refusal told when the screen read anew drops the choice [WF-INTF-0080-A]", async () => {
    const entry = gapped();
    const client = open(entry, {
      [RULE]: { problem: example("import_duration_rule_applied") as Problem & { status: 409 } },
    });
    await userEvent.click(KEEP_DATES());
    expect(await screen.findByRole("alert")).toBeVisible();
    for (const next of [
      { ...entry, status: "applied" as const },
      { ...entry, report: (example("import_analysed") as Import).report },
    ]) {
      client.rerender(next);
      expect(screen.queryByRole("radio")).toBeNull();
      expect(screen.getByRole("alert")).toHaveTextContent("Condition non remplie");
    }
  });

  it("tells the 409 of an import without a calendar gap and reads it again [WF-INTF-0080-A]", async () => {
    open(gapped(), {
      [RULE]: { problem: example("import_duration_rule_without_gap") as Problem & { status: 409 } },
    });
    await userEvent.click(KEEP_DATES());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Condition non remplie : écart de calendrier au compte rendu",
    );
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("tells a refusal of permission under the choice, without reading again", async () => {
    open(gapped(), { [RULE]: { problem: { code: "PERMISSION_MISSING", status: 403 } } });
    await userEvent.click(KEEP_DATES());
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("shows an import failed after the new analysis as any failed analysis, with no choice [WF-INTF-0080-A]", () => {
    const analysing = example("import_duration_rule_set") as Import;
    open({ ...analysing, status: "failed" });
    expect(screen.queryByRole("radio")).toBeNull();
    expect(screen.getByText(/rouvrez le fichier/)).toBeVisible();
    expect(screen.queryByText("Cet import n’a pas de compte rendu.")).toBeNull();
  });

  it("leaves the project unchanged when abandoned after a change of option [WF-INTF-0080-A]", async () => {
    const client = open(gapped(), {
      [RULE]: { example: "import_duration_rule_set", status: 202 },
      [ABANDON]: { status: 204 },
    });
    await userEvent.click(KEEP_DATES());
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalled();
    });
    await userEvent.click(screen.getByRole("button", { name: "Abandonner l’import" }));
    await waitFor(() => {
      expect(router.push).toHaveBeenCalledWith(START);
    });
    expect(client.calls.map(({ route }) => route)).toEqual([RULE, ABANDON]);
  });
});
