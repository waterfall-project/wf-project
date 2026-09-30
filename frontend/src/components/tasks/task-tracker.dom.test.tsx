// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { markRevision } from "@/api/actions/revisions";
import type { ApiClient } from "@/api/client";
import type { BackgroundTask, Outcome } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  unreachable,
} from "@/test/fixtures";

import { STORAGE_KEY } from "./storage";
import { POLL_INTERVAL } from "./task-entry";
import { TaskPanel, TasksButton, TaskTracker, useTrackTask } from "./task-tracker";
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
const RELAUNCHED = "01926f3a-7c00-7000-8000-000000000903";
const TASK = "GET /tasks/{task_id}";
const TASKS = "GET /tasks";
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

/**
 * The shell, as far as the tracker goes: the texts, the tracker, the button of its panel in the
 * bar, its panel, the page.
 */
function shell(page: ReactNode, signedIn = false, running?: readonly BackgroundTask[]) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker signedIn={signedIn} running={running}>
        <header>
          <TasksButton />
        </header>
        <TaskPanel />
        {page}
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** The button of the bar that shows or hides the panel, whatever the number it names. */
function panelButton() {
  return screen.getByRole("button", { name: /^Tâches de fond/ });
}

/** Render a screen that starts a task, and start it. */
async function started(given: BackgroundTask, launch?: Launch) {
  const view = render(shell(<Starting given={given} launch={launch} />));
  await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
  return view;
}

/** A screen that hands several tasks over to the tracker at once. */
function StartingAll({ given }: { readonly given: readonly BackgroundTask[] }) {
  const track = useTrackTask();
  return (
    <Screen
      name="Import"
      start={() => {
        for (const one of given) {
          track(one);
        }
      }}
    />
  );
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

/** The tasks the panel lists, apart from the log that repeats their ends. */
function entries() {
  return within(panel()).getByRole("list");
}

/** The log of the ends of the tasks. */
function endLog() {
  return within(panel()).getByRole("log");
}

/** The ends the log reads out, each in its sentences, as they are written: typography included. */
function ends(): (string | null)[][] {
  return [...endLog().children].map((end) =>
    [...end.children].map((sentence) => sentence.textContent),
  );
}

/** The button that dismisses a task, by the name of the task. */
function dismissal(name: string) {
  return screen.getByRole("button", { name: `Retirer du suivi\u00A0: ${name}` });
}

/** The button that runs a failed task again, by the name of the task. */
function relaunchButton(name = "Marquage d’une révision") {
  return within(panel()).getByRole("button", { name: `Relancer\u00A0: ${name}` });
}

/** What the progress of the task says next to its bar. */
function progressText(): string | null | undefined {
  return within(panel()).getByRole("progressbar").nextElementSibling?.textContent;
}

/** The paths the tracker asked the API. */
function reads(client: FakeClient): string[] {
  return client.calls.filter((call) => call.route === TASK).map((call) => call.path);
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
    expect(ends()).toEqual([["Tâche terminée\u00A0: Application d’un import."]]);
    expect(within(entries()).getByText("Réussie")).toBeVisible();
    expect(reads(client)).toEqual([`/tasks/${IMPORT}`]);
  });

  it("signals the failure of a background task with its motive, and runs the same treatment again [WF-IHM-0080-A]", async () => {
    // L'échec d'un traitement de fond est signalé avec son motif, et le même traitement peut
    // être relancé.
    const client = serve({
      [MARK]: { example: "task_mark_relaunched", status: 202 },
      [TASK]: ["task_failed", "task_mark_relaunched"],
    });
    const mark = { version_name: "V2", lock_version: 4 };
    const command = () => markRevision(PROJECT, REVISION, mark);
    const { container } = await started(task("task_mark_queued"), { command, subject: "V2" });

    await tick();
    const motive = "Aucun taux horaire n’est défini pour ce rôle et cette année.";
    expect(ends()).toEqual([
      ["Tâche échouée\u00A0: Marquage d’une révision «\u00A0V2\u00A0».", motive],
    ]);
    expect(within(entries()).getByText("Échouée")).toBeVisible();
    expect(within(entries()).getByText(motive)).toBeVisible();
    await expectAccessible(container);

    // The relaunch names its task, its name beginning with the label it shows.
    const relaunch = relaunchButton("Marquage d’une révision «\u00A0V2\u00A0»");
    expect(relaunch.textContent).toBe("Relancer");
    await userEvent.click(relaunch);
    // The same command, with the same version name and the same version of the revision.
    const marks = client.calls.filter((call) => call.route === MARK);
    expect(marks.map((call) => [call.path, call.body])).toEqual([
      [`/projects/${PROJECT}/revisions/${REVISION}/mark`, mark],
    ]);
    expect(within(entries()).getByText("En attente")).toBeVisible();
    expect(dismissal("Marquage d’une révision «\u00A0V2\u00A0»")).toHaveFocus();

    // The new task is followed, not the one that failed.
    await tick();
    expect(reads(client)).toEqual([`/tasks/${MARKING}`, `/tasks/${RELAUNCHED}`]);
    expect(ends()).toHaveLength(1);
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
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision."]]);

    await tick(3);
    expect(reads(client)).toHaveLength(2);
  });

  it("offers to reload the screen once a task has succeeded, and never reloads by itself", async () => {
    serve({ [TASK]: "task_succeeded" });
    await started(task("task_mark_queued"));
    await tick();
    const reload = within(entries()).getByRole("button", { name: "Recharger l’écran" });
    await tick(2);
    expect(router.refresh).not.toHaveBeenCalled();
    await userEvent.click(reload);
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("offers no reload of the screen while a task runs, nor once it has failed", async () => {
    serve({ [TASK]: ["task_running", "task_failed"] });
    await started(task("task_mark_queued"));
    await tick();
    expect(within(entries()).queryByRole("button", { name: "Recharger l’écran" })).toBeNull();
    await tick();
    expect(within(entries()).queryByRole("button", { name: "Recharger l’écran" })).toBeNull();
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
    await userEvent.click(dismissal("Application d’un import"));
    expect(within(panel()).queryByRole("list")).toBeNull();
    await tick(2);
    expect(reads(client)).toEqual([]);
  });

  it("takes the focus from a task dismissed to the next, else the one before, else the main content", async () => {
    serve({ [TASK]: "task_running" });
    const all = [
      task("task_mark_queued"),
      task("task_import_queued"),
      task("task_mark_relaunched"),
    ];
    render(shell(<StartingAll given={all} />));
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    const [first, second, third] = within(entries()).getAllByRole("button");
    await userEvent.click(first ?? document.body);
    expect(second).toHaveFocus();
    await userEvent.click(third ?? document.body);
    expect(second).toHaveFocus();
    await userEvent.click(second ?? document.body);
    // The last one gone, the region is empty, without a height to show a focus: the focus
    // goes to the main content of the page, outside the order of the keyboard, never to the
    // document.
    expect(within(panel()).queryByRole("list")).toBeNull();
    const main = screen.getByRole("main");
    expect(main).toHaveFocus();
    expect(main).toHaveAttribute("tabindex", "-1");
    expect(document.activeElement).not.toBe(document.body);
  });

  it("keeps a task being relaunched from being dismissed, lest the task relaunched be lost", async () => {
    serve({ [TASK]: "task_failed" });
    let answer: (outcome: Outcome<BackgroundTask>) => void = () => undefined;
    const command = () =>
      new Promise<Outcome<BackgroundTask>>((resolve) => {
        answer = resolve;
      });
    await started(task("task_mark_queued"), { command });
    await tick();
    await userEvent.click(relaunchButton());
    const dismiss = dismissal("Marquage d’une révision");
    expect(dismiss).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(dismiss);
    expect(within(entries()).getAllByRole("listitem")).toHaveLength(1);

    await act(async () => {
      answer({ kind: "done", data: task("task_mark_relaunched") });
      await Promise.resolve();
    });
    expect(dismiss).not.toHaveAttribute("aria-disabled");
    expect(within(entries()).getByText("En attente")).toBeVisible();
  });

  it("keeps its region and its log in place while it follows no task, and lists nothing", () => {
    render(shell(<Screen name="Planning" />));
    expect(within(panel()).queryByRole("list")).toBeNull();
    expect(endLog()).toBeEmptyDOMElement();
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
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision."]]);
  });

  it("takes a server action that does not answer at all for the API out of reach", async () => {
    server.client = {
      GET: () => Promise.reject(new Error("the server of Next cannot be reached")),
    } as unknown as ApiClient;
    await started(task("task_mark_queued"));
    await tick();
    expect(within(panel()).getByRole("alert")).toHaveTextContent("Le service est injoignable");
  });

  it("interrupts the follow-up once the API refuses to say where the task stands, and says why", async () => {
    const client = serve({ [TASK]: { problem: { code: "NOT_FOUND", status: 404 } } });
    await started(task("task_mark_queued"));
    expect(window.sessionStorage.getItem(STORAGE_KEY)).not.toBeNull();
    await tick();
    const refusal = "Introuvable\u00A0: cet élément n’existe pas, ou vous n’y avez pas accès.";
    // No longer said to run, no progress, no alert: an announcement among the others.
    expect(within(entries()).getByText("Suivi interrompu")).toBeVisible();
    expect(within(entries()).queryByText("En attente")).toBeNull();
    expect(within(panel()).queryByRole("progressbar")).toBeNull();
    expect(within(panel()).queryByRole("alert")).toBeNull();
    expect(within(entries()).getByText(/^Introuvable/).textContent).toBe(refusal);
    expect(ends()).toEqual([["Suivi interrompu\u00A0: Marquage d’une révision.", refusal]]);
    // Not kept for a reload: there is nothing more to follow.
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    await tick(2);
    expect(reads(client)).toHaveLength(1);
  });

  it("leads to the sign-in page when the session is gone during the follow-up", async () => {
    serve({ [TASK]: { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    await started(task("task_mark_queued"));
    await tick();
    expect(within(entries()).getByText("Suivi interrompu")).toBeVisible();
    expect(within(entries()).getByRole("link", { name: "Se connecter" })).toBeVisible();
  });

  it("keeps a task interrupted for want of a session, and follows it on after a reload", async () => {
    serve({ [TASK]: { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    const view = await started(task("task_mark_queued"), { subject: "V2" });
    await tick();
    expect(JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "null")).toEqual([
      { key: MARKING, task_id: MARKING, kind: "revision_mark", status: "queued", subject: "V2" },
    ]);

    // Signed in again, the user reloads the tab: the task is read anew, and its end announced.
    view.unmount();
    const client = serve({ [TASK]: "task_succeeded" });
    render(shell(<Screen name="Planning" />));
    await tick();
    expect(reads(client)).toEqual([`/tasks/${MARKING}`]);
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision «\u00A0V2\u00A0»."]]);
  });

  it("leaves no alert of the API out of reach once the API refuses to say where the task stands", async () => {
    server.client = unreachable();
    await started(task("task_mark_queued"));
    await tick();
    expect(within(panel()).getByRole("alert")).toHaveTextContent("Le service est injoignable");

    serve({ [TASK]: { problem: { code: "NOT_FOUND", status: 404 } } });
    await tick();
    expect(within(entries()).getByText("Suivi interrompu")).toBeVisible();
    expect(within(panel()).queryByRole("alert")).toBeNull();
  });

  it("tells the refusal of a relaunch, and keeps the failed task to run again", async () => {
    serve({
      [MARK]: { problem: { code: "ALREADY_EXISTS", status: 409 } },
      [TASK]: "task_failed",
    });
    const command = () => markRevision(PROJECT, REVISION, { version_name: "V2", lock_version: 4 });
    await started(task("task_mark_queued"), { command, subject: "V2" });
    await tick();
    await userEvent.click(relaunchButton("Marquage d’une révision «\u00A0V2\u00A0»"));

    expect(within(panel()).getByRole("alert")).toHaveTextContent("Cet élément existe déjà.");
    expect(within(entries()).getByText("Échouée")).toBeVisible();
    expect(relaunchButton("Marquage d’une révision «\u00A0V2\u00A0»")).toBeVisible();
  });

  it("offers no relaunch bound to be refused again once the object changed since it was read", async () => {
    const client = serve({
      [MARK]: { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
      [TASK]: "task_failed",
    });
    const command = () => markRevision(PROJECT, REVISION, { version_name: "V2", lock_version: 4 });
    await started(task("task_mark_queued"), { command });
    await tick();
    await userEvent.click(relaunchButton());

    // The same version of the revision would be refused again: the command goes, and the
    // entry says where to start the treatment again. The focus, on the button gone, stays in
    // the entry, on its dismissal.
    expect(within(panel()).queryByRole("button", { name: /^Relancer/ })).toBeNull();
    expect(dismissal("Marquage d’une révision")).toHaveFocus();
    expect(document.activeElement).not.toBe(document.body);
    expect(
      within(entries()).getByText("Pour relancer cette tâche, repartez de l’écran de son objet."),
    ).toBeVisible();
    expect(client.calls.filter((call) => call.route === MARK)).toHaveLength(1);
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
    await userEvent.click(relaunchButton());
    expect(within(panel()).getByRole("alert")).toHaveTextContent("Le service est injoignable");
  });

  it("offers no relaunch of a failed task handed over without its command", async () => {
    serve({ [TASK]: "task_failed" });
    await started(task("task_mark_queued"));
    await tick();
    expect(within(entries()).getByText("Échouée")).toBeVisible();
    expect(within(panel()).queryByRole("button", { name: /^Relancer/ })).toBeNull();
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
    expect(ends()[0]?.[0]).toBe("Tâche échouée\u00A0: Marquage d’une révision «\u00A0V2\u00A0».");
    // The command did not survive the reload: the entry says where to start it again.
    expect(within(panel()).queryByRole("button", { name: /^Relancer/ })).toBeNull();
    expect(
      within(entries()).getByText("Pour relancer cette tâche, repartez de l’écran de son objet."),
    ).toBeVisible();
  });

  it("follows nothing again when the storage holds no list", () => {
    window.sessionStorage.setItem(STORAGE_KEY, "{not json");
    const view = render(shell(<Screen name="Planning" />));
    expect(within(panel()).queryByRole("list")).toBeNull();
    view.unmount();
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ key: MARKING }));
    render(shell(<Screen name="Planning" />));
    expect(within(panel()).queryByRole("list")).toBeNull();
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
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision."]]);
  });

  it("shows the panel from the button of the bar, which names the number of the tasks followed", async () => {
    serve({ [TASK]: "task_running" });
    render(shell(<Starting given={task("task_mark_queued")} />));
    const button = panelButton();
    expect(button).toHaveAccessibleName("Tâches de fond");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveAttribute("aria-controls", panel().id);
    expect(button.querySelector("svg")).toHaveAttribute("aria-hidden", "true");

    // Shown before any task, the panel says it follows none.
    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(within(panel()).getByText("Aucune tâche de fond suivie.")).toBeVisible();
    await userEvent.click(button);
    expect(within(panel()).queryByText("Aucune tâche de fond suivie.")).toBeNull();

    // A task handed over shows the panel, and the button counts it.
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    expect(button).toHaveAccessibleName("Tâches de fond\u00A0: 1 suivie");
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(within(entries()).getByText("Marquage d’une révision")).toBeVisible();
    await expectAccessible(document.body);
  });

  it("follows the tasks still, and reads out their ends, with the panel hidden", async () => {
    const client = serve({ [TASK]: ["task_running", "task_succeeded"] });
    await started(task("task_mark_queued"));
    await userEvent.click(panelButton());
    expect(panelButton()).toHaveAttribute("aria-expanded", "false");
    expect(within(panel()).queryByRole("list")).toBeNull();

    await tick(2);
    expect(reads(client)).toHaveLength(2);
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision."]]);

    // Shown again, the panel lists the task as it now stands.
    await userEvent.click(panelButton());
    expect(within(entries()).getByText("Réussie")).toBeVisible();
  });

  it("shows the panel again on the next task handed over, once the user hid it", async () => {
    serve({ [TASK]: "task_running" });
    const view = await started(task("task_mark_queued"));
    await userEvent.click(panelButton());
    expect(within(panel()).queryByRole("list")).toBeNull();

    view.rerender(shell(<Starting given={task("task_import_queued")} />));
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    expect(panelButton()).toHaveAttribute("aria-expanded", "true");
    expect(panelButton()).toHaveAccessibleName("Tâches de fond\u00A0: 2 suivies");
  });
});

/** The tasks of the user the root layout read with the document, by the name of their example. */
function listed(name: string): readonly BackgroundTask[] {
  return (example(name) as { readonly items: readonly BackgroundTask[] }).items;
}

/** The tab hidden, or shown again, as the browser tells it. */
function showTab(state: DocumentVisibilityState) {
  vi.spyOn(document, "visibilityState", "get").mockReturnValue(state);
  act(() => {
    document.dispatchEvent(new Event("visibilitychange"));
  });
}

describe("the tasks of its user the API lists", () => {
  it("follows the tasks of its user that ran as the document was read, started elsewhere, and announces their end, without a server action as it mounts", async () => {
    const client = serve({ [TASK]: "task_failed" });
    render(shell(<Screen name="Planning" />, true, listed("tasks_running")));

    // The marking another tab started, read with the document.
    expect(within(panel()).getByRole("listitem")).toHaveTextContent("Marquage d’une révision");
    expect(client.calls).toEqual([]);
    await tick();
    expect(reads(client)).toEqual([`/tasks/${MARKING}`]);
    expect(ends()[0]?.[0]).toBe("Tâche échouée\u00A0: Marquage d’une révision.");
    // The list does not say which command started it: it is run again from its screen.
    expect(within(panel()).queryByRole("button", { name: /^Relancer/ })).toBeNull();
    expect(
      within(entries()).getByText("Pour relancer cette tâche, repartez de l’écran de son objet."),
    ).toBeVisible();
  });

  it("reads the list again when the tab shows once more, and follows what another tab started", async () => {
    const client = serve({ [TASKS]: "tasks_running", [TASK]: "task_running" });
    render(shell(<Screen name="Planning" />, true, listed("tasks_none")));
    const asked = () => client.calls.filter((call) => call.route === TASKS);
    expect(within(panel()).queryByRole("list")).toBeNull();
    // Hidden, the tab asks nothing; shown again, it asks.
    showTab("hidden");
    expect(asked()).toEqual([]);
    showTab("visible");
    expect(await within(panel()).findByRole("listitem")).toHaveTextContent(
      "Marquage d’une révision",
    );
    expect(asked().map((call) => call.query.get("status"))).toEqual(["queued,running"]);
  });

  it("brings back no task the user dismissed, when the tab shows again and the list is read anew", async () => {
    const client = serve({ [TASKS]: "tasks_running", [TASK]: "task_running" });
    render(shell(<Screen name="Planning" />, true, listed("tasks_running")));
    await userEvent.click(dismissal("Marquage d’une révision"));
    expect(within(panel()).queryByRole("list")).toBeNull();
    showTab("visible");
    await vi.waitFor(() => {
      expect(client.calls.filter((call) => call.route === TASKS)).toHaveLength(1);
    });
    await act(() => Promise.resolve());
    expect(within(panel()).queryByRole("list")).toBeNull();
  });

  it("follows once a task the tab already follows, with what the user named it after", async () => {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { key: MARKING, task_id: MARKING, kind: "revision_mark", status: "running", subject: "V2" },
      ]),
    );
    serve({ [TASK]: "task_running" });
    render(shell(<Screen name="Planning" />, true, listed("tasks_running")));
    await tick();
    expect(within(panel()).getAllByRole("listitem")).toHaveLength(1);
    expect(within(panel()).getByRole("listitem")).toHaveTextContent(
      "Marquage d’une révision « V2 »",
    );
  });

  it("does without a list the API refuses, or does not give", async () => {
    const client = serve({ [TASKS]: { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    render(shell(<Screen name="Planning" />, true));
    showTab("visible");
    await vi.waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([TASKS]);
    });
    expect(within(panel()).queryByRole("list")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    server.client = unreachable();
    showTab("visible");
    await tick();
    expect(within(panel()).queryByRole("list")).toBeNull();
  });

  it("asks nothing without a session", async () => {
    const client = serve({});
    render(shell(<Screen name="Planning" />));
    showTab("visible");
    await tick();
    expect(client.calls).toEqual([]);
  });
});
