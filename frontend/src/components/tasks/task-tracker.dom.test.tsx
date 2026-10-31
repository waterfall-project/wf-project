// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { type ReactNode, Suspense } from "react";
import { hydrateRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { markRevision } from "@/api/actions/revisions";
import type { ApiClient } from "@/api/client";
import type { BackgroundTask, Outcome } from "@/api/problem";
import { forgetMessages, readMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
  unreachable,
} from "@/test/fixtures";
import { closeTasks, tasksButton, tasksRegion } from "@/test/task-panel";

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
const MARKING = "01926f3a-7c00-7000-8000-000000000931";
const IMPORT = "01926f3a-7c00-7000-8000-000000000932";
const RELAUNCHED = "01926f3a-7c00-7000-8000-000000000933";
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
 * bar, its panel, the page — and the tasks of the user the root layout streams, if any.
 */
function shell(page: ReactNode, signedIn = false, running?: Promise<readonly BackgroundTask[]>) {
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

/** The tasks the panel lists, apart from the log that repeats their ends. */
function entries() {
  return within(tasksRegion()).getByRole("list");
}

/** The log of the ends of the tasks: outside the panel, or within it while it is open. */
function endLog() {
  return screen.getByRole("log");
}

/** The ends the log reads out, each in its sentences, as they are written: typography included. */
function ends(): (string | null)[][] {
  return [...endLog().children].map((end) =>
    [...end.children].map((sentence) => sentence.textContent),
  );
}

/** The button that dismisses a task, by the name of the task. */
function dismissal(name: string) {
  return within(tasksRegion()).getByRole("button", { name: `Retirer du suivi\u00A0: ${name}` });
}

/** The button that runs a failed task again, by the name of the task. */
function relaunchButton(name = "Marquage d’une révision") {
  return within(tasksRegion()).getByRole("button", { name: `Relancer\u00A0: ${name}` });
}

/** What the progress of the task says next to its bar. */
function progressText(): string | null | undefined {
  return within(tasksRegion()).getByRole("progressbar").nextElementSibling?.textContent;
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
  forgetMessages();
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
    closeTasks();
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
    // The motive names the categories of labour without a rate, as the failed task gives them.
    const motive =
      "Aucun taux horaire n’est défini pour ce rôle et cette année. " +
      "Sans taux horaire\u00A0: «\u00A0Ingénierie électrique\u00A0» en 2026.";
    expect(ends()).toEqual([
      ["Tâche échouée\u00A0: Marquage d’une révision «\u00A0V2\u00A0».", motive],
    ]);
    expect(within(entries()).getByText("Échouée")).toBeVisible();
    expect(within(entries()).getByText(/^Aucun taux horaire .* en 2026\.$/)).toBeVisible();
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
    const bar = within(tasksRegion()).getByRole("progressbar", { name: "Marquage d’une révision" });
    expect(bar).toHaveAttribute("aria-valuenow", "0");
    expect(progressText()).toBe("0\u202F%");
    await expectAccessible(container);

    await tick();
    expect(bar).toHaveAttribute("aria-valuenow", "40");
    expect(progressText()).toBe("40\u202F%");
    expect(within(entries()).getByText("En cours")).toBeVisible();

    await tick();
    expect(within(tasksRegion()).queryByRole("progressbar")).toBeNull();
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision."]]);

    await tick(3);
    expect(reads(client)).toHaveLength(2);
  });

  it("offers to reload the screen once a task has succeeded, never reloads by itself, and closes the panel on the screen read anew", async () => {
    serve({ [TASK]: "task_succeeded" });
    await started(task("task_mark_queued"));
    await tick();
    const reload = within(entries()).getByRole("button", { name: "Recharger l’écran" });
    await tick(2);
    expect(router.refresh).not.toHaveBeenCalled();
    await userEvent.click(reload);
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(tasksButton()).toHaveFocus();
  });

  it("offers no reload of the screen while a task runs, nor once it has failed", async () => {
    serve({ [TASK]: ["task_running", "task_failed"] });
    await started(task("task_mark_queued"));
    await tick();
    expect(within(entries()).queryByRole("button", { name: "Recharger l’écran" })).toBeNull();
    await tick();
    expect(within(entries()).queryByRole("button", { name: "Recharger l’écran" })).toBeNull();
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
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
    await tick(2);
    expect(reads(client)).toEqual([]);
  });

  it("takes the focus from a task dismissed to the next, else the one before, else the region of the tasks", async () => {
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
    // The last one gone, the focus goes to the region of the tasks, outside the order of the
    // keyboard: within the panel, which holds it, never to the document.
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
    expect(tasksRegion()).toHaveFocus();
    expect(tasksRegion()).toHaveAttribute("tabindex", "-1");
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
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
    expect(endLog()).toBeEmptyDOMElement();
  });

  it("says the API is out of reach, and asks again until it answers", async () => {
    server.client = unreachable();
    await started(task("task_mark_queued"));
    await tick();
    expect(within(tasksRegion()).getByRole("alert").textContent).toBe(
      "Le service est injoignable\u202F; réessayez dans un instant.",
    );

    serve({ [TASK]: "task_succeeded" });
    await tick();
    expect(within(tasksRegion()).queryByRole("alert")).toBeNull();
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision."]]);
  });

  it("takes a server action that does not answer at all for the API out of reach", async () => {
    server.client = {
      // The browser could not reach the server of Next: its `fetch` rejected (`rejected`).
      GET: () => Promise.reject(new TypeError("Failed to fetch")),
    } as unknown as ApiClient;
    await started(task("task_mark_queued"));
    await tick();
    expect(within(tasksRegion()).getByRole("alert")).toHaveTextContent(
      "Le service est injoignable",
    );
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
    expect(within(tasksRegion()).queryByRole("progressbar")).toBeNull();
    expect(within(tasksRegion()).queryByRole("alert")).toBeNull();
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

  it.each([
    [
      "session_revoked",
      `/login?next=${encodeURIComponent(`/projects/${PROJECT}/revisions`)}&reauthenticate=1`,
    ],
    ["session_expired", `/login?next=${encodeURIComponent(`/projects/${PROJECT}/revisions`)}`],
  ] as const)(
    "leads a follow-up refused as %s to a sign-in that asks for the identifiers again for a session closed only (#855) [WF-SEC-0020-A]",
    async (name, href) => {
      serve({ [TASK]: { problem: example(name) as Problem & { readonly status: 401 } } });
      await started(task("task_mark_queued"));
      await tick();
      expect(within(entries()).getByRole("link", { name: "Se connecter" })).toHaveAttribute(
        "href",
        href,
      );
    },
  );

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
    expect(within(tasksRegion()).getByRole("alert")).toHaveTextContent(
      "Le service est injoignable",
    );

    serve({ [TASK]: { problem: { code: "NOT_FOUND", status: 404 } } });
    await tick();
    expect(within(entries()).getByText("Suivi interrompu")).toBeVisible();
    expect(within(tasksRegion()).queryByRole("alert")).toBeNull();
  });

  it("tells the refusal of a relaunch, and keeps the failed task to run again", async () => {
    serve({
      [MARK]: { problem: { code: "ALREADY_EXISTS", status: 409 } },
      [TASK]: "task_failed",
    });
    const command = () => markRevision(PROJECT, REVISION, { version_name: "V2", lock_version: 4 });
    await started(task("task_mark_queued"), { command, subject: "V2" });
    await tick();
    const name = "Marquage d’une révision «\u00A0V2\u00A0»";
    await userEvent.click(relaunchButton(name));

    expect(within(tasksRegion()).getByRole("alert")).toHaveTextContent("Cet élément existe déjà.");
    expect(within(entries()).getByText("Échouée")).toBeVisible();
    expect(relaunchButton(name)).toBeVisible();
    // Noted once, about the task, by the follow-up: the panel opened again, its entry notes nothing.
    closeTasks();
    tasksRegion();
    const noted = readMessages().messages.filter(({ sentence }) => sentence.startsWith("Cet élé"));
    expect(noted).toEqual([expect.objectContaining({ tone: "refusal", object: name })]);
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
    expect(within(tasksRegion()).queryByRole("button", { name: /^Relancer/ })).toBeNull();
    expect(dismissal("Marquage d’une révision")).toHaveFocus();
    expect(document.activeElement).not.toBe(document.body);
    expect(
      within(entries()).getByText("Pour relancer cette tâche, repartez de l’écran de son objet."),
    ).toBeVisible();
    expect(client.calls.filter((call) => call.route === MARK)).toHaveLength(1);
    const alert = within(tasksRegion()).getByRole("alert");
    await userEvent.click(within(alert).getByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(within(tasksRegion()).queryByRole("alert")).toBeNull();
    expect(within(entries()).getByText("Échouée")).toBeVisible();
  });

  it("says the API is out of reach when the relaunch does not answer at all", async () => {
    serve({ [TASK]: "task_failed" });
    const command = () => Promise.reject(new TypeError("Failed to fetch"));
    await started(task("task_mark_queued"), { command });
    await tick();
    await userEvent.click(relaunchButton());
    expect(within(tasksRegion()).getByRole("alert")).toHaveTextContent(
      "Le service est injoignable",
    );
  });

  it("offers no relaunch of a failed task handed over without its command", async () => {
    serve({ [TASK]: "task_failed" });
    await started(task("task_mark_queued"));
    await tick();
    expect(within(entries()).getByText("Échouée")).toBeVisible();
    expect(within(tasksRegion()).queryByRole("button", { name: /^Relancer/ })).toBeNull();
  });

  it("is a piece of the shell: a screen outside it cannot hand a task over", () => {
    expect(() => render(<Starting given={task("task_mark_queued")} />)).toThrow(
      "within the TaskTracker of the shell",
    );
  });
});

/** The messages of the history the panel shows, the last first. */
function history(): HTMLElement[] {
  tasksRegion();
  const region = screen.getByRole("region", { name: "Messages" });
  return within(region).queryAllByRole("listitem");
}

/** The screens the tests go to, as the browser shows them. */
const EXCHANGES = `/projects/${PROJECT}/revisions/${REVISION}/exchanges`;
const PLANNING = `/projects/${PROJECT}/revisions/${REVISION}/planning`;

describe("the history of the messages", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", EXCHANGES);
  });

  afterEach(() => {
    window.history.replaceState(null, "", "/");
  });

  it("keeps the end of an import for a user who changed screens, with when, where, and a link back [WF-IHM-0080-A]", async () => {
    // Un utilisateur qui change d'écran pendant un import est informé de son aboutissement.
    serve({ [TASK]: "task_import_succeeded" });
    const view = await started(task("task_import_queued"), { subject: "devis.xlsx" });
    window.history.replaceState(null, "", PLANNING);
    view.rerender(shell(<Screen name="Planning" />));
    await tick();

    const [ended, launched] = history();
    const name = "Application d’un import « devis.xlsx »";
    expect(ended).toHaveTextContent(/^Réussite\s:/);
    expect(ended).toHaveTextContent(`Tâche terminée : ${name}.`);
    expect(ended).toHaveTextContent(`Objet : ${name}.`);
    const back = within(ended ?? document.body).getByRole("link");
    expect(back).toHaveAttribute("href", EXCHANGES);
    expect(back).toHaveTextContent("Imports et exports");
    expect(ended?.querySelector("time")).toHaveAttribute("datetime");
    expect(launched).toHaveTextContent(`Tâche lancée : ${name}.`);
    // The link back to the screen closes the panel.
    await userEvent.click(back);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("keeps the correlation identifier of an import failed by an unexpected error, which its message gives [WF-OBS-0020-A]", async () => {
    // Un import échoué peut être suivi du dépôt du fichier à l'échec de la tâche par un seul
    // identifiant, que le message présenté à l'utilisateur contient. The task handed over has
    // failed already: its end is logged at once.
    const failed: BackgroundTask = {
      ...task("task_import_queued"),
      status: "failed",
      problem: { code: "INTERNAL_ERROR", status: 500, correlation_id: "req-7f3a9c" },
    };
    await started(failed);
    const [ended] = history();
    expect(ended).toHaveTextContent(/^Refus\s:/);
    expect(ended).toHaveTextContent("Tâche échouée : Application d’un import.");
    expect(ended).toHaveTextContent("Erreur inattendue du service.");
    expect(ended).toHaveTextContent("Référence : req-7f3a9c");
  });

  it("counts the refusals not read yet on the button of the panel, until the panel shows them", async () => {
    serve({ [TASK]: "task_failed" });
    await started(task("task_mark_queued"));
    await tick();
    expect(tasksButton()).toHaveAccessibleName(
      "Tâches et messages\u00A0: 1 tâche suivie, 1 refus non lu",
    );
    expect(history()).toHaveLength(2);
    closeTasks();
    expect(tasksButton()).toHaveAccessibleName("Tâches et messages\u00A0: 1 tâche suivie");
  });

  it("counts the API out of reach during the follow-up while the panel stays closed [WF-IHM-0080-A]", async () => {
    server.client = unreachable();
    await started(task("task_mark_queued"));
    await tick();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(tasksButton()).toHaveAccessibleName(
      "Tâches et messages\u00A0: 1 tâche suivie, 1 refus non lu",
    );
  });

  it("notes the API out of reach once for reads refused in a row, every two seconds, and anew after a read answered", async () => {
    const GET = vi.fn(() => Promise.reject(new TypeError("Failed to fetch")));
    server.client = { GET } as unknown as ApiClient;
    await started(task("task_mark_queued"));
    await tick(5);
    // One read every two seconds, never more: the refusals do not hasten the follow-up.
    expect(GET).toHaveBeenCalledTimes(5);
    const outOfReach = "Le service est injoignable\u202F; réessayez dans un instant.";
    const refusals = () =>
      readMessages().messages.flatMap(({ tone, sentence }) =>
        tone === "refusal" ? [sentence] : [],
      );
    expect(refusals()).toEqual([outOfReach]);
    expect(tasksButton()).toHaveAccessibleName(
      "Tâches et messages\u00A0: 1 tâche suivie, 1 refus non lu",
    );

    // A read answered ends the series; out of reach again, a new one begins.
    const client = serve({ [TASK]: "task_running" });
    await tick();
    expect(reads(client)).toHaveLength(1);
    server.client = unreachable();
    await tick(3);
    expect(refusals()).toEqual([outOfReach, outOfReach]);
    expect(tasksButton()).toHaveAccessibleName(
      "Tâches et messages\u00A0: 1 tâche suivie, 2 refus non lus",
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

    expect(within(tasksRegion()).getAllByRole("listitem")).toHaveLength(1);
    expect(within(tasksRegion()).getByRole("listitem")).toHaveTextContent(
      "Marquage d’une révision « V2 »",
    );
    await tick();
    expect(reads(client)).toEqual([`/tasks/${MARKING}`]);
    expect(ends()[0]?.[0]).toBe("Tâche échouée\u00A0: Marquage d’une révision «\u00A0V2\u00A0».");
    // The command did not survive the reload: the entry says where to start it again.
    expect(within(tasksRegion()).queryByRole("button", { name: /^Relancer/ })).toBeNull();
    expect(
      within(entries()).getByText("Pour relancer cette tâche, repartez de l’écran de son objet."),
    ).toBeVisible();
  });

  it("follows nothing again when the storage holds no list", () => {
    window.sessionStorage.setItem(STORAGE_KEY, "{not json");
    const view = render(shell(<Screen name="Planning" />));
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
    view.unmount();
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ key: MARKING }));
    render(shell(<Screen name="Planning" />));
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
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

  it("opens the panel from the button of the bar, which names the number of the tasks followed", async () => {
    serve({ [TASK]: "task_running" });
    render(shell(<Starting given={task("task_mark_queued")} />));
    const button = tasksButton();
    expect(button).toHaveAccessibleName("Tâches et messages");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveAttribute("aria-haspopup", "dialog");
    expect(button.querySelector("svg")).toHaveAttribute("aria-hidden", "true");

    // A task handed over does not open the panel: the line under the bar says it, and the button
    // counts it.
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    expect(button).toHaveAccessibleName("Tâches et messages\u00A0: 1 tâche suivie");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("Tâche lancée : Marquage d’une révision.")).toBeVisible();
    expect(screen.queryByRole("dialog")).toBeNull();

    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(button).toHaveAttribute("aria-controls", screen.getByRole("dialog").id);
    expect(within(entries()).getByText("Marquage d’une révision")).toBeVisible();
    await expectAccessible(document.body);
  });

  it("follows the tasks still, and reads out their ends, with the panel closed", async () => {
    const client = serve({ [TASK]: ["task_running", "task_succeeded"] });
    await started(task("task_mark_queued"));
    expect(tasksButton()).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("dialog")).toBeNull();

    await tick(2);
    expect(reads(client)).toHaveLength(2);
    expect(ends()).toEqual([["Tâche terminée\u00A0: Marquage d’une révision."]]);

    // The line under the bar says the end, on whatever screen; opened, the panel lists the task as
    // it now stands.
    const said = screen
      .getAllByText("Tâche terminée : Marquage d’une révision.")
      .filter((line) => line.closest("[role=log]") === null);
    expect(said).toHaveLength(1);
    expect(said[0]).toBeVisible();
    await userEvent.click(tasksButton());
    expect(within(entries()).getByText("Réussie")).toBeVisible();
  });

  it("holds the focus in the panel, closes it on Escape, and gives the focus back to its button", async () => {
    serve({ [TASK]: "task_running" });
    await started(task("task_mark_queued"));
    await userEvent.click(tasksButton());
    const dialog = screen.getByRole("dialog", { name: "Tâches et messages" });
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    await userEvent.tab();
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(tasksButton()).toHaveFocus();

    // Its close button closes it too.
    await userEvent.click(tasksButton());
    await userEvent.click(screen.getByRole("button", { name: "Fermer les tâches et messages" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(tasksButton()).toHaveFocus();
  });
});

/** The tasks of the user the root layout streams, by the name of their example. */
function listed(name: string): Promise<readonly BackgroundTask[]> {
  return Promise.resolve((example(name) as { readonly items: readonly BackgroundTask[] }).items);
}

/**
 * Render the shell with the tasks the layout streams: React retries what waited for them within
 * an `act` it is given the time of, as the browser would once they come.
 */
async function renderStreamed(ui: ReactNode) {
  await act(async () => {
    render(ui);
    await Promise.resolve();
  });
}

/** The tab hidden, or shown again, as the browser tells it. */
function showTab(state: DocumentVisibilityState) {
  vi.spyOn(document, "visibilityState", "get").mockReturnValue(state);
  act(() => {
    document.dispatchEvent(new Event("visibilitychange"));
  });
}

describe("the tasks of its user the API lists", () => {
  it("follows the tasks of its user the layout streams, started elsewhere, and announces their end, without a server action as it mounts", async () => {
    const client = serve({ [TASK]: "task_failed" });
    await renderStreamed(shell(<Screen name="Planning" />, true, listed("tasks_running")));

    // The marking another tab started, streamed by the layout.
    expect(await within(tasksRegion()).findByRole("listitem")).toHaveTextContent(
      "Marquage d’une révision",
    );
    expect(client.calls).toEqual([]);
    await tick();
    expect(reads(client)).toEqual([`/tasks/${MARKING}`]);
    expect(ends()[0]?.[0]).toBe("Tâche échouée\u00A0: Marquage d’une révision.");
    // The list does not say which command started it: it is run again from its screen.
    expect(within(tasksRegion()).queryByRole("button", { name: /^Relancer/ })).toBeNull();
    expect(
      within(entries()).getByText("Pour relancer cette tâche, repartez de l’écran de son objet."),
    ).toBeVisible();
  });

  it("reads the list again when the tab shows once more, and follows what another tab started", async () => {
    const client = serve({ [TASKS]: "tasks_running", [TASK]: "task_running" });
    await renderStreamed(shell(<Screen name="Planning" />, true, listed("tasks_none")));
    const asked = () => client.calls.filter((call) => call.route === TASKS);
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
    // Hidden, the tab asks nothing; shown again, it asks.
    showTab("hidden");
    expect(asked()).toEqual([]);
    showTab("visible");
    expect(await within(tasksRegion()).findByRole("listitem")).toHaveTextContent(
      "Marquage d’une révision",
    );
    expect(asked().map((call) => call.query.get("status"))).toEqual(["queued,running"]);
  });

  it("brings back no task the user dismissed, when the tab shows again and the list is read anew", async () => {
    const client = serve({ [TASKS]: "tasks_running", [TASK]: "task_running" });
    await renderStreamed(shell(<Screen name="Planning" />, true, listed("tasks_running")));
    await within(tasksRegion()).findByRole("listitem");
    await userEvent.click(dismissal("Marquage d’une révision"));
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
    showTab("visible");
    await vi.waitFor(() => {
      expect(client.calls.filter((call) => call.route === TASKS)).toHaveLength(1);
    });
    await act(() => Promise.resolve());
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
  });

  it("follows once a task the tab already follows, with what the user named it after", async () => {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { key: MARKING, task_id: MARKING, kind: "revision_mark", status: "running", subject: "V2" },
      ]),
    );
    serve({ [TASK]: "task_running" });
    await renderStreamed(shell(<Screen name="Planning" />, true, listed("tasks_running")));
    await tick();
    expect(within(tasksRegion()).getAllByRole("listitem")).toHaveLength(1);
    expect(within(tasksRegion()).getByRole("listitem")).toHaveTextContent(
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
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    server.client = unreachable();
    showTab("visible");
    await tick();
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
  });

  it("renders the page and its panel while the tasks of the user are on their way", async () => {
    serve({ [TASK]: "task_running" });
    let answer: (tasks: readonly BackgroundTask[]) => void = () => undefined;
    const coming = new Promise<readonly BackgroundTask[]>((resolve) => {
      answer = resolve;
    });
    await renderStreamed(shell(<Screen name="Planning" />, true, coming));
    expect(screen.getByRole("heading", { name: "Planning" })).toBeVisible();
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
    await act(async () => {
      answer((example("tasks_running") as { readonly items: readonly BackgroundTask[] }).items);
      await coming;
    });
    expect(await within(tasksRegion()).findByRole("listitem")).toHaveTextContent(
      "Marquage d’une révision",
    );
  });

  it("asks nothing without a session", async () => {
    const client = serve({});
    render(shell(<Screen name="Planning" />));
    showTab("visible");
    await tick();
    expect(client.calls).toEqual([]);
  });
});

/**
 * Hydrate, inside the tracker, a page the server sent but the browser has not revealed yet: its
 * boundary queued, the fallback still in place (`<!--$~-->`), as the document of a screen with a
 * `loading.tsx` stands while React holds back the reveal of what the server streamed — within
 * an element of the shell, where a change of a context above reaches it.
 */
async function hydratePending(running: Promise<readonly BackgroundTask[]>) {
  const container = document.createElement("div");
  container.innerHTML =
    '<div><!--$~--><template id="B:0"></template><p>Chargement</p><!--/$--></div>';
  document.body.append(container);
  let root: Root | undefined;
  await act(async () => {
    root = hydrateRoot(
      container,
      <TaskTracker signedIn running={running}>
        <div>
          <Suspense fallback={<p>Chargement</p>}>
            <Screen name="Avatar" />
          </Suspense>
        </div>
      </TaskTracker>,
    );
    await running;
  });
  await tick();
  return { container, root };
}

describe("the tracker as the page hydrates", () => {
  // #173: a context above the page that changes while its boundary is pending makes React render
  // the page anew in the browser, beside the one the server sent, which the browser still holds.
  it.each([
    ["it has no task to follow", false, false, false],
    ["the tab has tasks to follow again", true, false, false],
    ["the layout streams tasks it did not follow", false, true, false],
    ["the address carries the refusal of a result (#416)", false, false, true],
  ])("leaves the page the server sent to hydrate, when %s", async (_, kept, streamed, refused) => {
    const address = `${window.location.pathname}${window.location.search}`;
    if (refused) {
      window.history.replaceState(
        null,
        "",
        `/projects/${PROJECT}/revisions?refused_task=${MARKING}&refusal=409:STATE_FORBIDS_OPERATION`,
      );
    }
    if (kept) {
      window.sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify([
          { key: MARKING, task_id: MARKING, kind: "revision_mark", status: "running" },
        ]),
      );
    }
    serve({ [TASK]: "task_running" });
    const running = streamed
      ? (example("tasks_running") as { readonly items: readonly BackgroundTask[] }).items
      : [];
    const { container, root } = await hydratePending(Promise.resolve(running));
    try {
      await tick();
      expect(within(container).queryByRole("heading", { name: "Avatar" })).toBeNull();
      expect(container).toHaveTextContent("Chargement");
    } finally {
      window.history.replaceState(null, "", address);
      act(() => {
        root?.unmount();
      });
      container.remove();
    }
  });
});
