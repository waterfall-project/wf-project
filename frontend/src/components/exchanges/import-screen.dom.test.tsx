// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { Project } from "@/components/context/reading";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  type FakeTiming,
  fakeClient,
  held,
  type Problem,
} from "@/test/fixtures";
import { tasksRegion } from "@/test/task-panel";

import { ImportCommands } from "./import-commands";
import { ImportReport } from "./import-report";
import { importOffers } from "./offers";

// What the screen of the imports does with an application that fails or is refused, and with a
// form while a file is sent (US-3280); the rest of the screen is in `exchanges.dom.test.tsx`.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => `/projects/${PROJECT}/revisions/${REVISION}/exchanges`,
  useSearchParams: () => new URLSearchParams(),
}));

type Import = components["schemas"]["ImportDetail"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IMPORT = "01926f3a-7c00-7000-8000-000000000a11";
const START = `/projects/${PROJECT}/revisions/${REVISION}/exchanges?as_of=2026-05-31`;
const UPLOAD = "POST /file-uploads";
const OPEN = "POST /projects/{project_id}/imports";
const APPLY = "POST /projects/{project_id}/imports/{import_id}/apply";
const RULE = "PUT /projects/{project_id}/imports/{import_id}/duration-rule";
const TASK = "GET /tasks/{task_id}";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers, timing?: FakeTiming): FakeClient {
  const client = fakeClient(answers, timing);
  server.client = client;
  return client;
}

/** Render a part of the screen within the shell that follows the tasks, in French. */
function open(part: ReactNode) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>{part}</main>
      </TaskTracker>
    </NextIntlClientProvider>,
  );
}

/** The report of an import, as the screen shows it. */
function report(entry: Import) {
  return <ImportReport projectId={PROJECT} entry={entry} start={START} />;
}

/** Press « Appliquer l’import » and confirm the application. */
async function apply() {
  await userEvent.click(screen.getByRole("button", { name: "Appliquer l’import" }));
  const confirmation = screen.getByRole("form", { name: "Confirmation de l’application" });
  await userEvent.click(
    within(confirmation).getByRole("button", { name: "Confirmer l’application" }),
  );
  return confirmation;
}

beforeEach(() => {
  window.history.replaceState(null, "", `${START}&import=${IMPORT}`);
  router.push.mockClear();
  router.refresh.mockClear();
  window.sessionStorage.clear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the application of an import that fails or is refused", () => {
  it("tells the failure of the application with its motive, offers no « Relancer » and says to start again from the screen [WF-IHM-0080-A]", async () => {
    // An import that failed has lost its file, and the service refuses its application still: the
    // tracker does not hold the command that would run it again (#4424, FCO-02).
    serve({
      [APPLY]: { example: "task_import_queued", status: 202 },
      [TASK]: "task_import_analysis_failed",
    });
    open(report(example("import_analysed") as Import));
    await apply();
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    const tasks = tasksRegion();
    await waitFor(() => {
      expect(within(tasks).getByText("Échouée")).toBeVisible();
    });
    expect(within(tasks).queryByRole("button", { name: /Relancer/ })).toBeNull();
    expect(
      within(tasks).getByText("Pour relancer cette tâche, repartez de l’écran de son objet."),
    ).toBeVisible();
  });

  it.each([
    ["import_apply_structure_changed", "the condition of the structure, a refusal for good"],
    ["import_apply_expired", "an import that expired"],
  ])(
    "reads the screen anew once the application is refused (409): %s — %s [US-3280]",
    async (name) => {
      serve({ [APPLY]: { problem: example(name) as Problem & { status: 409 } } });
      open(report(example("import_analysed") as Import));
      const confirmation = await apply();
      await waitFor(() => {
        expect(within(confirmation).getByRole("alert")).toBeVisible();
      });
      // The screen read anew says the import « Refusé » and lists no application: it does not stay
      // « Analysé », its « Appliquer » pressable for a refusal that will come again (FCO-04).
      expect(router.refresh).toHaveBeenCalledOnce();
    },
  );

  it("shows an import refused as such, with its explanation, and offers neither the application nor the choice of the rule [US-3280]", () => {
    serve({});
    const gapped = example("import_planning_calendar_gap") as Import;
    open(
      report({
        ...gapped,
        status: "refused",
        available_commands: [
          {
            command: "apply",
            is_available: false,
            missing_conditions: ["import_awaiting_decision"],
          },
          { command: "abandon", is_available: false, missing_conditions: ["import_not_applied"] },
        ],
      }),
    );
    expect(screen.getByText("Refusé", { selector: "dd" })).toBeVisible();
    expect(screen.getAllByText(CATALOGUES.fr.exchanges.refused).length).toBeGreaterThan(0);
    expect(screen.queryByRole("radio")).toBeNull();
    expect(screen.getByRole("button", { name: "Appliquer l’import" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });
});

describe("the choice of the rule of the durations while it is asked", () => {
  it("shows the rule chosen while the request runs, and goes back to the one in force when it is refused [US-3280]", async () => {
    const hold = held();
    serve(
      {
        [RULE]: {
          problem: example("import_duration_rule_applied") as Problem & { status: 409 },
        },
      },
      hold.timing,
    );
    open(report(example("import_planning_calendar_gap") as Import));
    const keepDates = screen.getByRole("radio", { name: /^Garder les dates/ });
    const keepDurations = screen.getByRole("radio", { name: /^Garder les durées/ });
    expect(keepDurations).toBeChecked();
    await userEvent.click(keepDates);
    expect(keepDates).toBeChecked();
    expect(keepDurations).not.toBeChecked();
    hold.release();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeVisible();
    });
    expect(keepDurations).toBeChecked();
    expect(keepDates).not.toBeChecked();
  });
});

describe("the commands of import while a file is sent", () => {
  /** The commands of import a project of the contract offers. */
  function commands() {
    const offers = importOffers(example("project") as Project);
    return <ImportCommands projectId={PROJECT} offers={offers} start={START} />;
  }

  it("keeps the commands inactive and « Analyser » waiting, and closes only the form that sent the file [US-3280]", async () => {
    const hold = held();
    const client = serve(
      {
        [UPLOAD]: { example: "file_upload", status: 201 },
        [OPEN]: { example: "import_analysing", status: 202 },
        [TASK]: "task_running",
      },
      hold.timing,
    );
    open(commands());
    await userEvent.click(screen.getByRole("button", { name: "Importer un devis" }));
    const form = screen.getByRole("form", { name: "Importer un devis" });
    await userEvent.upload(
      within(form).getByLabelText("Fichier à importer"),
      new File(["devis"], "devis.xlsx"),
    );
    const analyse = within(form).getByRole("button", { name: "Analyser le fichier" });
    await userEvent.click(analyse);
    expect(analyse).toHaveAttribute("aria-busy", "true");
    expect(analyse).toHaveAttribute("aria-disabled", "true");
    expect(analyse.querySelector("[data-waiting]")).not.toBeNull();
    const other = screen.getByRole("button", { name: "Importer un reste à engager" });
    expect(other).toHaveAttribute("aria-disabled", "true");
    expect(other).toHaveAttribute("aria-busy", "true");
    await userEvent.click(other);
    expect(screen.getAllByRole("form")).toHaveLength(1);
    hold.release();
    await waitFor(() => {
      expect(screen.queryByRole("form")).toBeNull();
    });
    expect(client.calls.map((call) => call.route).slice(0, 2)).toEqual([UPLOAD, OPEN]);
    expect(other).toHaveAttribute("aria-busy", "false");
    await userEvent.click(other);
    expect(screen.getByRole("form", { name: "Importer un reste à engager" })).toBeVisible();
  });

  it("closes no form, and takes no focus, when the answer of a deposit comes to a form cancelled since [US-3280] [FCO-03]", async () => {
    // FCO-03 is held in two parts. While the file goes every command is inactive (`writing`), so no
    // other form opens before the answer: the case of a form opened since cannot be reached. What
    // is left to hold is the answer itself, which comes to a form cancelled: it must not close
    // what is open (nothing) nor give the focus back to the command that was pressed, as the
    // user has gone elsewhere. Without the guard of the opening, the focus would jump back.
    const hold = held();
    serve(
      {
        [UPLOAD]: { example: "file_upload", status: 201 },
        [OPEN]: { example: "import_analysing", status: 202 },
        [TASK]: "task_running",
      },
      hold.timing,
    );
    open(commands());
    await userEvent.click(screen.getByRole("button", { name: "Importer un devis" }));
    const form = screen.getByRole("form", { name: "Importer un devis" });
    await userEvent.upload(
      within(form).getByLabelText("Fichier à importer"),
      new File(["devis"], "devis.xlsx"),
    );
    await userEvent.click(within(form).getByRole("button", { name: "Analyser le fichier" }));
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("form")).toBeNull();
    // Another command stays inactive until the answer, so no form is opened meanwhile.
    const other = screen.getByRole("button", { name: "Importer un reste à engager" });
    expect(other).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(other);
    expect(screen.queryByRole("form")).toBeNull();
    // The user moves on; the answer comes.
    other.focus();
    hold.release();
    await waitFor(() => {
      expect(router.push).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(other).not.toHaveAttribute("aria-disabled");
    });
    expect(screen.queryByRole("form")).toBeNull();
    expect(other).toHaveFocus();
    await userEvent.click(other);
    expect(screen.getByRole("form", { name: "Importer un reste à engager" })).toBeVisible();
  });
});
