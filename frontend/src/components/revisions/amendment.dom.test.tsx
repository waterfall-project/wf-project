// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { findOffer } from "@/components/commands/offer";
import { RevisionCommands } from "@/components/commands/object-commands";
import type { Revision } from "@/components/context/read-only";
import { forgetMessages } from "@/components/notices/message-history";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { closeTasks, tasksRegion } from "@/test/task-panel";

import { MergeAmendmentCommand } from "./merge-amendment-command";

// The server of Next, as far as these commands need it: the fake back behind serverClient, the
// render of the page again once a write is answered, and the router that leads the screen.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ refresh: vi.fn(), push: vi.fn(), replace: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions",
  useSearchParams: () => new URLSearchParams(),
}));

type Problem = components["schemas"]["Problem"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const AMENDMENT = "01926f3a-7c00-7000-8000-000000000213";
const CREATE = "POST /projects/{project_id}/revisions/{revision_id}/structures";
const REPORT = "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge";
const MERGE = "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge";
const TASK = "GET /tasks/{task_id}";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The revision of the contract, in the shell that follows the tasks, with what is beside it. */
function shell(children: React.ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>{children}</main>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

function open(children: React.ReactNode) {
  return render(shell(children));
}

/** The merge of the amendment 2, as the revision lists it. */
function merging(merged = false, name = "revision") {
  const revision = example(name) as Revision;
  return (
    <MergeAmendmentCommand
      offer={findOffer(revision.available_commands, "merge_structure")}
      amendment={{
        projectId: PROJECT,
        revisionId: REVISION,
        structureId: AMENDMENT,
        label: "Avenant 2 — reprise des essais",
      }}
      merged={merged}
      names={{}}
    />
  );
}

/** Open the merge: the command pressed, the report read. */
async function openMerge() {
  await userEvent.click(screen.getByRole("button", { name: "Contractualiser l’avenant" }));
  return screen.findByRole("form", { name: "Contractualiser l’avenant" });
}

/** The calls of a route, their bodies. */
function bodies(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}

/** Let the time of one read of the task go by. */
async function tick() {
  await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
}

beforeEach(() => {
  router.refresh.mockClear();
  router.push.mockClear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
  forgetMessages();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the preparation of an amendment", () => {
  it("is offered as the revision lists it, asks a label, creates the differential and opens it in the grid of the planning", async () => {
    const client = serve({ [CREATE]: { example: "amendment_created", status: 201 } });
    open(<RevisionCommands revision={example("revision") as Revision} />);
    await userEvent.click(screen.getByRole("button", { name: "Préparer un avenant" }));
    const form = screen.getByRole("form", { name: "Préparer un avenant" });
    // The label is asked: nothing is sent without one.
    await userEvent.click(within(form).getByRole("button", { name: "Créer l’avenant" }));
    expect(bodies(client, CREATE)).toEqual([]);

    await userEvent.type(
      within(form).getByRole("textbox", { name: "Libellé de l’avenant" }),
      "Avenant 3",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer l’avenant" }));
    expect(bodies(client, CREATE)).toEqual([{ kind: "amendment", label: "Avenant 3" }]);
    expect(router.push).toHaveBeenCalledWith(
      `/projects/${PROJECT}/revisions/${REVISION}/planning?structure=${AMENDMENT}`,
    );
  });

  it("is unavailable on a revision marked, naming its condition, and sends nothing", async () => {
    const client = serve({});
    open(<RevisionCommands revision={example("revision_marked") as Revision} />);
    const command = screen.getByRole("button", { name: "Préparer un avenant" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(command);
    expect(screen.queryByRole("form")).toBeNull();
    expect(client.calls).toEqual([]);
  });

  it("tells the refusal of a revision no longer the current one, keeps the form and its label, and leads nowhere", async () => {
    const client = serve({
      [CREATE]: {
        problem: {
          code: "STATE_FORBIDS_OPERATION",
          status: 409 as const,
          params: { missing_condition: "revision_current" },
        },
      },
    });
    open(<RevisionCommands revision={example("revision") as Revision} />);
    await userEvent.click(screen.getByRole("button", { name: "Préparer un avenant" }));
    const form = screen.getByRole("form", { name: "Préparer un avenant" });
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Libellé de l’avenant" }),
      "Avenant 3",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer l’avenant" }));
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(bodies(client, CREATE)).toHaveLength(1);
    expect(screen.getByRole("form", { name: "Préparer un avenant" })).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Libellé de l’avenant" })).toHaveValue("Avenant 3");
    expect(router.push).not.toHaveBeenCalled();
  });
});

describe("the contractualisation of an amendment", () => {
  it("presents the report with the marks, asks the version name, and confirms with the two counters read [WF-REV-0050-A]", async () => {
    // La fusion demande un nom de version, et la révision produite le porte.
    const client = serve({
      [REPORT]: "structure_merge_report",
      [MERGE]: { example: "task_merge_queued", status: 202 },
      [TASK]: ["task_merge_running", "task_merge_succeeded"],
    });
    open(merging());
    const form = await openMerge();

    // The report as the server read it: what is added, modified and removed, in the marks.
    const counts = await within(form).findByRole("list", { name: "Écarts par objet" });
    expect(within(counts).getByText("Tâches")).toBeVisible();
    expect(counts).toHaveTextContent("+");
    expect(counts).toHaveTextContent("M");
    expect(counts).toHaveTextContent("-");
    expect(counts).toHaveTextContent("2 ajoutées");
    const table = within(form).getByRole("table", { name: /écarts/i });
    expect(within(table).getByText("Essais sur site")).toBeVisible();
    expect(within(table).getByText("Assistance aux essais de câblage")).toBeVisible();
    // The mark is doubled by a word: each change keeps an accessible name beside its character.
    const rowOf = (label: string) => within(table).getByRole("row", { name: new RegExp(label) });
    expect(within(rowOf("Essais sur site")).getAllByRole("cell")[0]).toHaveAccessibleName("Ajouté");
    expect(
      within(rowOf("Assistance aux essais de câblage")).getAllByRole("cell")[0],
    ).toHaveAccessibleName("Retiré");
    expect(within(rowOf("Mise en service sur site")).getAllByRole("cell")[0]).toHaveAccessibleName(
      "Modifié",
    );
    await expectAccessible(form);

    // Without a version name, the confirmation is not given.
    const confirm = within(form).getByRole("button", { name: "Confirmer la fusion" });
    expect(confirm).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(confirm);
    expect(bodies(client, MERGE)).toEqual([]);

    await userEvent.type(
      within(form).getByRole("textbox", { name: "Nom de version" }),
      "Avenant 2",
    );
    await userEvent.click(confirm);
    // The two counters of the report, which the fake back says are 1 and 2.
    expect(bodies(client, MERGE)).toEqual([
      {
        confirmed: true,
        version_name: "Avenant 2",
        main_structure_lock_version: 1,
        amendment_lock_version: 2,
      },
    ]);
    expect(client.calls.find((call) => call.route === MERGE)?.path).toBe(
      `/projects/${PROJECT}/revisions/${REVISION}/structures/${AMENDMENT}/merge`,
    );
    expect(screen.queryByRole("form", { name: "Contractualiser l’avenant" })).toBeNull();

    // The merge is followed in « Tâches de fond », then the new reference is said.
    const tasks = tasksRegion();
    await tick();
    expect(within(tasks).getByText("En cours")).toBeVisible();
    await tick();
    // Told on the screen, and noted in the history of the messages.
    const told = await screen.findAllByText(/« Avenant 2 » est la nouvelle révision de référence/);
    expect(told.length).toBeGreaterThan(0);
    expect(router.refresh).toHaveBeenCalled();
    // The task is followed by the identifier the queue gave it (…948), which its reads bear.
    const reads = client.calls.filter((call) => call.route === TASK);
    expect(reads.length).toBeGreaterThan(0);
    for (const one of reads) {
      expect(one.path).toBe("/tasks/01926f3a-7c00-7000-8000-000000000948");
    }
    closeTasks();
    expect(screen.getByRole("link", { name: "Voir les révisions" })).toHaveAttribute(
      "href",
      `/projects/${PROJECT}/revisions`,
    );
  });

  it("gives the focus to the way on once the reference is told and the command is taken away [WF-REV-0050-A]", async () => {
    serve({
      [REPORT]: "structure_merge_report",
      [MERGE]: { example: "task_merge_queued", status: 202 },
      [TASK]: ["task_merge_running", "task_merge_succeeded"],
    });
    const page = open(merging());
    const form = await openMerge();
    await within(form).findByRole("list", { name: "Écarts par objet" });
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Nom de version" }),
      "Avenant 2",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Confirmer la fusion" }));
    await tick();
    await tick();
    await screen.findAllByText(/« Avenant 2 » est la nouvelle révision de référence/);
    expect(router.refresh).toHaveBeenCalled();
    // The page read again lists the amendment as merged: the button that held the focus is gone.
    page.rerender(shell(merging(true)));
    expect(screen.queryByRole("button", { name: "Contractualiser l’avenant" })).toBeNull();
    expect(screen.getByRole("link", { name: "Voir les révisions" })).toHaveFocus();
  });

  it("tells no reference when the merge fails, does not read the page again, and keeps the command offered [WF-REV-0050-A]", async () => {
    serve({
      [REPORT]: "structure_merge_report",
      [MERGE]: { example: "task_merge_queued", status: 202 },
      [TASK]: ["task_failed"],
    });
    open(merging());
    const form = await openMerge();
    await within(form).findByRole("list", { name: "Écarts par objet" });
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Nom de version" }),
      "Avenant 2",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Confirmer la fusion" }));
    await tick();
    await tick();
    expect(within(tasksRegion()).getByText("Échouée")).toBeVisible();
    closeTasks();
    expect(screen.queryByText(/nouvelle révision de référence/)).toBeNull();
    expect(screen.queryByRole("link", { name: "Voir les révisions" })).toBeNull();
    expect(router.refresh).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Contractualiser l’avenant" })).toBeVisible();
  });

  it("tells a merge that fails for a post out of the subtree of its lot, naming the two tasks, as the contract gives them [WF-PLA-0170-A]", async () => {
    serve({
      [REPORT]: "structure_merge_report",
      [MERGE]: { example: "task_merge_queued", status: 202 },
      [TASK]: ["task_merge_outside_work_package"],
    });
    open(merging());
    const form = await openMerge();
    await within(form).findByRole("list", { name: "Écarts par objet" });
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Nom de version" }),
      "Avenant 2",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Confirmer la fusion" }));
    await tick();
    await tick();
    expect(tasksRegion()).toHaveTextContent(
      /La tâche d’un poste doit rester dans le sous-arbre de la tâche de son lot\. Tâche du lot\s:\s« Poste de commande »\. Tâche du poste en cause\s:\s« Câblage des armoires »\./,
    );
    closeTasks();
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("names the started task the merge will complete [WF-REV-0050-A]", async () => {
    // Le compte rendu d'une fusion dont le différentiel retire une tâche démarrée nomme cette
    // tâche comme terminée.
    serve({ [REPORT]: "structure_merge_report_started_task" });
    open(merging());
    const form = await openMerge();
    const report = example("structure_merge_report_started_task") as {
      completed_tasks: { label: string }[];
    };
    const [started] = report.completed_tasks;
    expect(await within(form).findByText(new RegExp(`« ${started?.label ?? ""} »`))).toBeVisible();
    expect(within(form).getByText("1 tâche démarrée sera terminée")).toBeVisible();
  });

  it("sends nothing when abandoned at the report: the revision and the reference stay as they were [WF-REV-0050-A]", async () => {
    // L'abandon à cette étape laisse la révision en cours et la référence inchangées.
    const client = serve({ [REPORT]: "structure_merge_report" });
    open(merging());
    const form = await openMerge();
    await within(form).findByRole("list", { name: "Écarts par objet" });
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("form", { name: "Contractualiser l’avenant" })).toBeNull();
    expect(client.calls.map((call) => call.route)).toEqual([REPORT]);
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("does not offer the confirmation while the report carries a motive of refusal [WF-REV-0050-A]", async () => {
    const client = serve({ [REPORT]: "structure_merge_report_refused" });
    open(merging());
    const form = await openMerge();
    expect(
      await within(form).findByText(/motif refuse la fusion|motifs refusent la fusion/),
    ).toBeVisible();
    await userEvent.type(within(form).getByRole("textbox", { name: "Nom de version" }), "V3");
    const confirm = within(form).getByRole("button", { name: "Confirmer la fusion" });
    expect(confirm).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(confirm);
    expect(bodies(client, MERGE)).toEqual([]);
  });

  it("joins the description typed to the revision produced, and sends none when it is left empty [WF-REV-0050-A]", async () => {
    // La description de la fusion, facultative, est celle de la révision marquée qu'elle produit.
    const client = serve({
      [REPORT]: "structure_merge_report",
      [MERGE]: { example: "task_merge_queued", status: 202 },
      [TASK]: ["task_merge_running", "task_merge_succeeded"],
    });
    open(merging());
    const form = await openMerge();
    await within(form).findByRole("list", { name: "Écarts par objet" });
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Nom de version" }),
      "Avenant 2",
    );
    await userEvent.type(
      within(form).getByRole("textbox", {
        name: "Description de la révision produite (facultative)",
      }),
      "Essais sur site ajoutés par l’avenant 2",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Confirmer la fusion" }));
    expect(bodies(client, MERGE)).toEqual([
      {
        confirmed: true,
        version_name: "Avenant 2",
        description: "Essais sur site ajoutés par l’avenant 2",
        main_structure_lock_version: 1,
        amendment_lock_version: 2,
      },
    ]);
  });

  it("proposes to read the report again on a stale version (412), and keeps the version name typed [WF-IHM-0110-A]", async () => {
    const client = serve({
      [REPORT]: "structure_merge_report",
      [MERGE]: { problem: { ...(example("merge_report_stale") as Problem), status: 412 as const } },
    });
    open(merging());
    const form = await openMerge();
    await within(form).findByRole("list", { name: "Écarts par objet" });
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Nom de version" }),
      "Avenant 2",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Confirmer la fusion" }));

    const reread = await within(form).findByRole("button", { name: "Relire le compte rendu" });
    await userEvent.click(reread);
    await within(form).findByRole("list", { name: "Écarts par objet" });
    expect(client.calls.filter((call) => call.route === REPORT)).toHaveLength(2);
    expect(within(form).getByRole("textbox", { name: "Nom de version" })).toHaveValue("Avenant 2");
  });

  it("is offered on the last revision marked when the project has none in progress, and its report says the merge creates it [WF-REV-0050-A]", async () => {
    // Lorsque le projet ne comporte pas de révision en cours, elle en crée une au préalable
    // (conception d'EP-16, « Une fusion sans révision en cours », #790 : le Vérif de WF-REV-0050-A
    // ne dit pas ce cas).
    const client = serve({ [REPORT]: "structure_merge_report_without_current_revision" });
    open(merging(false, "revision_marked_merge_offered"));
    const form = await openMerge();
    expect(await within(form).findByRole("note")).toHaveTextContent(
      "Le projet n’a pas de révision en cours : la fusion la crée d’abord par copie de la dernière révision marquée",
    );
    expect(within(form).getByRole("list", { name: "Écarts par objet" })).toBeVisible();
    await userEvent.type(within(form).getByRole("textbox", { name: "Nom de version" }), "V3");
    const confirm = within(form).getByRole("button", { name: "Confirmer la fusion" });
    expect(confirm).not.toHaveAttribute("aria-disabled", "true");
    expect(client.calls.map((call) => call.route)).toEqual([REPORT]);
  });

  it("says nothing of a revision created when the project has one in progress [WF-REV-0050-A]", async () => {
    serve({ [REPORT]: "structure_merge_report" });
    open(merging());
    const form = await openMerge();
    await within(form).findByRole("list", { name: "Écarts par objet" });
    expect(within(form).queryByRole("note")).toBeNull();
  });

  it.each([
    {
      example: "structure_merge_report_link_forbidden" as const,
      sentence:
        /Liaison en cause, la récapitulative d’abord : « Installation sur site » et « Montage des armoires sur site »/,
    },
    {
      example: "structure_merge_report_horizon_exceeded" as const,
      sentence: /Tâche en cause : « Mise en service »/,
    },
  ])(
    "gives the tasks of a refusal with the motive, and does not offer the confirmation [WF-PLA-0030-A] [WF-PLA-0150-A] ($example)",
    async ({ example: name, sentence }) => {
      serve({ [REPORT]: name });
      open(merging());
      const form = await openMerge();
      expect(await within(form).findByRole("alert")).toHaveTextContent(sentence);
      await userEvent.type(within(form).getByRole("textbox", { name: "Nom de version" }), "V3");
      expect(within(form).getByRole("button", { name: "Confirmer la fusion" })).toHaveAttribute(
        "aria-disabled",
        "true",
      );
    },
  );

  it("is not presented for an amendment already merged, and not at all without the offer", () => {
    serve({});
    const merged = open(merging(true));
    expect(screen.queryByRole("button", { name: "Contractualiser l’avenant" })).toBeNull();
    merged.unmount();
    const reader = open(merging(false, "revision_estimator"));
    expect(screen.queryByRole("button", { name: "Contractualiser l’avenant" })).toBeNull();
    reader.unmount();
  });
});
