// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { markRevision } from "@/api/actions/revisions";
import { type ApiClient, createApiClient } from "@/api/client";
import type { BackgroundTask } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { STORAGE_KEY } from "./storage";
import { POLL_INTERVAL } from "./task-entry";
import { TaskPanel, TaskTracker, useTrackTask } from "./task-tracker";
import type { Launch } from "./tracking";

// The server of Next, as far as the tracker needs it: the fake back behind serverClient, which
// a test may swap for another between two reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
// The router of Next, as far as a notice needs it: the refresh that reads the screen anew.
const router = vi.hoisted(() => ({ refresh: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions",
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const MARKING = "01926f3a-7c00-7000-8000-000000000901";
const IMPORT = "01926f3a-7c00-7000-8000-000000000902";
const TASK = "GET /tasks/{task_id}";
const MARK = "POST /projects/{project_id}/revisions/{revision_id}/mark";

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

/** A screen of the application, which starts a task when the user presses its button. */
function Screen({ name, start }: { readonly name: string; readonly start?: () => void }) {
  return (
    <main>
      <h1>{name}</h1>
      {start === undefined ? null : (
        <button type="button" onClick={start}>
          Lancer
        </button>
      )}
    </main>
  );
}

/** A screen that hands a task over to the tracker, as a command does once the API answered. */
function Starting({
  given,
  launch,
}: {
  readonly given: BackgroundTask;
  readonly launch?: Launch | undefined;
}) {
  const track = useTrackTask();
  return (
    <Screen
      name="Import"
      start={() => {
        track(given, launch);
      }}
    />
  );
}

/** The shell, as far as the tracker goes: the texts, the tracker, its panel, the page. */
function shell(page: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <TaskPanel />
        {page}
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** Render a screen that starts a task, and start it. */
async function started(given: BackgroundTask, launch?: Launch) {
  const view = render(shell(<Starting given={given} launch={launch} />));
  await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
  return view;
}

/** Let the time of one read go by, and the read be answered. */
async function tick(times = 1) {
  for (let turn = 0; turn < times; turn += 1) {
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
  }
}

/** The tasks the shell follows. */
function panel() {
  return screen.getByRole("region", { name: "Tâches de fond" });
}

/** The tasks the panel lists, apart from the announcement that repeats the end of one. */
function entries() {
  return within(panel()).getByRole("list");
}

/** The announcement of the end of a task. */
function announcement() {
  return within(panel()).getByRole("status");
}

/** The sentences of the announcement, as they are written: typography included. */
function announced(): (string | null)[] {
  return [...announcement().children].map((sentence) => sentence.textContent);
}

/** What the progress of the task says next to its bar. */
function progressText(): string | null | undefined {
  return within(panel()).getByRole("progressbar").nextElementSibling?.textContent;
}

/** The paths the tracker asked the API. */
function reads(client: FakeClient): string[] {
  return client.calls.filter((call) => call.route === TASK).map((call) => call.path);
}

/** A client of the API whose every call finds the API out of reach. */
function unreachable(): ApiClient {
  return createApiClient({
    address: "http://unreachable.invalid",
    fetch: () => Promise.reject(new TypeError("fetch failed")),
  });
}

beforeEach(() => {
  router.refresh.mockClear();
  // The time of the tracker is the test's: a read comes when the test lets it come.
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the tracker of background tasks", () => {
  it("informs a user who changed screens during an import of its end [WF-IHM-0080-A]", async () => {
    // Un utilisateur qui change d'écran pendant un import est informé de son aboutissement.
    // The follow-up is one for every kind of task: an import applied here, a marking there.
    const client = serve({ [TASK]: "task_import_succeeded" });
    const view = await started(task("task_import_queued"));
    expect(within(entries()).getByText("Application d’un import")).toBeVisible();
    expect(within(entries()).getByText("En attente")).toBeVisible();

    // The user goes to another screen: the one that started the import is gone.
    view.rerender(shell(<Screen name="Planning" />));
    expect(screen.getByRole("heading", { name: "Planning" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Lancer" })).toBeNull();

    await tick();
    expect(announced()).toEqual(["Tâche terminée\u00A0: Application d’un import."]);
    expect(within(entries()).getByText("Réussie")).toBeVisible();
    expect(reads(client)).toEqual([`/tasks/${IMPORT}`]);
  });

  it("signals the failure of a background task with its motive, and runs the same treatment again [WF-IHM-0080-A]", async () => {
    // L'échec d'un traitement de fond est signalé avec son motif, et le même traitement peut
    // être relancé.
    const client = serve({
      [MARK]: { example: "task_mark_queued", status: 202 },
      [TASK]: ["task_failed", "task_running"],
    });
    const mark = { version_name: "V2", lock_version: 4 };
    const command = () => markRevision(PROJECT, REVISION, mark);
    const { container } = await started(task("task_mark_queued"), { command, subject: "V2" });

    await tick();
    const motive = "Aucun taux horaire n’est défini pour ce rôle et cette année.";
    expect(announced()).toEqual([
      "Tâche échouée\u00A0: Marquage d’une révision «\u00A0V2\u00A0».",
      motive,
    ]);
    expect(within(entries()).getByText("Échouée")).toBeVisible();
    expect(within(entries()).getByText(motive)).toBeVisible();
    await expectAccessible(container);

    await userEvent.click(within(panel()).getByRole("button", { name: "Relancer" }));
    // The same command, with the same version name and the same version of the revision.
    const marks = client.calls.filter((call) => call.route === MARK);
    expect(marks.map((call) => [call.path, call.body])).toEqual([
      [`/projects/${PROJECT}/revisions/${REVISION}/mark`, mark],
    ]);
    expect(within(entries()).getByText("En attente")).toBeVisible();
    expect(announcement()).toBeEmptyDOMElement();
    expect(
      screen.getByRole("button", {
        name: "Retirer du suivi\u00A0: Marquage d’une révision «\u00A0V2\u00A0»",
      }),
    ).toHaveFocus();

    await tick();
    expect(within(panel()).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "40");
    expect(reads(client)).toEqual([`/tasks/${MARKING}`, `/tasks/${MARKING}`]);
  });

  it("shows how far a task has gone, asks again while it runs, and stops once it has ended", async () => {
    const client = serve({ [TASK]: ["task_running", "task_succeeded"] });
    const { container } = await started(task("task_mark_queued"));
    const bar = within(panel()).getByRole("progressbar", { name: "Marquage d’une révision" });
    expect(bar).toHaveAttribute("aria-valuenow", "0");
    expect(progressText()).toBe("0\u202F%");
    await expectAccessible(container);

    await tick();
    expect(bar).toHaveAttribute("aria-valuenow", "40");
    expect(progressText()).toBe("40\u202F%");
    expect(within(entries()).getByText("En cours")).toBeVisible();

    await tick();
    expect(within(panel()).queryByRole("progressbar")).toBeNull();
    expect(announced()).toEqual(["Tâche terminée\u00A0: Marquage d’une révision."]);

    await tick(3);
    expect(reads(client)).toHaveLength(2);
  });

  it("shows a bar without a value while the API does not say how far a task has gone", async () => {
    serve({ [TASK]: "task_running" });
    // The contract makes the progress optional: a task queued without one.
    const unmeasured = task("task_mark_queued");
    delete unmeasured.progress;
    await started(unmeasured);
    expect(within(panel()).getByRole("progressbar")).not.toHaveAttribute("aria-valuenow");
    expect(within(entries()).queryByText(/%/)).toBeNull();
  });

  it("stops asking once the shell goes away", async () => {
    const client = serve({ [TASK]: "task_running" });
    const view = await started(task("task_mark_queued"));
    view.unmount();
    await tick(2);
    expect(reads(client)).toEqual([]);
  });

  it("stops following a task the user dismisses", async () => {
    const client = serve({ [TASK]: "task_running" });
    await started(task("task_import_queued"));
    await userEvent.click(
      screen.getByRole("button", { name: "Retirer du suivi\u00A0: Application d’un import" }),
    );
    expect(screen.queryByRole("region", { name: "Tâches de fond" })).toBeNull();
    await tick(2);
    expect(reads(client)).toEqual([]);
  });

  it("shows nothing while it follows no task", () => {
    render(shell(<Screen name="Planning" />));
    expect(screen.queryByRole("region", { name: "Tâches de fond" })).toBeNull();
  });

  it("says the API is out of reach, and asks again until it answers", async () => {
    server.client = unreachable();
    await started(task("task_mark_queued"));
    await tick();
    expect(within(panel()).getByRole("alert").textContent).toBe(
      "Le service est injoignable\u202F; réessayez dans un instant.",
    );

    serve({ [TASK]: "task_succeeded" });
    await tick();
    expect(within(panel()).queryByRole("alert")).toBeNull();
    expect(announced()).toEqual(["Tâche terminée\u00A0: Marquage d’une révision."]);
  });

  it("takes a server action that does not answer at all for the API out of reach", async () => {
    server.client = {
      GET: () => Promise.reject(new Error("the server of Next cannot be reached")),
    } as unknown as ApiClient;
    await started(task("task_mark_queued"));
    await tick();
    expect(within(panel()).getByRole("alert")).toHaveTextContent("Le service est injoignable");
  });

  it("stops asking once the API refuses to say where the task stands, and tells why", async () => {
    const client = serve({ [TASK]: { problem: { code: "NOT_FOUND", status: 404 } } });
    await started(task("task_mark_queued"));
    await tick();
    expect(within(panel()).getByRole("alert").textContent).toBe(
      "Introuvable\u00A0: cet élément n’existe pas, ou vous n’y avez pas accès.",
    );
    await tick(2);
    expect(reads(client)).toHaveLength(1);
  });

  it("tells the refusal of a relaunch, and keeps the failed task to run again", async () => {
    serve({
      [MARK]: { problem: { code: "ALREADY_EXISTS", status: 409 } },
      [TASK]: "task_failed",
    });
    const command = () => markRevision(PROJECT, REVISION, { version_name: "V2", lock_version: 4 });
    await started(task("task_mark_queued"), { command, subject: "V2" });
    await tick();
    await userEvent.click(within(panel()).getByRole("button", { name: "Relancer" }));

    expect(within(panel()).getByRole("alert")).toHaveTextContent("Cet élément existe déjà.");
    expect(within(entries()).getByText("Échouée")).toBeVisible();
    expect(within(panel()).getByRole("button", { name: "Relancer" })).toBeVisible();
  });

  it("offers to reload a revision changed since the failed task was started", async () => {
    serve({
      [MARK]: { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
      [TASK]: "task_failed",
    });
    const command = () => markRevision(PROJECT, REVISION, { version_name: "V2", lock_version: 4 });
    await started(task("task_mark_queued"), { command });
    await tick();
    await userEvent.click(within(panel()).getByRole("button", { name: "Relancer" }));
    const alert = within(panel()).getByRole("alert");
    await userEvent.click(within(alert).getByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(within(panel()).queryByRole("alert")).toBeNull();
    expect(within(entries()).getByText("Échouée")).toBeVisible();
  });

  it("says the API is out of reach when the relaunch does not answer at all", async () => {
    serve({ [TASK]: "task_failed" });
    const command = () => Promise.reject(new Error("the server of Next cannot be reached"));
    await started(task("task_mark_queued"), { command });
    await tick();
    await userEvent.click(within(panel()).getByRole("button", { name: "Relancer" }));
    expect(within(panel()).getByRole("alert")).toHaveTextContent("Le service est injoignable");
  });

  it("offers no relaunch of a failed task handed over without its command", async () => {
    serve({ [TASK]: "task_failed" });
    await started(task("task_mark_queued"));
    await tick();
    expect(within(entries()).getByText("Échouée")).toBeVisible();
    expect(within(panel()).queryByRole("button", { name: "Relancer" })).toBeNull();
  });

  it("is a piece of the shell: a screen outside it cannot hand a task over", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<Starting given={task("task_mark_queued")} />)).toThrow(
      "within the TaskTracker of the shell",
    );
  });
});

describe("the follow-up across a full reload of the tab", () => {
  it("keeps the tasks that still run in the storage of the tab, and forgets them once ended", async () => {
    serve({ [TASK]: ["task_running", "task_succeeded"] });
    await started(task("task_mark_queued"), { subject: "V2" });
    expect(JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "null")).toEqual([
      { key: MARKING, task_id: MARKING, kind: "revision_mark", status: "queued", subject: "V2" },
    ]);
    await tick(2);
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("follows again, after a reload, the tasks the tab followed, without their command", async () => {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { key: MARKING, task_id: MARKING, kind: "revision_mark", status: "running", subject: "V2" },
        // What is not a running task kept here is left: an ended task, an unknown kind, junk.
        { key: IMPORT, task_id: IMPORT, kind: "import_apply", status: "succeeded" },
        { key: "k", task_id: "t", kind: "print", status: "running" },
        { key: "k", task_id: "t", kind: "export", status: "running", subject: 3 },
        "junk",
        null,
      ]),
    );
    const client = serve({ [TASK]: "task_failed" });
    render(shell(<Screen name="Planning" />));

    expect(within(panel()).getAllByRole("listitem")).toHaveLength(1);
    expect(within(panel()).getByRole("listitem")).toHaveTextContent(
      "Marquage d’une révision « V2 »",
    );
    await tick();
    expect(reads(client)).toEqual([`/tasks/${MARKING}`]);
    expect(announcement()).toHaveTextContent("Tâche échouée");
    // The command did not survive the reload: the user starts it again from its screen.
    expect(within(panel()).queryByRole("button", { name: "Relancer" })).toBeNull();
  });

  it("follows nothing again when the storage holds no list", () => {
    window.sessionStorage.setItem(STORAGE_KEY, "{not json");
    render(shell(<Screen name="Planning" />));
    expect(screen.queryByRole("region", { name: "Tâches de fond" })).toBeNull();
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ key: MARKING }));
    render(shell(<Screen name="Planning" />));
    expect(screen.queryByRole("region", { name: "Tâches de fond" })).toBeNull();
  });

  it("follows the tasks all the same when the browser refuses the storage", async () => {
    const refused = () => {
      throw new DOMException("refused", "SecurityError");
    };
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(refused);
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(refused);
    serve({ [TASK]: "task_succeeded" });
    await started(task("task_mark_queued"));
    await tick();
    expect(announcement()).toHaveTextContent("Tâche terminée");
  });
});
