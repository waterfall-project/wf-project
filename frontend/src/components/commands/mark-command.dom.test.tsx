// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { Revision } from "@/components/context/read-only";
import { AccountMenu } from "@/components/shell/account-menu";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { atCommit } from "@/test/committed";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  held,
  refusedConnection,
} from "@/test/fixtures";
import { holdReading, Reading, releaseReading } from "@/test/held-reading";
import { closeTasks, tasksRegion } from "@/test/task-panel";

import { RevisionCommands } from "./object-commands";
import type { ProjectContext } from "@/navigation/context";

// The server of Next, as far as the marking needs it: the fake back behind serverClient.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
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
const CONTEXT: ProjectContext = {
  projectId: PROJECT,
  revisionId: REVISION,
  revisionInPath: true,
  parameters: new URLSearchParams(),
};
const MARK = "POST /projects/{project_id}/revisions/{revision_id}/mark";
const TASK = "GET /tasks/{task_id}";
const PREFERENCES = "PATCH /me/preferences";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/**
 * The commands of a revision of the contract, within the shell that follows the tasks, beside
 * what else the screen offers.
 */
function open(name = "revision", beside?: ReactNode) {
  return render(<Reading>{revisionCommands(name, beside)}</Reading>);
}

/** What `open` renders, within the reading the tests may hold (`held-reading.tsx`). */
function revisionCommands(name: string, beside?: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>
          {beside}
          <RevisionCommands revision={example(name) as Revision} context={CONTEXT} />
        </main>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** The command of marking. */
function markCommand() {
  return screen.getByRole("button", { name: "Marquer la révision" });
}

/** Open the entry of the version name, type one, and mark. */
async function mark(versionName: string) {
  await userEvent.click(markCommand());
  if (versionName !== "") {
    await userEvent.type(screen.getByRole("textbox", { name: "Nom de version" }), versionName);
  }
  await userEvent.click(screen.getByRole("button", { name: /^Marquer$/ }));
}

/** Let the time of one read of the task go by, and the read be answered. */
async function tick() {
  await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
}

/** The bodies sent to mark the revision. */
function marks(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === MARK).map((call) => call.body);
}

beforeEach(() => {
  router.refresh.mockClear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the marking of a revision", () => {
  it("leaves the screen usable while a revision is marked, and presents its progress [WF-IHM-0080-A]", async () => {
    // Le marquage d'une révision de dix mille objets laisse l'écran utilisable et présente son
    // avancement. Ten thousand objects mean nothing to the fake back, which answers the
    // example at once: their weight is the worker's. What the screen does of it is the same
    // whatever their number — the hand back as soon as the task is queued, and the progress
    // the API reports as it reads, running then succeeded.
    const client = serve({
      [MARK]: { example: "task_mark_queued", status: 202 },
      [TASK]: ["task_running", "task_succeeded"],
      [PREFERENCES]: "preferences",
    });
    const user = example("me") as components["schemas"]["UserSelf"];
    open("revision", <AccountMenu account={user} language="default" theme="default" />);

    await mark("V2");
    expect(client.calls.find((call) => call.route === MARK)?.path).toBe(
      `/projects/${PROJECT}/revisions/${REVISION}/mark`,
    );
    expect(marks(client)).toEqual([{ version_name: "V2", lock_version: 4 }]);
    // The hand is back at once: the form has closed, the focus is on the command again.
    expect(screen.queryByRole("form", { name: "Marquer la révision" })).toBeNull();
    expect(markCommand()).toHaveFocus();

    const tasks = tasksRegion();
    await tick();
    const progress = within(tasks).getByRole("progressbar", {
      name: "Marquage d’une révision «\u00A0V2\u00A0»",
    });
    expect(progress).toHaveAttribute("aria-valuenow", "40");
    expect(within(tasks).getByText("En cours")).toBeVisible();

    // While the task runs, nothing of the screen is withheld — the panel read closed again —: no
    // dialog, nothing inert or disabled, and the user goes on — here, choosing the language of
    // the interface and applying it, which the server records while the revision is marked.
    closeTasks();
    expect(document.querySelector("[aria-modal], [inert], :disabled")).toBeNull();
    const account = screen.getByRole("button", { name: "Compte de Camille Martin, CM" });
    await userEvent.click(account);
    await userEvent.click(screen.getByRole("menuitem", { name: /^Langue/ }));
    await userEvent.click(await screen.findByRole("menuitemradio", { name: "English" }));
    await waitFor(() => {
      expect(account).toHaveFocus();
    });
    expect(
      client.calls.filter((call) => call.route === PREFERENCES).map((call) => call.body),
    ).toEqual([{ language: "en" }]);
    expect(within(tasksRegion()).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "40");

    await tick();
    expect(screen.getByRole("log").textContent).toBe(
      "Tâche terminée\u00A0: Marquage d’une révision «\u00A0V2\u00A0».",
    );
    expect(within(tasksRegion()).queryByRole("progressbar")).toBeNull();
    expect(client.calls.filter((call) => call.route === TASK)).toHaveLength(2);
  });

  it("keeps the marking pressed inert and saying it waits, until its request then its task have answered, a second press running nothing [WF-IHM-0080-A]", async () => {
    // Le marquage d'une révision de dix mille objets laisse l'écran utilisable et présente son
    // avancement : the button pressed says the marking is under way, where it was pressed (#3103).
    const answer = held();
    const { until } = answer;
    const client = fakeClient(
      {
        [MARK]: { example: "task_mark_queued", status: 202 },
        [TASK]: ["task_running", "task_succeeded"],
      },
      { hold: (route) => (route === MARK ? until : undefined) },
    );
    server.client = client;
    open();
    await userEvent.click(markCommand());
    await userEvent.type(screen.getByRole("textbox", { name: "Nom de version" }), "V2");
    const submit = screen.getByRole("button", { name: /^Marquer$/ });
    await userEvent.click(submit);
    // The request under way: the button keeps its name, says it waits, and runs nothing more.
    expect(submit).toHaveAttribute("aria-busy", "true");
    expect(submit).toHaveAttribute("aria-disabled", "true");
    expect(submit.querySelector("[data-waiting]")).not.toBeNull();
    await userEvent.click(submit);
    expect(marks(client)).toHaveLength(1);

    await act(async () => {
      answer.release();
      await until;
    });
    // The task handed over runs: the command waits for it, and opens nothing.
    const command = markCommand();
    await waitFor(() => {
      expect(command).toHaveAttribute("aria-busy", "true");
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command.querySelector("[data-waiting]")).not.toBeNull();
    await userEvent.click(command);
    expect(screen.queryByRole("form")).toBeNull();
    await tick();
    expect(command).toHaveAttribute("aria-busy", "true");

    // Ended: the command is given back, and the screen of the revisions is read anew, once.
    await tick();
    expect(command).toHaveAttribute("aria-busy", "false");
    expect(command).not.toHaveAttribute("aria-disabled");
    expect(command.querySelector("[data-waiting]")).toBeNull();
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(marks(client)).toHaveLength(1);
  });

  it("gives the marking back to the screen that pressed it once its task has failed, and the same marking runs again [WF-IHM-0080-A]", async () => {
    // L'échec d'un traitement de fond est signalé avec son motif, et le même traitement peut être
    // relancé : the failure gives the button back to the screen that started it.
    const client = serve({
      [MARK]: { example: "task_mark_queued", status: 202 },
      [TASK]: ["task_running", "task_failed"],
    });
    open();
    await mark("V2");
    await tick();
    expect(markCommand()).toHaveAttribute("aria-busy", "true");
    await tick();
    expect(within(tasksRegion()).getByText("Échouée")).toBeVisible();
    closeTasks();
    expect(markCommand()).toHaveAttribute("aria-busy", "false");
    expect(markCommand()).not.toHaveAttribute("aria-disabled");
    await mark("V2");
    expect(marks(client)).toEqual([
      { version_name: "V2", lock_version: 4 },
      { version_name: "V2", lock_version: 4 },
    ]);
  });

  it("opens the entry of the version name, which takes the focus, and closes it again", async () => {
    serve({});
    const { container } = open();
    const command = markCommand();
    expect(command).toHaveAttribute("aria-expanded", "false");
    expect(command).not.toHaveAttribute("aria-controls");

    await userEvent.click(command);
    const form = screen.getByRole("form", { name: "Marquer la révision" });
    expect(command).toHaveAttribute("aria-expanded", "true");
    expect(command).toHaveAttribute("aria-controls", form.id);
    expect(within(form).getByRole("textbox", { name: "Nom de version" })).toHaveFocus();
    await expectAccessible(container);

    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("form")).toBeNull();
    expect(command).toHaveFocus();

    await userEvent.click(command);
    await userEvent.click(command);
    expect(screen.queryByRole("form")).toBeNull();
  });

  it("requires the version name, and asks nothing of the API without one", async () => {
    const client = serve({});
    open();
    await mark("");
    const field = screen.getByRole("textbox", { name: "Nom de version" });
    expect(screen.getByRole("alert").textContent).toBe("Le nom de version est obligatoire.");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAccessibleDescription("Le nom de version est obligatoire.");
    expect(field).toHaveFocus();

    // Spaces are no name either; typing takes the notice away.
    await userEvent.type(field, "   ");
    expect(screen.queryByRole("alert")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: /^Marquer$/ }));
    expect(screen.getByRole("alert")).toBeVisible();
    expect(client.calls).toEqual([]);
  });

  it("sends the description the user joins to the marking", async () => {
    const client = serve({
      [MARK]: { example: "task_mark_queued", status: 202 },
      [TASK]: "task_running",
    });
    open();
    await userEvent.click(markCommand());
    await userEvent.type(screen.getByRole("textbox", { name: "Nom de version" }), "V2");
    await userEvent.type(
      screen.getByRole("textbox", { name: "Description (facultative)" }),
      "Taux 2026",
    );
    await userEvent.click(screen.getByRole("button", { name: /^Marquer$/ }));
    expect(marks(client)).toEqual([
      { version_name: "V2", lock_version: 4, description: "Taux 2026" },
    ]);
  });

  it("tells a version name already taken, and follows no task", async () => {
    // The name is held by the reference, a marked revision the form does not name.
    serve({
      [MARK]: {
        problem: {
          code: "ALREADY_EXISTS",
          status: 409,
          fields: [
            {
              pointer: "/version_name",
              code: "ALREADY_EXISTS",
              params: { conflicting_object_id: "01926f3a-7c00-7000-8000-000000000101" },
            },
          ],
        },
      },
    });
    open();
    // Whether the entry was still busy in the commit that told the refusal: the request over, never
    // while it holds a press (#1484).
    const busyWhenTold = atCommit(
      document.body,
      () => screen.queryByRole("alert") !== null,
      () => screen.getByRole("form", { name: "Marquer la révision" }).getAttribute("aria-busy"),
    );
    await mark("V1");
    const form = screen.getByRole("form", { name: "Marquer la révision" });
    expect((await within(form).findByRole("alert")).textContent).toBe("Cet élément existe déjà.");
    expect(busyWhenTold.stop()).toEqual(["false"]);
    const tasks = tasksRegion();
    expect(within(tasks).queryByRole("list")).toBeNull();
  });

  it("offers to reload a revision changed since it was read, and reloads it", async () => {
    serve({ [MARK]: { problem: { code: "STALE_LOCK_VERSION", status: 412 } } });
    open();
    await mark("V2");
    const alert = within(screen.getByRole("form", { name: "Marquer la révision" })).getByRole(
      "alert",
    );
    await userEvent.click(within(alert).getByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("says the API is out of reach, and keeps the name typed", async () => {
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(refusedConnection()),
    });
    open();
    await mark("V2");
    expect(screen.getByRole("alert").textContent).toBe(
      "Le service est injoignable\u202F; réessayez dans un instant.",
    );
    expect(screen.getByRole("textbox", { name: "Nom de version" })).toHaveValue("V2");
  });

  it("holds its command too, until the page has been read anew after a marking whose connection was lost once sent, so that the entry closed cannot open again before (US-2240)", async () => {
    const lost = new TypeError("fetch failed", {
      cause: Object.assign(new Error("other side closed"), { code: "UND_ERR_SOCKET" }),
    });
    const send = vi.fn(() => Promise.reject(lost));
    server.client = createApiClient({ address: "http://localhost:4010", fetch: send });
    holdReading(router.refresh);
    open();
    await mark("V2");
    expect(await screen.findByRole("alert")).toHaveTextContent("l’opération a pu aboutir");
    expect(router.refresh).toHaveBeenCalledOnce();
    const submit = screen.getByRole("button", { name: /^Marquer$/ });
    expect(submit).toHaveAttribute("aria-disabled", "true");
    // The command waits as the entry does: pressed, it neither closes nor opens anything.
    expect(markCommand()).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(markCommand());
    expect(markCommand()).toHaveAttribute("aria-expanded", "true");

    // The entry closed by Cancel while the page is read anew: the command stays held, opens
    // nothing, and the notice that the marking may have been done stays told (#3443).
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Annuler" }));
      await Promise.resolve();
    });
    expect(screen.queryByRole("form")).toBeNull();
    expect(markCommand()).toHaveAttribute("aria-expanded", "false");
    expect(markCommand()).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("l’opération a pu aboutir");
    await userEvent.click(markCommand());
    expect(screen.queryByRole("form")).toBeNull();
    expect(markCommand()).toHaveAttribute("aria-expanded", "false");

    await act(async () => {
      releaseReading();
      await Promise.resolve();
    });
    expect(markCommand()).not.toHaveAttribute("aria-disabled");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(send).toHaveBeenCalledOnce();
    // Given back, the command opens the entry again.
    await userEvent.click(markCommand());
    expect(markCommand()).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("form")).toBeVisible();
  });

  it("opens nothing on a marked revision, where the marking is unavailable", async () => {
    serve({});
    open("revision_marked");
    const command = markCommand();
    expect(command).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(command);
    expect(command).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("form")).toBeNull();
  });
});
