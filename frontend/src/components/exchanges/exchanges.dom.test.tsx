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
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { atCommit } from "@/test/committed";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";
import { heldLink } from "@/test/held-link";
import { tasksRegion } from "@/test/task-panel";

import { ExportForm } from "./export-form";
import { ImportCommands } from "./import-commands";
import { ImportList } from "./import-list";
import { ImportReport } from "./import-report";
import { exportOffers, importOffers, type MappingGap } from "./offers";

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
type Report = components["schemas"]["ImportReport"];

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
        <TasksButton />
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
function importCommands(project = "project", gap?: MappingGap) {
  const offers = importOffers(example(project) as Project);
  return <ImportCommands projectId={PROJECT} offers={offers} start={START} gap={gap} />;
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

/** The line of the tracker of the shell that says a task. */
function taskLine(text: string | RegExp) {
  return within(tasksRegion()).getByText(text);
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

describe("the first step of an import", () => {
  it("offers no import on a project that ended, which lists none (US-0702/L3)", () => {
    serve({});
    open(importCommands("project_completed"));
    expect(within(screen.getByRole("main")).queryAllByRole("button")).toEqual([]);
  });

  it("offers the import of each kind as the server lists it", async () => {
    serve({});
    const { container } = open(importCommands());
    expect(
      within(screen.getByRole("main"))
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual([
      "Importer un planning MS Project",
      "Importer un devis",
      "Importer un reste à engager",
      "Importer des coûts réels",
    ]);
    await expectAccessible(container);
  });

  it("offers an import on a project without a current revision, naming the permission to create the revision when it lacks", async () => {
    serve({});
    const { container } = open(importCommands("project_pricing_estimator"));
    const estimate = screen.getByRole("button", { name: "Importer un devis" });
    expect(within(screen.getByRole("main")).getAllByRole("button")).toEqual([estimate]);
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
    const file = new File(["devis"], "devis-avenant-2-reprise-des-essais.xlsx");
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
      taskLine("Analyse d’un import « devis-avenant-2-reprise-des-essais.xlsx »"),
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
      new File(["devis"], "devis-avenant-2-reprise-des-essais.xlsx"),
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
      taskLine("Analyse d’un import « devis-avenant-2-reprise-des-essais.xlsx »"),
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
    // Whether the deposit was still busy in the commit that told the refusal: the request over, never
    // while it holds a press (#1484).
    const busyWhenTold = atCommit(
      form,
      () => within(form).queryByRole("alert") !== null,
      () => form.getAttribute("aria-busy"),
    );
    await userEvent.click(within(form).getByRole("button", { name: "Analyser le fichier" }));
    await settled(form);
    expect(within(form).getByRole("alert")).toHaveTextContent(CATALOGUES.fr.errors.FILE_TOO_LARGE);
    expect(busyWhenTold.stop()).toEqual(["false"]);
    expect(routes(client)).toEqual([UPLOAD]);
    expect(router.push).not.toHaveBeenCalled();
  });
});

describe("the import of actual costs and the correspondence of the extraction", () => {
  const GAP: MappingGap = {
    columns: ["wbs_element", "document_number", "document_date", "amount"],
    href: "/reference/costs/actual-cost-mapping",
  };
  const PROJECT_WAITING = "project_actual_cost_mapping_incomplete";

  /** Send a file of actual costs, and give back the form that told the refusal. */
  async function sendCosts() {
    await userEvent.click(screen.getByRole("button", { name: "Importer des coûts réels" }));
    const form = screen.getByRole("form", { name: "Importer des coûts réels" });
    await userEvent.upload(
      within(form).getByLabelText("Fichier à importer"),
      new File(["x"], "couts.xlsx"),
    );
    await userEvent.click(within(form).getByRole("button", { name: "Analyser le fichier" }));
    await settled(form);
    return form;
  }

  it("says the unavailable command lacks the correspondence, names the columns without a label, and leads to the page of the correspondence [WF-REF-0190-A]", async () => {
    serve({});
    const { container } = open(importCommands(PROJECT_WAITING, GAP));
    const costs = screen.getByRole("button", { name: "Importer des coûts réels" });
    expect(costs).toHaveAttribute("aria-disabled", "true");
    expect(costs).toHaveAccessibleDescription(
      "Condition non remplie\u00A0: correspondance de l’extraction des coûts réels complète.",
    );
    expect(
      screen.getByText(/Colonnes exigées sans intitulé dans la correspondance/),
    ).toHaveTextContent(
      "Colonnes exigées sans intitulé dans la correspondance : Élément d’OTP, N° de pièce, Date de pièce, Montant.",
    );
    expect(
      screen.getByRole("link", { name: "Régler la correspondance de l’extraction" }),
    ).toHaveAttribute("href", "/reference/costs/actual-cost-mapping");
    await expectAccessible(container);
  });

  it("says the condition alone, with no link, to a session that may not read the correspondence [WF-REF-0190-A]", () => {
    serve({});
    open(importCommands(PROJECT_WAITING));
    expect(
      screen.getByRole("button", { name: "Importer des coûts réels" }),
    ).toHaveAccessibleDescription(/correspondance de l’extraction des coûts réels complète/);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("adds no note while the import of actual costs is available [WF-REF-0190-A]", () => {
    serve({});
    open(importCommands("project", GAP));
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("tells the refusal of the analysis for want of the correspondence, with the columns without a label [WF-REF-0190-A]", async () => {
    serve({
      [UPLOAD]: { example: "file_upload", status: 201 },
      [OPEN]: {
        problem: example("import_actual_cost_mapping_incomplete") as Problem & { status: 409 },
      },
    });
    open(importCommands());
    const form = await sendCosts();
    expect(within(form).getByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération. Condition non remplie : correspondance de l’extraction des coûts réels complète. Colonnes exigées sans intitulé : Élément d’OTP, N° de pièce, Date de pièce, Montant.",
    );
    expect(router.push).not.toHaveBeenCalled();
  });

  it("tells the refusal of a file that lacks a column required, with the labels declared for it [WF-REF-0190-A]", async () => {
    serve({
      [UPLOAD]: { example: "file_upload", status: 201 },
      [OPEN]: {
        problem: example("import_actual_costs_column_missing") as Problem & { status: 422 },
      },
    });
    open(importCommands());
    const form = await sendCosts();
    expect(within(form).getByRole("alert")).toHaveTextContent(
      "Colonne exigée absente du fichier : Montant (intitulé déclaré : « Val./Devise objet »).",
    );
  });

  it("names in the report the columns of the file the import ignores, as the file carries them [WF-REF-0190-A]", () => {
    serve({});
    open(report(example("import_actual_costs_column_ignored") as Import));
    expect(screen.getByRole("heading", { name: "Éléments ignorés par l’import" })).toBeVisible();
    expect(screen.getByText(/Colonnes de l’extraction ni lues ni conservées/)).toHaveTextContent(
      "Colonnes de l’extraction ni lues ni conservées (1) : Nom Matricule",
    );
  });
});

describe("the report of an import", () => {
  it("says the motive of two lines of the file of the same document and item, each rejected, and designates a line by both [WF-INTF-0080-A]", () => {
    serve({});
    open(report(example("import_actual_costs_duplicate_line") as Import));
    const rejected = screen.getByRole("table", { name: "Lignes rejetées" });
    const sentence =
      "Cette ligne partage sa pièce et son poste, poste vide compris, avec d’autres lignes du fichier : toutes sont rejetées, aucune n’est préférée. Corrigez ou retirez les doublons dans le fichier.";
    expect(
      within(rejected)
        .getAllByRole("row")
        .map((row) => row.textContent),
    ).toEqual([
      "LigneMotif",
      `4${sentence} Autre ligne du fichier de même pièce et de même poste\u00a0: 5.`,
      `5${sentence} Autre ligne du fichier de même pièce et de même poste\u00a0: 4.`,
    ]);
    const differences = screen.getByRole("table", { name: "Écarts avec les données existantes" });
    expect(differences).toHaveTextContent("Ligne de coût réelFA-2026-0412, poste 10");
  });

  it("says the motive of the duplicate lines of actual costs in English, blank item included [WF-INTF-0080-A]", () => {
    serve({});
    open(report(example("import_actual_costs_duplicate_line") as Import), "en");
    const rejected = screen.getByRole("table", { name: "Rejected lines" });
    expect(rejected).toHaveTextContent(/blank item included/);
  });

  it("lists the rejected lines with their tab, their row and their motive before any confirmation, and applies nothing until confirmed [WF-INTF-0080-A]", async () => {
    const client = serve({
      [APPLY]: { example: "task_import_queued", status: 202 },
      [TASK]: "task_running",
    });
    const { container } = open(report(example("import_analysed") as Import));
    const section = screen.getByRole("region", {
      name: "Compte rendu de l’import « devis-avenant-2-reprise-des-essais.xlsx »",
    });
    const rejected = within(section).getByRole("table", { name: "Lignes rejetées" });
    expect(
      within(rejected)
        .getAllByRole("row")
        .map((row) => row.textContent),
    ).toEqual([
      "OngletLigneMotif",
      "Hors lot3Tâche inconnue. Valeur lue dans le fichier\u00a0: «\u00a0Essais de compatibilité électromagnétique\u00a0».",
      "Hors lot5Rôle de ressource inconnu. Valeur lue dans le fichier\u00a0: «\u00a0Soudeur (SOUD)\u00a0».",
    ]);

    const confirmation = await askApplication();
    expect(within(confirmation).getByRole("paragraph")).toHaveTextContent(
      "Appliquer au projet l’import « devis-avenant-2-reprise-des-essais.xlsx », en une seule opération ?",
    );
    expect(
      within(confirmation).getByRole("button", { name: "Confirmer l’application" }),
    ).toHaveFocus();
    expect(client.calls).toEqual([]);
    await expectAccessible(container);

    await confirmApplication(confirmation);
    await closed();
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [`/projects/${PROJECT}/imports/${IMPORT}/apply`, { confirmed: true }],
    ]);
    expect(screen.getByRole("button", { name: "Appliquer l’import" })).toHaveFocus();
    expect(
      taskLine("Application d’un import « devis-avenant-2-reprise-des-essais.xlsx »"),
    ).toBeVisible();
  });

  it("leads to the screen it was given only once the task that applies the import has succeeded, not when the application is accepted", async () => {
    serve({
      [APPLY]: { example: "task_import_queued", status: 202 },
      [TASK]: "task_import_succeeded",
    });
    const entry = example("import_analysed") as Import;
    const offers = importOffers(example("project") as Project);
    const planning = `/projects/${PROJECT}/revisions/${REVISION}/planning`;
    open(
      <ImportReport
        projectId={PROJECT}
        entry={entry}
        offer={offers[entry.kind]}
        start={START}
        then={planning}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Appliquer l’import" }));
    expect(router.push).not.toHaveBeenCalled();
    const confirmation = screen.getByRole("form", { name: "Confirmation de l’application" });
    await confirmApplication(confirmation);
    await closed();
    // Accepted, and still applying: the planning is not filled yet.
    expect(router.push).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await waitFor(() => {
      expect(router.push).toHaveBeenCalledWith(planning);
    });
    expect(router.push).toHaveBeenCalledOnce();
  });

  it("leads nowhere when the user left the report before the task that applies the import succeeded", async () => {
    serve({
      [APPLY]: { example: "task_import_queued", status: 202 },
      [TASK]: "task_import_succeeded",
    });
    const entry = example("import_analysed") as Import;
    const offers = importOffers(example("project") as Project);
    const planning = `/projects/${PROJECT}/revisions/${REVISION}/planning`;
    const view = open(
      <ImportReport
        projectId={PROJECT}
        entry={entry}
        offer={offers[entry.kind]}
        start={START}
        then={planning}
      />,
    );
    const confirmation = await askApplication();
    await confirmApplication(confirmation);
    await closed();
    // The user goes elsewhere: the report is gone, the tracker stays and follows the task.
    view.rerender(shell(<p>Ailleurs</p>));
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await waitFor(() => expect(taskLine(/Application d’un import/)).toBeVisible());
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    // The task did succeed, the report not being there to lead anywhere.
    await waitFor(() => {
      expect(screen.getByRole("log")).toHaveTextContent("Tâche terminée : Application d’un import");
    });
    expect(router.push).not.toHaveBeenCalled();
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

    const confirmation = await askApplication();
    // Whether the confirmation was still busy in the commit that told the refusal: the request over, never
    // while it holds a press (#1484).
    const busyWhenTold = atCommit(
      confirmation,
      () => within(confirmation).queryByRole("alert") !== null,
      () => confirmation.getAttribute("aria-busy"),
    );
    await confirmApplication(confirmation);
    await settled(confirmation);
    expect(within(confirmation).getByRole("alert")).toHaveTextContent(
      CATALOGUES.fr.errors.STATE_FORBIDS_OPERATION,
    );
    expect(busyWhenTold.stop()).toEqual(["false"]);
    expect(within(tasksRegion()).queryByText(/Application d’un import/)).toBeNull();
  });

  it("presents a file the report rejects whole by its reasons, naming the tasks, and offers its abandonment alone [WF-INTF-0040-A]", () => {
    serve({});
    open(report(example("import_planning_rejected") as Import));
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("2 motifs rejettent le fichier entier");
    expect(alert).toHaveTextContent(
      /La tâche d’un poste doit rester dans le sous-arbre de la tâche de son lot\. Tâche du lot\s:\s« Poste de commande »\. Tâche du poste en cause\s:\s« Câblage des armoires »\./,
    );
    expect(alert).toHaveTextContent(
      /La durée du projet dépasserait quinze ans\.\s*Tâche en cause\s:\s« Mise en service »\./,
    );
    expect(screen.queryByRole("button", { name: "Appliquer l’import" })).toBeNull();
    expect(screen.getByRole("button", { name: "Abandonner l’import" })).toBeInTheDocument();
  });

  it("tells the condition a file rejected whole misses when the server refuses its application [WF-INTF-0040-A]", async () => {
    serve({ [APPLY]: { problem: example("import_apply_rejected") as Problem & { status: 409 } } });
    open(report(example("import_analysed") as Import));
    const confirmation = await askApplication();
    await confirmApplication(confirmation);
    await settled(confirmation);
    expect(within(confirmation).getByRole("alert")).toHaveTextContent(
      "Condition non remplie : fichier accepté par le compte rendu",
    );
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
    expect(within(screen.getByRole("main")).queryByRole("button")).toBeNull();
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

  it("names a column the file kept as the file names it, beside the columns its catalogue names", () => {
    serve({});
    open(report(example("import_actual_costs_analysed") as Import), "en");
    const differences = screen.getByRole("table", { name: "Differences with the existing data" });
    // `passthrough.Fournisseur`, a column of the file no catalogue translates (#365).
    // The line is designated by its document and its item (US-0630); a line with no item, by its
    // document alone.
    expect(differences).toHaveTextContent("FA-2026-0412, item 10Amount and Fournisseur");
    expect(differences).toHaveTextContent("AV-2026-0388Subproject");
  });

  it("names the parent a node changes, which no column of the structure holds", () => {
    // The differences of the merge of amendment 2, which moves « Mise en service » under « Essais
    // sur site » (#1194): `ImportDifference`, the one schema of the differences of an import.
    const { differences: moved } = example("structure_merge_report") as Pick<Report, "differences">;
    const entry = example("import_planning_mismatch") as Import & { report: Report };
    serve({});
    open(report({ ...entry, report: { ...entry.report, differences: moved } }));
    const differences = screen.getByRole("table", { name: "Écarts avec les données existantes" });
    expect(differences).toHaveTextContent("ModifiéTâcheMise en serviceDurée et Rattachement");
  });

  it("says how many of the lines read the import leaves as they are, and the lines of provision it leaves untouched [WF-INTF-0140-A] [WF-INTF-0100-A]", () => {
    serve({});
    open(report(example("import_remaining_analysed") as Import));
    expect(screen.getByText(/lignes lues\./)).toHaveTextContent(
      "3 lignes lues. Parmi elles, aucune n’est inchangée.",
    );
    expect(
      screen.getByText(/Lignes de provision d’un risque, laissées telles quelles/),
    ).toHaveTextContent(
      "Lignes de provision d’un risque, laissées telles quelles (1) : Provision — risque de reprise du câblage",
    );
  });

  it("counts the lines of a file of a planning left as they are, in English [WF-INTF-0140-A]", () => {
    serve({});
    open(report(example("import_planning_non_working_day") as Import), "en");
    expect(screen.getByText(/lines read\./)).toHaveTextContent(
      "1,000 lines read. Of these, 999 are unchanged.",
    );
  });

  it("names the sub-project a line cannot leave, and the label two tasks share, in the motive of the line rejected [WF-INTF-0100-A] [WF-INTF-0120-A]", () => {
    serve({});
    const held = open(report(example("import_remaining_subproject_held") as Import));
    expect(screen.getByRole("table", { name: "Lignes rejetées" })).toHaveTextContent(
      "3Cette ligne ne peut pas quitter ce sous-projet",
    );
    expect(screen.getByRole("table", { name: "Lignes rejetées" })).toHaveTextContent(
      "« Poste de commande »",
    );
    held.unmount();
    open(report(example("import_remaining_ambiguous_label") as Import));
    expect(screen.getByRole("table", { name: "Lignes rejetées" })).toHaveTextContent(
      "3Ce libellé est porté par plusieurs tâches",
    );
    expect(screen.getByRole("table", { name: "Lignes rejetées" })).toHaveTextContent(
      "Libellé lu : « Mise en service », porté par les tâches « Mise en service » et « Mise en service ».",
    );
  });

  it("names the value no object has, in the motive of the line rejected [WF-INTF-0080-A]", () => {
    serve({});
    open(report(example("import_analysed") as Import));
    const rejected = screen.getByRole("table", { name: "Lignes rejetées" });
    expect(rejected).toHaveTextContent(
      "Valeur lue dans le fichier : « Essais de compatibilité électromagnétique ».",
    );
    expect(rejected).toHaveTextContent("Valeur lue dans le fichier : « Soudeur (SOUD) ».");
  });

  it("names the rank of the other line of the same document and item, in the motive of each line rejected [WF-INTF-0080-A]", () => {
    serve({});
    open(report(example("import_actual_costs_duplicate_line") as Import));
    const rows = within(screen.getByRole("table", { name: "Lignes rejetées" })).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Autre ligne du fichier de même pièce et de même poste : 5.");
    expect(rows[2]).toHaveTextContent("Autre ligne du fichier de même pièce et de même poste : 4.");
  });

  it("names the element of work breakdown a line of actual cost is rejected for [WF-CRE-0020-A]", () => {
    serve({});
    open(report(example("import_actual_costs_wbs_invalid") as Import));
    expect(screen.getByRole("table", { name: "Lignes rejetées" })).toHaveTextContent(
      "5L’élément d’OTP de la ligne n’a pas la forme attendue",
    );
    expect(screen.getByRole("table", { name: "Lignes rejetées" })).toHaveTextContent(
      "Élément d’OTP lu : « /SP-CAB ».",
    );
  });

  it("names each task the file dates otherwise than Waterfall computes it, with the columns that differ, as information and not a reason to confirm", () => {
    serve({});
    open(report(example("import_planning_mismatch") as Import));
    const table = screen.getByRole("table", { name: "Tâches datées autrement par le fichier" });
    expect(
      within(table)
        .getAllByRole("row")
        .map((row) => row.textContent),
    ).toEqual(["TâcheChamps", "ÉtudesFin", "Revue de conceptionFin"]);
    expect(screen.getByText(/^2 tâches datées autrement par le fichier/)).toBeVisible();
  });

  it("says the change of the date of start of planning of the structure, which no column holds [WF-INTF-0040-A]", () => {
    serve({});
    open(report(example("import_planning_mismatch") as Import));
    const differences = screen.getByRole("table", { name: "Écarts avec les données existantes" });
    expect(differences).toHaveTextContent("ModifiéStructure de coûts");
    expect(differences).toHaveTextContent("Date de début de planning");
  });

  it("tells each value of the file the import keeps or corrects, with its column and its sentence [WF-INTF-0040-A] [WF-PLA-0020-A]", () => {
    serve({});
    const day = open(report(example("import_planning_non_working_day") as Import));
    const kept = screen.getByRole("table", { name: "Valeurs du fichier gardées et signalées" });
    expect(kept).toHaveTextContent(
      "Mise en serviceDébutJour non travailléDate sur un jour sans heure travaillée. Le samedi 19 décembre n’est pas travaillé sur le calendrier de la tâche ; saisis le lundi 21 décembre.",
    );
    day.unmount();
    open(report(example("import_planning_mismatch") as Import));
    expect(
      screen.getByRole("table", { name: "Valeurs du fichier gardées et signalées" }),
    ).toHaveTextContent(
      "ÉtudesMode de planificationTâche récapitulative dérivée de ses tâchesUne tâche récapitulative tient ses valeurs de ses subordonnées. Ses dates courent du lundi 2 mars au jeudi 30 avril, celles de ses subordonnées.",
    );
  });

  it("names the tasks the import completes with the date of the review the file bears, not the day of the import [WF-INTF-0120-A] [WF-INTF-0130-A]", () => {
    const entry = example("import_remaining_completed_tasks") as Import;
    serve({});
    open(report(entry));
    const table = screen.getByRole("table", { name: "Tâches terminées par l’import" });
    expect(
      within(table)
        .getAllByRole("row")
        .map((row) => row.textContent),
    ).toEqual(["TâcheTerminée le", "Mise en service1 juin 2026", "Revue 1.2.111 juin 2026"]);
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
    const download = await within(tasksRegion()).findByRole("link", {
      name: "Télécharger le résultat : Export « Devis »",
    });
    expect(download.getAttribute("href")).toMatch(
      /^\/tasks\/01926f3a-7c00-7000-8000-000000000935\/result\?from=/,
    );
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
    // Whether the request was still busy in the commit that told the refusal: the request over, never
    // while it holds a press (#1484).
    const busyWhenTold = atCommit(
      form,
      () => within(form).queryByRole("alert") !== null,
      () => form.getAttribute("aria-busy"),
    );
    await userEvent.click(within(form).getByRole("button", { name: "Demander l’export" }));
    await settled(form);
    expect(client.calls.map((call) => call.body)).toEqual([
      { kind: "estimate", revision_id: REVISION },
    ]);
    expect(within(form).getByRole("alert")).toHaveTextContent(
      CATALOGUES.fr.errors.PERMISSION_MISSING,
    );
    expect(busyWhenTold.stop()).toEqual(["false"]);
  });

  it("holds a link clicked while the export is asked, and does not follow it when the server refuses it (#688)", async () => {
    let release: () => void = () => undefined;
    const released = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.client = fakeClient(
      { [EXPORT]: { problem: { code: "PERMISSION_MISSING", status: 403 } } },
      { hold: () => released },
    );
    open(exportForm("revision_estimator"));
    const link = heldLink();
    try {
      const form = screen.getByRole("form", { name: "Demander un export" });
      await userEvent.click(within(form).getByRole("button", { name: "Demander l’export" }));
      link.click();
      await act(async () => {
        release();
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
      await settled(form);
      expect(within(form).getByRole("alert")).toHaveTextContent(
        CATALOGUES.fr.errors.PERMISSION_MISSING,
      );
      expect(link.followed).not.toHaveBeenCalled();
    } finally {
      link.remove();
    }
  });

  it("keeps an export the revision lists unavailable, its request told what it lacks and asking nothing", async () => {
    const client = serve({});
    // The contract lists an export present or absent; one it listed unavailable would stay (#361).
    const revision = structuredClone(example("revision") as Revision);
    for (const command of revision.available_commands) {
      if (command.command === "export_estimate") {
        command.is_available = false;
        command.missing_conditions = ["revision_marked"];
      }
    }
    open(<ExportForm projectId={PROJECT} revisionId={REVISION} offers={exportOffers(revision)} />);
    const form = screen.getByRole("form", { name: "Demander un export" });
    await userEvent.selectOptions(within(form).getByLabelText("Fichier à exporter"), "Devis");
    const request = within(form).getByRole("button", { name: "Demander l’export" });
    expect(request).toHaveAttribute("aria-disabled", "true");
    expect(request).toHaveAccessibleDescription("Condition non remplie\u00A0: révision marquée.");
    await userEvent.click(request);
    expect(client.calls).toEqual([]);
  });

  it("says no export is offered without a revision that offers one", () => {
    serve({});
    open(<ExportForm projectId={PROJECT} revisionId={REVISION} offers={exportOffers(undefined)} />);
    expect(screen.queryByRole("form")).toBeNull();
    expect(screen.getByText("Aucun export ne vous est offert sur cette révision.")).toBeVisible();
  });

  it("asks the date of the review the file of a remaining to commit bears, the day of the request when it gives none [WF-INTF-0130-A]", async () => {
    const client = serve({ [EXPORT]: { example: "task_export_queued", status: 202 } });
    open(exportForm());
    const form = screen.getByRole("form", { name: "Demander un export" });
    expect(within(form).queryByLabelText("Date de la revue")).toBeNull();
    await userEvent.selectOptions(
      within(form).getByLabelText("Fichier à exporter"),
      "Reste à engager",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Demander l’export" }));
    await settled(form);
    await userEvent.type(within(form).getByLabelText("Date de la revue"), "2026-05-29");
    await userEvent.click(within(form).getByRole("button", { name: "Demander l’export" }));
    await settled(form);
    expect(client.calls.map((call) => call.body)).toEqual([
      { kind: "remaining", revision_id: REVISION, review_date: null },
      { kind: "remaining", revision_id: REVISION, review_date: "2026-05-29" },
    ]);
  });
});
