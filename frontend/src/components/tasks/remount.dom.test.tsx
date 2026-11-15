// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { IdentitySync } from "@/components/admin/identity-sync";
import { StartBackupButton } from "@/components/admin/backup-commands";
import type { Revision } from "@/components/context/read-only";
import { RevisionCommands } from "@/components/commands/object-commands";
import { ExportForm } from "@/components/exchanges/export-form";
import { FileDrop } from "@/components/exchanges/file-drop";
import { ImportReport } from "@/components/exchanges/import-report";
import { exportOffers } from "@/components/exchanges/offers";
import { TaskTreeExport } from "@/components/tree/task-tree-export";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ProjectContext } from "@/navigation/context";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { STORAGE_KEY, type KeptTask } from "./storage";
import { POLL_INTERVAL } from "./task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "./task-tracker";
import { taskAim } from "./tracking";

// The button that started a task finds it again once mounted anew, the screen left and come back
// to, or the tab reloaded, and waits for it until it ends (#3404); the waiting of each button from
// its press is in the tests of its screen. The server of Next, as far as the buttons need it.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => `/projects/${PROJECT}/revisions/${REVISION}/exchanges`,
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const START = `/projects/${PROJECT}/revisions/${REVISION}/exchanges`;
const CONTEXT: ProjectContext = {
  projectId: PROJECT,
  revisionId: REVISION,
  revisionInPath: true,
  parameters: new URLSearchParams(),
};
const TASK = "GET /tasks/{task_id}";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The shell that follows the tasks, with a part of a screen in it, or none: the screen left. */
function shell(part: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>{part}</main>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** A button that starts a task: the part of its screen, how it is pressed, what it asks. */
interface Case {
  readonly name: string;
  readonly part: () => ReactNode;
  readonly button: () => HTMLElement;
  readonly press: () => Promise<void>;
  /** The route that starts the task, which is asked once. */
  readonly route: string;
  readonly answers: FakeAnswers;
}

/** The button of the main region named so. */
function button(name: string | RegExp): () => HTMLElement {
  return () => within(screen.getByRole("main")).getByRole("button", { name });
}

/** Press a button of the main region. */
async function click(name: string | RegExp) {
  await userEvent.click(button(name)());
}

/** The commands of the revision of the contract, its marking among them. */
function revisionCommands() {
  return <RevisionCommands revision={example("revision") as Revision} context={CONTEXT} />;
}

const CASES: readonly Case[] = [
  {
    name: "the marking of a revision",
    part: revisionCommands,
    button: button("Marquer la révision"),
    press: async () => {
      await click("Marquer la révision");
      await userEvent.type(screen.getByRole("textbox", { name: "Nom de version" }), "V2");
      await click(/^Marquer$/);
    },
    route: "POST /projects/{project_id}/revisions/{revision_id}/mark",
    answers: {
      "POST /projects/{project_id}/revisions/{revision_id}/mark": {
        example: "task_mark_queued",
        status: 202,
      },
    },
  },
  {
    name: "the request of an export",
    part: () => (
      <ExportForm
        projectId={PROJECT}
        revisionId={REVISION}
        offers={exportOffers(example("revision") as Revision)}
      />
    ),
    button: button("Demander l’export"),
    press: () => click("Demander l’export"),
    route: "POST /projects/{project_id}/exports",
    answers: {
      "POST /projects/{project_id}/exports": { example: "task_export_queued", status: 202 },
    },
  },
  {
    name: "the export of the image of the task tree",
    part: () => (
      <TaskTreeExport
        projectId={PROJECT}
        revisionId={REVISION}
        depth={2}
        offer={exportOffers(example("revision") as Revision).task_tree_image}
      />
    ),
    button: button("Exporter l’image de l’arborescence de tâches"),
    press: () => click("Exporter l’image de l’arborescence de tâches"),
    route: "POST /projects/{project_id}/exports",
    answers: {
      "POST /projects/{project_id}/exports": { example: "task_export_queued", status: 202 },
    },
  },
  {
    name: "the drop zone of the file of an import",
    part: () => <FileDrop projectId={PROJECT} start={START} />,
    button: button(/^Choisir/),
    press: async () => {
      fireEvent.drop(within(screen.getByRole("main")).getByRole("group"), {
        dataTransfer: { files: [new File(["<Project/>"], "planning.xml", { type: "text/xml" })] },
      });
      await Promise.resolve();
    },
    route: "POST /projects/{project_id}/imports",
    answers: {
      "POST /file-uploads": { example: "file_upload", status: 201 },
      "POST /projects/{project_id}/imports": { example: "import_analysing", status: 202 },
    },
  },
  {
    name: "the application of an import",
    part: () => (
      <ImportReport
        projectId={PROJECT}
        entry={example("import_analysed") as components["schemas"]["ImportDetail"]}
        start={START}
      />
    ),
    button: button("Appliquer l’import"),
    press: async () => {
      await click("Appliquer l’import");
      await click("Confirmer l’application");
    },
    route: "POST /projects/{project_id}/imports/{import_id}/apply",
    answers: {
      "POST /projects/{project_id}/imports/{import_id}/apply": {
        example: "task_import_queued",
        status: 202,
      },
    },
  },
  {
    name: "a backup",
    part: () => <StartBackupButton variant="default" />,
    button: button("Sauvegarder maintenant"),
    press: () => click("Sauvegarder maintenant"),
    route: "POST /backups",
    answers: { "POST /backups": { example: "task_backup_queued", status: 202 } },
  },
  {
    name: "a reading of the accounts of the identity provider",
    part: () => <IdentitySync report={undefined} schedule={undefined} startable />,
    button: button("Lire les comptes"),
    press: () => click("Lire les comptes"),
    route: "POST /identity-syncs",
    answers: { "POST /identity-syncs": { example: "identity_sync_queued", status: 202 } },
  },
];

/** Whether a button waits: inert, busy, a wheel in place of its icon. */
function expectWaiting(element: HTMLElement) {
  expect(element).toHaveAttribute("aria-busy", "true");
  expect(element).toHaveAttribute("aria-disabled", "true");
  expect(element.querySelector("[data-waiting]")).not.toBeNull();
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("a button mounted anew while the task it started runs", () => {
  it.each(CASES)(
    "$name waits after the screen is left and come back to, and after a reload, until the task ends [WF-IHM-0080-A]",
    async ({ part, button: pressed, press, route, answers }) => {
      // The button that started the task stays inert while it runs (#3404). A read while it runs
      // finds it running still.
      const client = serve({ ...answers, [TASK]: "task_running" });
      const view = render(shell(part()));
      await press();
      await waitFor(() => {
        expectWaiting(pressed());
      });

      // The screen left, and come back to: the button, mounted anew, finds its task.
      view.rerender(shell(null));
      expect(within(screen.getByRole("main")).queryByRole("button")).toBeNull();
      view.rerender(shell(part()));
      expectWaiting(pressed());
      await userEvent.click(pressed());

      // The tab reloaded: the shell reads back what the tab kept, and the button finds its task.
      view.unmount();
      render(shell(part()));
      await waitFor(() => {
        expectWaiting(pressed());
      });
      await userEvent.click(pressed());
      expect(client.calls.filter((call) => call.route === route)).toHaveLength(1);

      // The task fails: the button is given back, to run the same treatment again.
      serve({ [TASK]: "task_failed" });
      await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
      await waitFor(() => {
        expect(pressed()).toHaveAttribute("aria-busy", "false");
      });
      expect(pressed().querySelector("[data-waiting]")).toBeNull();
    },
  );

  it("waits for the task of its own aim only, not for one of another object [WF-IHM-0080-A]", async () => {
    // The marking of another revision runs in the tab: the command of this one does not wait.
    const kept: KeptTask[] = [
      {
        key: "01926f3a-7c00-7000-8000-000000000931",
        task_id: "01926f3a-7c00-7000-8000-000000000931",
        kind: "revision_mark",
        status: "running",
        subject: "V2",
        aim: taskAim("revision_mark", "01926f3a-7c00-7000-8000-000000000103"),
      },
    ];
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(kept));
    serve({ [TASK]: "task_running" });
    render(shell(revisionCommands()));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^Tâches et messages/ })).toHaveAccessibleName(/1/);
    });
    expect(button("Marquer la révision")()).toHaveAttribute("aria-busy", "false");
  });
});

describe("what a task found again does not do by itself", () => {
  /** Keep a running task of the tab, as a reload finds it. */
  function keep(task: KeptTask) {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify([task]));
  }

  it("takes no file in the drop zone while the analysis found again runs [WF-IHM-0080-A]", async () => {
    keep({
      key: "01926f3a-7c00-7000-8000-000000000932",
      task_id: "01926f3a-7c00-7000-8000-000000000932",
      kind: "import_analysis",
      status: "running",
      subject: "planning.xml",
      aim: taskAim("import_analysis", PROJECT),
    });
    const client = serve({ [TASK]: "task_running" });
    render(shell(<FileDrop projectId={PROJECT} start={START} />));
    await waitFor(() => {
      expectWaiting(button(/^Choisir/)());
    });
    fireEvent.drop(within(screen.getByRole("main")).getByRole("group"), {
      dataTransfer: { files: [new File(["<Project/>"], "other.xml", { type: "text/xml" })] },
    });
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(client.calls.filter((call) => call.route.startsWith("POST "))).toHaveLength(0);
  });

  it("downloads nothing by itself when the export found again succeeds [WF-IHM-0080-A] [WF-DAT-0120]", async () => {
    // A file served once: only the screen that asked for the export downloads it by itself; the
    // card of the end offers it to the user.
    keep({
      key: "01926f3a-7c00-7000-8000-000000000935",
      task_id: "01926f3a-7c00-7000-8000-000000000935",
      kind: "export",
      status: "running",
      subject: "Devis",
      aim: taskAim("export", REVISION),
    });
    serve({ [TASK]: "task_running" });
    render(
      shell(
        <ExportForm
          projectId={PROJECT}
          revisionId={REVISION}
          offers={exportOffers(example("revision") as Revision)}
        />,
      ),
    );
    await waitFor(() => {
      expectWaiting(button("Demander l’export")());
    });
    const client = serve({ [TASK]: "task_export_succeeded" });
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await waitFor(() => {
      expect(button("Demander l’export")()).toHaveAttribute("aria-busy", "false");
    });
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    expect(document.querySelector("iframe")).toBeNull();
    expect(client.calls.filter((call) => call.route === TASK).length).toBeLessThanOrEqual(2);
  });
});
