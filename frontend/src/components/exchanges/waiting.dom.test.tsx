// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { Revision } from "@/components/context/read-only";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { closeTasks, tasksRegion } from "@/test/task-panel";

import { ExportForm } from "./export-form";
import { ImportReport } from "./import-report";
import { exportOffers } from "./offers";

// The commands of the exchanges that start a background task wait for it, saying so (#3103); the
// rest of the screen is in `exchanges.dom.test.tsx`. The server of Next, as far as the exchanges need
// it, and its router, whose refresh reads the screen anew.
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
const APPLY = "POST /projects/{project_id}/imports/{import_id}/apply";
const EXPORT = "POST /projects/{project_id}/exports";
const TASK = "GET /tasks/{task_id}";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** Render a part of the screen within the shell that follows the tasks. */
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

/** The request of an export of the revision of the contract, as it offers its exports. */
function exportForm() {
  const offers = exportOffers(example("revision") as Revision);
  return <ExportForm projectId={PROJECT} revisionId={REVISION} offers={offers} />;
}

/** The report of an import of the contract, as the screen shows it. */
function report(entry: Import) {
  return <ImportReport projectId={PROJECT} entry={entry} start={START} />;
}

/** Press « Appliquer l’import » and give the confirmation it opens. */
async function askApplication() {
  await userEvent.click(screen.getByRole("button", { name: "Appliquer l’import" }));
  return screen.getByRole("form", { name: "Confirmation de l’application" });
}

/** Press the button that confirms the application, in the confirmation. */
async function confirmApplication(confirmation: HTMLElement) {
  await userEvent.click(
    within(confirmation).getByRole("button", { name: "Confirmer l’application" }),
  );
}

/** Wait until the confirmation, accepted, has gone. */
async function closed() {
  await waitFor(() => {
    expect(screen.queryByRole("form")).toBeNull();
  });
}

/** Wait until a form no longer waits for the answer of its action. */
async function settled(form: HTMLElement) {
  await waitFor(() => {
    expect(form).toHaveAttribute("aria-busy", "false");
  });
}

beforeEach(() => {
  // The browser shows the report of the import, on the screen of the exchanges.
  window.history.replaceState(null, "", `${START}&import=${IMPORT}`);
  router.push.mockClear();
  router.refresh.mockClear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("a command of the exchanges that starts a background task", () => {
  it("keeps the application waiting while its task runs, and reads the imports of the project anew once it has ended (#3103)", async () => {
    serve({
      [APPLY]: { example: "task_import_queued", status: 202 },
      [TASK]: "task_import_succeeded",
    });
    open(report(example("import_analysed") as Import));
    await confirmApplication(await askApplication());
    await closed();
    const apply = screen.getByRole("button", { name: "Appliquer l’import" });
    expect(apply).toHaveAttribute("aria-busy", "true");
    expect(apply).toHaveAttribute("aria-disabled", "true");
    expect(apply.querySelector("[data-waiting]")).not.toBeNull();
    await userEvent.click(apply);
    expect(screen.queryByRole("form")).toBeNull();
    expect(router.refresh).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalledOnce();
    });
    expect(apply).toHaveAttribute("aria-busy", "false");
  });

  it("waits, saying so, for the export it asked, asks no second one, and is given back by its failure [WF-IHM-0080-A]", async () => {
    // L'échec d'un traitement de fond est signalé avec son motif, et le même traitement peut être
    // relancé : the five exports of 2026-11-13 were asked from a button that said nothing (#3103).
    const client = serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_tree_image_too_large",
    });
    open(exportForm());
    const form = screen.getByRole("form", { name: "Demander un export" });
    const request = within(form).getByRole("button", { name: "Demander l’export" });
    await userEvent.click(request);
    await settled(form);
    expect(request).toHaveAttribute("aria-busy", "true");
    expect(request).toHaveAttribute("aria-disabled", "true");
    expect(request.querySelector("[data-waiting]")).not.toBeNull();
    await userEvent.click(request);
    const asked = () => client.calls.filter((call) => call.route === EXPORT);
    expect(asked()).toHaveLength(1);

    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    expect(within(tasksRegion()).getByText("Échouée")).toBeVisible();
    closeTasks();
    expect(request).toHaveAttribute("aria-busy", "false");
    expect(request).not.toHaveAttribute("aria-disabled");
    expect(request.querySelector("[data-waiting]")).toBeNull();
    await userEvent.click(request);
    await settled(form);
    expect(asked()).toHaveLength(2);
  });
});
