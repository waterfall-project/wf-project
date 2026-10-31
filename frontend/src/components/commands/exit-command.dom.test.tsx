// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { refresh } from "next/cache";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import type { Problem } from "@/api/problem";
import type { Project } from "@/components/context/reading";
import { forgetMessages, readMessages } from "@/components/notices/message-history";
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
  type FakeTiming,
} from "@/test/fixtures";
import { closeTasks, tasksRegion } from "@/test/task-panel";

import { LifecycleCommands } from "./object-commands";

// The server of Next, as far as an exit needs it: the fake back behind serverClient, and the
// render of the page again once the exit is applied.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ refresh: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/lifecycle",
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
/** The counter the examples of the projects of the contract carry, which an exit sends back (WF-IHM-0110). */
const LOCK = (example("project") as Project).lock_version;
const EXIT = "POST /projects/{project_id}/exit";
const TASK = "GET /tasks/{task_id}";
/** The exit of the contract that marks the current revision, as the API receives it. */
const MARKING = (example("project_exit_marking") as { current_revision: unknown }).current_revision;
const CONFLICT = {
  problem: {
    code: "STATE_FORBIDS_OPERATION",
    status: 409,
    params: { conflicting_object_id: PROJECT },
  },
} as const;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers, timing?: FakeTiming): FakeClient {
  const client = fakeClient(answers, timing);
  server.client = client;
  return client;
}

/** The exits of a project of the contract, in French. */
function exitsOf(name: string, options: { marking?: boolean } = {}) {
  const project = example(name) as Project;
  if (options.marking) {
    // While a marking runs, no exit is available (WF-CYC-0080): only the offers change.
    project.available_commands = project.available_commands.map((offer) =>
      offer.command === "complete" || offer.command === "abandon"
        ? {
            ...offer,
            is_available: false,
            missing_conditions: ["no_background_task_running" as const],
          }
        : offer,
    );
  }
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>
          <LifecycleCommands project={project} />
        </main>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** Render the exits of a project of the contract. */
function open(name = "project") {
  return render(exitsOf(name));
}

/** The bodies sent to take the project out of its lifecycle. */
function exits(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === EXIT).map((call) => call.body);
}

/** What the live regions of the exits say, the silent ones left out. */
function said(): (string | null)[] {
  return screen
    .queryAllByRole("status")
    .map((status) => status.textContent)
    .filter(Boolean);
}

/** An exit, by its name. */
function exit(name: string) {
  return screen.getByRole("button", { name });
}

/** The refusal of an example of the contract, as the fake back answers it. */
function refused<S extends 409 | 422>(name: string, status: S) {
  return { problem: { ...(example(name) as Problem), status } };
}

/** Choose the fate of the current revision in the open confirmation: abandoned, or marked. */
async function choose(fate: "abandon" | "mark") {
  await userEvent.click(
    screen.getByRole("radio", {
      name: fate === "mark" ? /^Marquer la révision en cours/ : /^Abandonner la révision en cours/,
    }),
  );
}

/** Mark the revision under the name and the description of the exit of the contract. */
async function chooseMarking() {
  const { version_name: name, description } = MARKING as {
    version_name: string;
    description: string;
  };
  await choose("mark");
  await userEvent.type(screen.getByRole("textbox", { name: "Nom de version" }), name);
  await userEvent.type(
    screen.getByRole("textbox", { name: "Description (facultative)" }),
    description,
  );
}

/** Open the confirmation of an exit, abandon the current revision if the project carries one, confirm. */
async function confirm(name: string, options: { revision?: boolean } = {}) {
  await userEvent.click(exit(name));
  if (options.revision ?? true) {
    await choose("abandon");
  }
  await userEvent.click(screen.getByRole("button", { name: "Confirmer la sortie" }));
}

/**
 * The fake back for an exit that marks: it answers the exit with the task of the contract (202)
 * and reads of that task the examples of the contract, running then succeeded, under the
 * identifier the exit's task bears — the contract has no running or succeeded example for it, only
 * for the marking's own. It gives back the bodies of the exits it received.
 */
function serveMarking(): unknown[] {
  const queued = example("task_exit_mark_queued") as { task_id: string };
  const reads = ["task_running", "task_succeeded"].map((name) => ({
    ...(example(name) as object),
    task_id: queued.task_id,
  }));
  const sent: unknown[] = [];
  const answer = async (request: Request): Promise<Response> => {
    if (request.method === "POST") {
      sent.push(await request.json());
      return Response.json(queued, { status: 202 });
    }
    return Response.json(reads.length > 1 ? reads.shift() : reads[0]);
  };
  server.client = createApiClient({ address: "http://fake.invalid", fetch: answer });
  return sent;
}

/** Let the time of one read of the task go by, and the read be answered. */
async function tick() {
  await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
}

beforeEach(() => {
  vi.mocked(refresh).mockClear();
  router.refresh.mockClear();
  server.client = undefined;
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the exits of the lifecycle of a project", () => {
  it("offers the exits alone, in the order of the server: no command to create or modify, and no loss from a project in progress [WF-CYC-0060]", () => {
    // Déclarer perdu n'est possible que depuis Chiffrage : un projet en cours n'offre que Terminer
    // et Abandonner.
    open();
    const region = screen.getByRole("region", { name: "Commandes" });
    expect(
      within(region)
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual(["Terminer le projet", "Abandonner le projet"]);
    expect(within(region).queryByRole("button", { name: "Déclarer le projet perdu" })).toBeNull();
  });

  it("on a project in pricing, presents completion unavailable, naming the condition it lacks [WF-IHM-0090-A]", async () => {
    // Sur un projet en chiffrage, la commande de terminaison est présentée indisponible en
    // nommant la condition manquante.
    const client = serve({});
    const { container } = open("project_pricing");
    const complete = exit("Terminer le projet");
    expect(complete).toHaveAttribute("aria-disabled", "true");
    expect(complete).toHaveAccessibleDescription("Condition non remplie\u00A0: projet en cours.");
    // Pressed, it opens nothing and asks nothing.
    await userEvent.click(complete);
    expect(screen.queryByRole("form")).toBeNull();
    expect(exits(client)).toEqual([]);
    await expectAccessible(container);
  });

  it("confirms an exit before it is applied, naming the state it leads to and that the project becomes read only [WF-IHM-0110-A]", async () => {
    forgetMessages();
    const client = serve({ [EXIT]: "project_completed" });
    const { container } = open();
    const complete = exit("Terminer le projet");
    await userEvent.click(complete);
    expect(complete).toHaveAttribute("aria-expanded", "true");

    const form = screen.getByRole("form", { name: "Terminer le projet" });
    // What the user reads, the no-break spaces of French typography aside.
    expect(form.textContent.replaceAll(" ", " ")).toContain(
      "Cette sortie est définitive : le projet passera à l’état « Terminé », et lui comme toutes ses données",
    );
    // A screen reader hears it too, on the field of the motive and on the button that confirms.
    const reason = within(form).getByRole("textbox", { name: "Motif (facultatif)" });
    const confirmation = within(form).getByRole("button", { name: "Confirmer la sortie" });
    for (const described of [reason, confirmation]) {
      expect(described).toHaveAccessibleDescription(/définitive.*Terminé.*lecture seule/);
    }
    // Nothing is asked of the API before the user confirms.
    expect(exits(client)).toEqual([]);
    expect(reason).toHaveFocus();
    await expectAccessible(container);

    await userEvent.type(reason, "Recette prononcée");
    await choose("abandon");
    await userEvent.click(confirmation);

    expect(client.calls.find((call) => call.route === EXIT)?.path).toBe(
      `/projects/${PROJECT}/exit`,
    );
    expect(exits(client)).toEqual([
      {
        to_state: "completed",
        confirmed: true,
        lock_version: LOCK,
        reason: "Recette prononcée",
        current_revision: { action: "abandon" },
      },
    ]);
    // The page is rendered again, the confirmation closes, and the new state is said.
    await waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
      expect(screen.queryByRole("form")).toBeNull();
    });
    expect(complete).toHaveFocus();
    expect(said()).toEqual(["Le projet est passé à l’état «\u00A0Terminé\u00A0»."]);
    // Kept in the history of the messages, about the project it exited (#1043).
    expect(readMessages().messages).toEqual([
      expect.objectContaining({
        tone: "success",
        sentence: "Le projet est passé à l’état «\u00A0Terminé\u00A0».",
        object: (example("project") as Project).label,
      }),
    ]);
  });

  it("lists no exit once the page is read again, the project completed, the new state kept in the history of the messages [WF-CYC-0060]", async () => {
    // A closed project lists no exit: none will become possible (Vérif de WF-CYC-0060).
    forgetMessages();
    serve({ [EXIT]: "project_completed" });
    const view = open();
    await confirm("Terminer le projet");
    view.rerender(exitsOf("project_completed"));
    expect(screen.queryByRole("button", { name: "Terminer le projet" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Abandonner le projet" })).toBeNull();
    expect(readMessages().messages).toEqual([
      expect.objectContaining({
        sentence: "Le projet est passé à l’état «\u00A0Terminé\u00A0».",
      }),
    ]);
  });

  it("asks what becomes of the current revision, only when the project carries one [WF-CYC-0090-A]", async () => {
    // Avec une révision en cours, la confirmation demande de la marquer, avec un nom de version,
    // ou de l'abandonner ; sans, elle se tait.
    const view = open();
    await userEvent.click(exit("Terminer le projet"));
    const form = screen.getByRole("form", { name: "Terminer le projet" });
    const fate = within(form).getByRole("group", { name: "Sort de la révision en cours" });
    expect(within(fate).getAllByRole("radio")).toHaveLength(2);
    // Nothing chosen for the user, and the version name asked only when marking.
    expect(within(fate).queryByRole("radio", { checked: true })).toBeNull();
    expect(within(form).queryByRole("textbox", { name: "Nom de version" })).toBeNull();
    await choose("mark");
    expect(within(form).getByRole("textbox", { name: "Nom de version" })).toBeVisible();
    expect(within(form).getByRole("textbox", { name: "Description (facultative)" })).toBeVisible();
    await choose("abandon");
    expect(within(form).queryByRole("textbox", { name: "Nom de version" })).toBeNull();
    expect(form).toHaveTextContent("elle sera supprimée, sans retour possible");
    view.unmount();
    open("project_without_current_revision");
    await userEvent.click(exit("Terminer le projet"));
    const bare = screen.getByRole("form", { name: "Terminer le projet" });
    expect(within(bare).queryByRole("group")).toBeNull();
    expect(bare).not.toHaveTextContent("révision");
  });

  it("marks the current revision under the version name given, and follows the task of the marking until the exit applies [WF-CYC-0090-A] [WF-REV-0020] [WF-IHM-0080]", async () => {
    // La sortie qui marque rend 202 et la tâche ; elle s'applique à la réussite de la tâche.
    forgetMessages();
    const sent = serveMarking();
    open();
    await userEvent.click(exit("Terminer le projet"));
    await chooseMarking();
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la sortie" }));

    await waitFor(() => {
      expect(screen.queryByRole("form")).toBeNull();
    });
    expect(sent).toEqual([
      { to_state: "completed", confirmed: true, lock_version: LOCK, current_revision: MARKING },
    ]);
    // The task is followed by the tracker as a marking; nothing is applied yet: the page is not
    // read again, and no state is told.
    expect(refresh).not.toHaveBeenCalled();
    expect(router.refresh).not.toHaveBeenCalled();
    expect(said()).toEqual([]);
    await tick();
    expect(
      within(tasksRegion()).getByRole("progressbar", {
        name: "Marquage d’une révision «\u00A0Clôture\u00A0»",
      }),
    ).toBeVisible();
    expect(router.refresh).not.toHaveBeenCalled();

    closeTasks();
    // The task succeeded: the exit applies, the project is read again, the new state is told.
    await tick();
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalledOnce();
    });
    await waitFor(() => {
      expect(said()).toEqual(["Le projet est passé à l’état «\u00A0Terminé\u00A0»."]);
    });
  });

  it("applies nothing when the task of the marking fails, and runs the same exit again from the tracker [WF-IHM-0080] [WF-CYC-0090-A]", async () => {
    const client = serve({
      [EXIT]: { example: "task_exit_mark_queued", status: 202 },
      [TASK]: "task_failed",
    });
    open();
    await userEvent.click(exit("Terminer le projet"));
    await chooseMarking();
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la sortie" }));
    await waitFor(() => {
      expect(screen.queryByRole("form")).toBeNull();
    });
    await tick();
    expect(router.refresh).not.toHaveBeenCalled();
    expect(said()).toEqual([]);
    const relaunch = within(tasksRegion()).getByRole("button", { name: /^Relancer/ });
    await userEvent.click(relaunch);
    // The same exit, the same body, is sent again.
    await waitFor(() => {
      expect(exits(client)).toHaveLength(2);
    });
    expect(exits(client)[1]).toEqual(exits(client)[0]);
  });

  it("sends the abandon of the current revision, and the exit answers the project at once [WF-CYC-0090-A] [WF-REV-0010]", async () => {
    const client = serve({ [EXIT]: "project_completed" });
    open();
    await confirm("Abandonner le projet");
    expect(exits(client)).toEqual([
      {
        to_state: "abandoned",
        confirmed: true,
        lock_version: LOCK,
        current_revision: { action: "abandon" },
      },
    ]);
    await waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(within(tasksRegion()).queryByRole("list")).toBeNull();
  });

  it.each([
    ["the version name missing", refused("project_exit_version_name_required", 422)],
    ["the version name taken", refused("project_exit_version_name_taken", 409)],
    ["the fate missing", refused("project_exit_revision_required", 422)],
    ["the counter stale", { problem: { code: "STALE_LOCK_VERSION", status: 412 } } as const],
  ])(
    "tells under the confirmation an exit refused for %s, which stays open and follows no task [WF-CYC-0090-A]",
    async (_, refusal) => {
      serve({ [EXIT]: refusal });
      open();
      await userEvent.click(exit("Terminer le projet"));
      await choose("mark");
      await userEvent.click(screen.getByRole("button", { name: "Confirmer la sortie" }));
      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(/\S/);
      expect(screen.getByRole("form", { name: "Terminer le projet" })).toBeInTheDocument();
      expect(within(tasksRegion()).queryByRole("list")).toBeNull();
      expect(router.refresh).not.toHaveBeenCalled();
    },
  );

  it("sends no current revision when the project carries none [WF-CYC-0090-A]", async () => {
    const client = serve({ [EXIT]: "project_completed" });
    open("project_without_current_revision");
    await confirm("Terminer le projet", { revision: false });
    expect(exits(client)).toEqual([
      {
        to_state: "completed",
        confirmed: true,
        lock_version: (example("project_without_current_revision") as Project).lock_version,
      },
    ]);
  });

  it("sends no motive when the user gives none [WF-IHM-0110-A]", async () => {
    const client = serve({ [EXIT]: "project_completed" });
    open();
    await userEvent.click(exit("Abandonner le projet"));
    await userEvent.type(screen.getByRole("textbox", { name: "Motif (facultatif)" }), "   ");
    await choose("abandon");
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la sortie" }));
    expect(exits(client)).toEqual([
      {
        to_state: "abandoned",
        confirmed: true,
        lock_version: LOCK,
        current_revision: { action: "abandon" },
      },
    ]);
  });

  it("opens one confirmation at a time", async () => {
    serve({});
    open();
    await userEvent.click(exit("Terminer le projet"));
    await userEvent.click(exit("Abandonner le projet"));
    expect(screen.getAllByRole("form").map((form) => form.getAttribute("aria-label"))).toEqual([
      "Abandonner le projet",
    ]);
    expect(exit("Terminer le projet")).toHaveAttribute("aria-expanded", "false");
    expect(exit("Abandonner le projet")).toHaveAttribute("aria-expanded", "true");
  });

  it("reads the page again on a refusal for the state of the project, and no longer offers what the server refused, the focus back on the command", async () => {
    const client = serve({ [EXIT]: CONFLICT });
    const view = open();
    await confirm("Terminer le projet");
    expect(exits(client)).toHaveLength(1);
    // The refusal is told once the server has answered: the page is read again, and the alert names
    // the project the state of which forbids the exit.
    await waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
      expect(screen.getByRole("alert")).toHaveTextContent("Modernisation du poste de commande");
    });
    for (const status of screen.getAllByRole("status")) {
      expect(status).toBeEmptyDOMElement();
    }

    // The page read again: a marking is running, so the two exits of the project stay listed but
    // name `no_background_task_running`. The confirmation closes by an effect (`withdrawn` ->
    // `onClose`), a commit later: waited for, not assumed (one failure under a load of 7, #315).
    view.rerender(exitsOf("project", { marking: true }));
    await waitFor(() => {
      expect(screen.queryByRole("form")).toBeNull();
    });
    const complete = exit("Terminer le projet");
    expect(complete).toHaveAttribute("aria-disabled", "true");
    expect(complete).toHaveAttribute("aria-expanded", "false");
    expect(complete).toHaveFocus();
    // The alert of the refusal is the one of the exit the user confirmed, and it stays.
    expect(screen.getByRole("alert")).toHaveTextContent("Modernisation du poste de commande");
  });

  it("keeps the confirmation while the API is asked, and says its refusal once it answers", async () => {
    let answer: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      answer = resolve;
    });
    serve({ [EXIT]: CONFLICT }, { hold: () => held });
    open();
    await confirm("Terminer le projet");
    const cancel = screen.getByRole("button", { name: "Annuler" });
    expect(cancel).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(cancel);
    expect(screen.getByRole("form", { name: "Terminer le projet" })).toBeInTheDocument();

    // Cancel is offered again in the commit that tells the refusal, never a commit after it, while
    // the confirmation would hold it still (#1484).
    const heldWhenTold = atCommit(
      document.body,
      () => screen.queryByRole("alert") !== null,
      () => screen.getByRole("button", { name: "Annuler" }).getAttribute("aria-disabled"),
    );
    // Let go outside `act`, which would render both commits at once: as the browser gets the answer.
    answer();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Modernisation du poste de commande",
    );
    expect(heldWhenTold.stop()).toEqual([null]);
  });

  it("says the permission the API finds missing, and reads nothing again", async () => {
    serve({
      [EXIT]: {
        problem: {
          code: "PERMISSION_MISSING",
          status: 403,
          params: { missing_permission: "project_exit" },
        },
      },
    });
    open();
    await confirm("Abandonner le projet");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Vous n’avez pas la permission nécessaire.",
    );
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says the API out of reach, and the screen stays", async () => {
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    open();
    await confirm("Abandonner le projet");
    expect(screen.getByRole("alert")).toHaveTextContent("Le service est injoignable");
    expect(screen.getByRole("form", { name: "Abandonner le projet" })).toBeInTheDocument();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("closes without asking anything when cancelled, the focus back on the command", async () => {
    const client = serve({});
    open();
    const abandon = exit("Abandonner le projet");
    await userEvent.click(abandon);
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("form")).toBeNull();
    expect(abandon).toHaveFocus();
    expect(abandon).toHaveAttribute("aria-expanded", "false");
    expect(exits(client)).toEqual([]);
  });
});
