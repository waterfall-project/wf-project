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
import type { Revision } from "@/components/context/read-only";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { ExportForm } from "./export-form";
import { ImportCommands } from "./import-commands";
import { ImportList } from "./import-list";
import { ImportReport } from "./import-report";
import { exportOffers, importOffers } from "./offers";

// The server of Next, as far as the exchanges need it: the fake back behind serverClient.
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

type Import = components["schemas"]["Import"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IMPORT = "01926f3a-7c00-7000-8000-000000000a11";
const START = `/projects/${PROJECT}/revisions/${REVISION}/exchanges?as_of=2026-05-31`;
const UPLOAD = "POST /file-uploads";
const OPEN = "POST /projects/{project_id}/imports";
const APPLY = "POST /projects/{project_id}/imports/{import_id}/apply";
const ABANDON = "DELETE /projects/{project_id}/imports/{import_id}";
const EXPORT = "POST /projects/{project_id}/exports";
const TASK = "GET /tasks/{task_id}";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The routes the fake back was called on, in order. */
function routes(client: FakeClient): string[] {
  return client.calls.map((call) => call.route);
}

/** A part of the screen within the shell that follows the tasks, in a language. */
function shell(part: ReactNode, locale: "fr" | "en" = "fr") {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      <TaskTracker>
        <TaskPanel />
        <main>{part}</main>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** Render a part of the screen within the shell, in a language. */
function open(part: ReactNode, locale: "fr" | "en" = "fr") {
  return render(shell(part, locale));
}

/** The commands of import a project of the contract offers. */
function importCommands(project = "project") {
  const offers = importOffers(example(project) as Project);
  return <ImportCommands projectId={PROJECT} offers={offers} start={START} />;
}

/** The request of an export of a revision of the contract, as it offers its exports. */
function exportForm(revision = "revision") {
  const offers = exportOffers(example(revision) as Revision);
  return <ExportForm projectId={PROJECT} revisionId={REVISION} offers={offers} />;
}

/** The report of an import of the contract, as the screen shows it. */
function report(entry: Import) {
  const offers = importOffers(example("project") as Project);
  return (
    <ImportReport projectId={PROJECT} entry={entry} offer={offers[entry.kind]} start={START} />
  );
}

/** The region of the tasks of the shell. */
function tasks() {
  return screen.getByRole("region", { name: "Tâches de fond" });
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

describe("the first step of an import", () => {
  it("offers the import of each kind as the server offers it, an unavailable one with what it lacks", async () => {
    serve({});
    const { container } = open(importCommands("project_completed"));
    expect(screen.getAllByRole("button").map((button) => button.textContent)).toEqual([
      "Importer un planning MS Project",
      "Importer un devis",
      "Importer un reste à engager",
      "Importer des coûts réels",
    ]);
    const costs = screen.getByRole("button", { name: "Importer des coûts réels" });
    expect(costs).toHaveAttribute("aria-disabled", "true");
    expect(costs).toHaveAccessibleDescription("Condition non remplie : projet non clos.");
    await userEvent.click(costs);
    expect(screen.queryByRole("form")).toBeNull();
    await expectAccessible(container);
  });

  it("offers an import on a project without a current revision, naming the permission to create the revision when it lacks", async () => {
    serve({});
    const { container } = open(importCommands("project_pricing_estimator"));
    const estimate = screen.getByRole("button", { name: "Importer un devis" });
    expect(screen.getAllByRole("button")).toEqual([estimate]);
    expect(estimate).toHaveAttribute("aria-disabled", "true");
    expect(estimate).toHaveAccessibleDescription(
      "Condition non remplie\u00A0: avoir la permission de créer une révision.",
    );
    await userEvent.click(estimate);
    expect(screen.queryByRole("form")).toBeNull();
    await expectAccessible(container);
  });

  it("asks the file, says it missing without sending anything, and closes on cancel", async () => {
    const client = serve({});
    open(importCommands());
    const command = screen.getByRole("button", { name: "Importer un devis" });
    await userEvent.click(command);
    const form = screen.getByRole("form", { name: "Importer un devis" });
    expect(within(form).getByLabelText("Fichier à importer")).toHaveFocus();
    await userEvent.click(within(form).getByRole("button", { name: "Analyser le fichier" }));
    expect(within(form).getByRole("alert")).toHaveTextContent("Choisissez le fichier à importer.");
    expect(client.calls).toEqual([]);
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("form")).toBeNull();
    expect(command).toHaveFocus();
  });

  it("deposits the file, opens its analysis, follows it in the shell, and shows the report of the import", async () => {
    const client = serve({
      [UPLOAD]: { example: "file_upload", status: 201 },
      [OPEN]: { example: "import_analysing", status: 202 },
      [TASK]: "task_running",
    });
    open(importCommands());
    await userEvent.click(screen.getByRole("button", { name: "Importer un devis" }));
    const form = screen.getByRole("form", { name: "Importer un devis" });
    const file = new File(["devis"], "devis-poste-de-commande.xlsx");
    await userEvent.upload(within(form).getByLabelText("Fichier à importer"), file);
    await userEvent.click(within(form).getByRole("button", { name: "Analyser le fichier" }));
    await waitFor(() => {
      expect(router.push).toHaveBeenCalledWith(`${START}&import=${IMPORT}`);
    });
    expect(routes(client).slice(0, 2)).toEqual([UPLOAD, OPEN]);
    expect(client.calls[1]?.body).toEqual({
      kind: "estimate",
      upload_id: "01926f3a-7c00-7000-8000-000000000a01",
    });
    expect(screen.queryByRole("form")).toBeNull();
    expect(
      within(tasks()).getByText("Analyse d’un import « devis-poste-de-commande.xlsx »"),
    ).toBeVisible();
  });

  it("follows the analysis but stays where the user went when the import opens after the screen was left", async () => {
    let answer!: () => void;
    const held = new Promise<void>((resolve) => {
      answer = resolve;
    });
    const client = fakeClient(
      {
        [UPLOAD]: { example: "file_upload", status: 201 },
        [OPEN]: { example: "import_analysing", status: 202 },
        [TASK]: "task_running",
      },
      { hold: (route) => (route === OPEN ? held : undefined) },
    );
    server.client = client;
    open(importCommands());
    await userEvent.click(screen.getByRole("button", { name: "Importer un devis" }));
    const form = screen.getByRole("form", { name: "Importer un devis" });
    await userEvent.upload(
      within(form).getByLabelText("Fichier à importer"),
      new File(["devis"], "devis-poste-de-commande.xlsx"),
    );
    await userEvent.click(within(form).getByRole("button", { name: "Analyser le fichier" }));
    await waitFor(() => {
      expect(routes(client)).toEqual([UPLOAD, OPEN]);
    });
    window.history.replaceState(null, "", `/projects/${PROJECT}/lifecycle`);
    answer();
    await waitFor(() => {
      expect(screen.queryByRole("form")).toBeNull();
    });
    expect(router.push).not.toHaveBeenCalled();
    expect(
      within(tasks()).getByText("Analyse d’un import « devis-poste-de-commande.xlsx »"),
    ).toBeVisible();
  });

  it("refuses at once a file larger than an import takes, and sends nothing", async () => {
    const client = serve({});
    open(importCommands());
    await userEvent.click(screen.getByRole("button", { name: "Importer un planning MS Project" }));
    const form = screen.getByRole("form", { name: "Importer un planning MS Project" });
    const field = within(form).getByLabelText("Fichier à importer");
    const large = new File(["x"], "planning.xml");
    Object.defineProperty(large, "size", { value: 10 * 1024 * 1024 + 1 });
    await userEvent.upload(field, large);
    await userEvent.click(within(form).getByRole("button", { name: "Analyser le fichier" }));
    expect(within(form).getByRole("alert")).toHaveTextContent(
      "Le fichier dépasse 10 Mio, la plus grande taille qu’un import admet.",
    );
    expect(field).toHaveFocus();
    expect(client.calls).toEqual([]);
  });

  it("sends the period an extraction of actual costs declares, and none it leaves out", async () => {
    const client = serve({
      [UPLOAD]: { example: "file_upload", status: 201 },
      [OPEN]: { example: "import_analysing", status: 202 },
      [TASK]: "task_running",
    });
    open(importCommands());
    await userEvent.click(screen.getByRole("button", { name: "Importer des coûts réels" }));
    const form = screen.getByRole("form", { name: "Importer des coûts réels" });
    const period = within(form).getByRole("group", { name: "Période extraite" });
    await userEvent.type(within(period).getByLabelText("Du"), "2026-05-01");
    await userEvent.upload(
      within(form).getByLabelText("Fichier à importer"),
      new File(["x"], "couts-reels-2026-05.xlsx"),
    );
    await userEvent.click(within(form).getByRole("button", { name: "Analyser le fichier" }));
    await waitFor(() => {
      expect(routes(client).slice(0, 2)).toEqual([UPLOAD, OPEN]);
    });
    expect(client.calls[1]?.body).toEqual({
      kind: "actual_costs",
      period_from: "2026-05-01",
      period_to: null,
      upload_id: "01926f3a-7c00-7000-8000-000000000a01",
    });
  });

  it("tells a deposit refused under the form, and opens no import", async () => {
    const client = serve({ [UPLOAD]: { problem: { code: "FILE_TOO_LARGE", status: 413 } } });
    open(importCommands());
    await userEvent.click(screen.getByRole("button", { name: "Importer des coûts réels" }));
    const form = screen.getByRole("form", { name: "Importer des coûts réels" });
    await userEvent.upload(
      within(form).getByLabelText("Fichier à importer"),
      new File(["x"], "couts.xlsx"),
    );
    await userEvent.click(within(form).getByRole("button", { name: "Analyser le fichier" }));
    await settled(form);
    expect(within(form).getByRole("alert")).toHaveTextContent(CATALOGUES.fr.errors.FILE_TOO_LARGE);
    expect(routes(client)).toEqual([UPLOAD]);
    expect(router.push).not.toHaveBeenCalled();
  });
});

describe("the report of an import", () => {
  it("lists the rejected lines with their motive before any confirmation, and applies nothing until confirmed [WF-INTF-0080-A]", async () => {
    const client = serve({
      [APPLY]: { example: "task_import_queued", status: 202 },
      [TASK]: "task_running",
    });
    const { container } = open(report(example("import_analysed") as Import));
    const section = screen.getByRole("region", {
      name: "Compte rendu de l’import « devis-poste-de-commande.xlsx »",
    });
    const rejected = within(section).getByRole("table", { name: "Lignes rejetées" });
    expect(
      within(rejected)
        .getAllByRole("row")
        .map((row) => row.textContent),
    ).toEqual(["LigneMotif", "3Tâche inconnue.", "5Rôle de ressource inconnu."]);

    await userEvent.click(screen.getByRole("button", { name: "Appliquer l’import" }));
    const confirmation = screen.getByRole("form", { name: "Confirmation de l’application" });
    expect(within(confirmation).getByRole("paragraph")).toHaveTextContent(
      "Appliquer au projet l’import « devis-poste-de-commande.xlsx », en une seule opération ?",
    );
    expect(
      within(confirmation).getByRole("button", { name: "Confirmer l’application" }),
    ).toHaveFocus();
    expect(client.calls).toEqual([]);
    await expectAccessible(container);

    await userEvent.click(
      within(confirmation).getByRole("button", { name: "Confirmer l’application" }),
    );
    await waitFor(() => {
      expect(screen.queryByRole("form")).toBeNull();
    });
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [`/projects/${PROJECT}/imports/${IMPORT}/apply`, { confirmed: true }],
    ]);
    expect(
      within(tasks()).getByText("Application d’un import « devis-poste-de-commande.xlsx »"),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Appliquer l’import" })).toHaveFocus();
  });

  it("applies nothing when the confirmation is cancelled, and tells a refusal of the application", async () => {
    const client = serve({
      [APPLY]: { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } },
    });
    open(report(example("import_analysed") as Import));
    await userEvent.click(screen.getByRole("button", { name: "Appliquer l’import" }));
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("form")).toBeNull();
    expect(client.calls).toEqual([]);

    await userEvent.click(screen.getByRole("button", { name: "Appliquer l’import" }));
    const confirmation = screen.getByRole("form", { name: "Confirmation de l’application" });
    await userEvent.click(
      within(confirmation).getByRole("button", { name: "Confirmer l’application" }),
    );
    await settled(confirmation);
    expect(within(confirmation).getByRole("alert")).toHaveTextContent(
      CATALOGUES.fr.errors.STATE_FORBIDS_OPERATION,
    );
    expect(within(tasks()).queryByText(/Application d’un import/)).toBeNull();
  });

  it("abandons the import, which applies nothing and leads back to the screen as it was before it", async () => {
    const client = serve({ [ABANDON]: { status: 204 } });
    open(report(example("import_analysed") as Import));
    await userEvent.click(screen.getByRole("button", { name: "Abandonner l’import" }));
    await waitFor(() => {
      expect(router.push).toHaveBeenCalledWith(START);
    });
    expect(client.calls.map(({ route, path }) => [route, path])).toEqual([
      [ABANDON, `/projects/${PROJECT}/imports/${IMPORT}`],
    ]);
  });

  it("stays where the user went when the abandonment answers after another import was opened", async () => {
    let answer!: () => void;
    const held = new Promise<void>((resolve) => {
      answer = resolve;
    });
    const client = fakeClient({ [ABANDON]: { status: 204 } }, { hold: () => held });
    server.client = client;
    open(report(example("import_analysed") as Import));
    const abandon = screen.getByRole("button", { name: "Abandonner l’import" });
    await userEvent.click(abandon);
    await waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    window.history.replaceState(null, "", `${START}&import=01926f3a-7c00-7000-8000-000000000a10`);
    answer();
    await waitFor(() => {
      expect(abandon).toHaveAttribute("aria-busy", "false");
    });
    expect(router.push).not.toHaveBeenCalled();
  });

  it("closes the confirmation when the screen shows another import, which no longer awaits it", async () => {
    serve({});
    const { items } = example("imports") as { items: Import[] };
    const applied = items.find((entry) => entry.status === "applied");
    if (applied === undefined) {
      throw new Error("the example of the imports holds one applied");
    }
    const { rerender } = open(report(example("import_analysed") as Import));
    await userEvent.click(screen.getByRole("button", { name: "Appliquer l’import" }));
    expect(screen.getByRole("form", { name: "Confirmation de l’application" })).toBeVisible();
    rerender(shell(report(applied)));
    expect(screen.queryByRole("form")).toBeNull();
    expect(screen.queryByRole("button", { name: "Appliquer l’import" })).toBeNull();
  });

  it("tells the refusal of an abandonment under the import it was asked for, not the next one", async () => {
    let answer!: () => void;
    const held = new Promise<void>((resolve) => {
      answer = resolve;
    });
    server.client = fakeClient(
      { [ABANDON]: { problem: { code: "PERMISSION_MISSING", status: 403 } } },
      { hold: () => held },
    );
    const { rerender } = open(report(example("import_analysed") as Import));
    await userEvent.click(screen.getByRole("button", { name: "Abandonner l’import" }));
    rerender(shell(report(example("import_planning_mismatch") as Import)));
    answer();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Abandonner l’import" })).toHaveAttribute(
        "aria-busy",
        "false",
      );
    });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("offers neither application nor abandonment of an import that no longer awaits a decision", () => {
    serve({});
    const { items } = example("imports") as { items: Import[] };
    const applied = items.find((entry) => entry.status === "applied");
    if (applied === undefined) {
      throw new Error("the example of the imports holds one applied");
    }
    open(report(applied));
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByText("Cet import n’a pas de compte rendu.")).toBeVisible();
  });

  it("offers no undo of an import applied: neither its report nor the list of the imports holds such a command [WF-IHM-0110-A]", () => {
    serve({});
    const { items } = example("imports") as { items: Import[] };
    const applied = items.find((entry) => entry.status === "applied");
    if (applied === undefined) {
      throw new Error("the example of the imports holds one applied");
    }
    const { unmount } = open(report(applied));
    expect(screen.queryByRole("button", { name: /Annuler|Rétablir/ })).toBeNull();
    unmount();
    open(<ImportList imports={items} total={items.length} current={undefined} start={START} />);
    expect(screen.getByRole("table")).toBeVisible();
    expect(screen.queryByRole("button", { name: /Annuler|Rétablir/ })).toBeNull();
    expect(screen.queryByRole("menuitem")).toBeNull();
  });

  it("is rendered from the same codes in the language of its reader [WF-ARC-0110-A]", () => {
    serve({});
    open(report(example("import_planning_mismatch") as Import), "en");
    const differences = screen.getByRole("table", { name: "Differences with the existing data" });
    expect(differences).toHaveTextContent("UpdatedTaskRevue de conceptionDuration");
    expect(differences).toHaveTextContent("KeptTaskÉtudes de détail");
  });
});

describe("the request of an export", () => {
  it("asks the kind chosen in the revision read, follows its task, and offers its result once made", async () => {
    const client = serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_succeeded",
    });
    open(exportForm());
    const form = screen.getByRole("form", { name: "Demander un export" });
    await userEvent.selectOptions(within(form).getByLabelText("Fichier à exporter"), "Devis");
    await userEvent.click(within(form).getByRole("button", { name: "Demander l’export" }));
    await settled(form);
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [`/projects/${PROJECT}/exports`, { kind: "estimate", revision_id: REVISION }],
    ]);
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    const download = await within(tasks()).findByRole("link", {
      name: "Télécharger le résultat : Export « Devis »",
    });
    expect(download).toHaveAttribute("href", "/tasks/01926f3a-7c00-7000-8000-000000000905/result");
    expect(download).toHaveAttribute("download");
  });

  it.each([
    ["2", 2],
    ["1000", 1000],
  ] as const)(
    "asks the image of the tree of tasks at the level given: %s",
    async (typed, level) => {
      const client = serve({ [EXPORT]: { example: "task_export_queued", status: 202 } });
      open(exportForm());
      const form = screen.getByRole("form", { name: "Demander un export" });
      await userEvent.selectOptions(
        within(form).getByLabelText("Fichier à exporter"),
        "Image de l’arborescence de tâches",
      );
      await userEvent.type(within(form).getByLabelText("Niveau de l’arborescence"), typed);
      await userEvent.click(within(form).getByRole("button", { name: "Demander l’export" }));
      await settled(form);
      expect(client.calls.map((call) => call.body)).toEqual([
        { kind: "task_tree_image", revision_id: REVISION, depth: level },
      ]);
    },
  );

  it("offers only the kinds the revision read offers, and tells a refusal", async () => {
    const client = serve({ [EXPORT]: { problem: { code: "PERMISSION_MISSING", status: 403 } } });
    open(exportForm("revision_estimator"));
    const form = screen.getByRole("form", { name: "Demander un export" });
    const kinds = within(form).getByLabelText("Fichier à exporter");
    expect(
      within(kinds)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Devis", "Reste à engager"]);
    await userEvent.click(within(form).getByRole("button", { name: "Demander l’export" }));
    await settled(form);
    expect(client.calls.map((call) => call.body)).toEqual([
      { kind: "estimate", revision_id: REVISION },
    ]);
    expect(within(form).getByRole("alert")).toHaveTextContent(
      CATALOGUES.fr.errors.PERMISSION_MISSING,
    );
  });

  it("says no export is offered without a revision that offers one", () => {
    serve({});
    open(<ExportForm projectId={PROJECT} revisionId={REVISION} offers={exportOffers(undefined)} />);
    expect(screen.queryByRole("form")).toBeNull();
    expect(screen.getByText("Aucun export ne vous est offert sur cette révision.")).toBeVisible();
  });
});
