// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFile } from "node:fs/promises";

import { expect, type Route } from "@playwright/test";

import catalogue from "../messages/fr.json" with { type: "json" };
import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { seedPlanning } from "./planning-seed";
import { API } from "./service/realm";

// The last path below is the service's, tagged `@shared` (US-1430): the export of the planning in MS
// Project XML, downloaded once, and imported back, on a project the run creates. The others keep to the
// fake back, which is the only one to serve the estimate and its examples.
//
// The fake back serves the first example of each operation: the file deposited, its import
// opened, its analysis under way; the report the address then names, the estimate analysed this
// morning and applicable until tomorrow — two lines rejected —; the application queued; the
// abandonment. It keeps no state: the component and page
// tests prove the other states of an import (`exchanges.dom.test.tsx`, `page.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IMPORT = "01926f3a-7c00-7000-8000-000000000a11";
const PLANNING = `/projects/${PROJECT}/revisions/${REVISION}/planning?as_of=2026-05-31`;
const START = `/projects/${PROJECT}/revisions/${REVISION}/exchanges?as_of=2026-05-31`;
// The task of the application queued (`task_import_queued`), which the tracker reads by its id.
const APPLICATION = "01926f3a-7c00-7000-8000-000000000932";

test("imports a file in two steps: the report lists the lines rejected with their motive before any confirmation, the application confirmed is followed in the shell, and the abandonment leads back to the screen as it was [WF-INTF-0080-A]", async ({
  page,
}) => {
  // The read of the application's task waits for the test to let it: the fake back would answer
  // it with its first example, a marking, under the name of the import.
  let release!: () => void;
  const released = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/projects/**", async (route: Route) => {
    if (route.request().postData()?.includes(APPLICATION) === true) {
      await released;
    }
    await route.fallback();
  });
  // The screen reached by a click, compiled first; the head of the planning leads to it, the
  // context kept.
  await compile(page.request, START);
  await openHydrated(page, PLANNING);
  await page.getByRole("main").getByRole("link", { name: "Imports et exports" }).click();
  await expect(page).toHaveURL(START);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Imports et exports");
  const imports = page.getByRole("region", { name: "Importer un fichier" });
  await imports.getByRole("button", { name: "Importer un devis" }).click();
  const form = imports.getByRole("form", { name: "Importer un devis" });
  await form.getByLabel("Fichier à importer").setInputFiles({
    name: "devis-avenant-2-reprise-des-essais.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: Buffer.from("devis"),
  });
  await form.getByRole("button", { name: "Analyser le fichier" }).click();

  // The report of the import the analysis opened, its lines rejected each with its tab and its motive.
  await expect(page).toHaveURL(`${START}&import=${IMPORT}`);
  const report = page.getByRole("region", {
    name: "Compte rendu de l’import « devis-avenant-2-reprise-des-essais.xlsx »",
  });
  const rejected = report.getByRole("table", { name: "Lignes rejetées" }).getByRole("row");
  await expect(rejected).toHaveText([
    /Onglet\s*Ligne\s*Motif/,
    /Hors lot\s*3\s*Tâche inconnue\./,
    /Hors lot\s*5\s*Rôle de ressource inconnu\./,
  ]);
  await expect(report.getByText("5 lignes lues.")).toBeVisible();
  await expect(report.getByText("Parmi elles, 1 est inchangée.")).toBeVisible();

  // Nothing is applied before the confirmation; confirmed, the application is a task followed.
  const read = page.waitForRequest((request) => request.postData()?.includes(APPLICATION) === true);
  await report.getByRole("button", { name: "Appliquer l’import" }).click();
  const confirmation = report.getByRole("form", { name: "Confirmation de l’application" });
  await confirmation.getByRole("button", { name: "Confirmer l’application" }).click();
  await expect(confirmation).toHaveCount(0);
  await page.getByRole("button", { name: /^Tâches et messages\s:/ }).click();
  const panel = page.getByRole("dialog", { name: "Tâches et messages" });
  const tasks = panel.getByRole("region", { name: "Tâches de fond" });
  const application = "Application d’un import « devis-avenant-2-reprise-des-essais.xlsx »";
  await expect(tasks.getByText(application)).toBeVisible();
  await expect(tasks.getByRole("progressbar", { name: application })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await read;
  release();

  // Abandoned, the import leaves the screen as it was before it.
  await report.getByRole("button", { name: "Abandonner l’import" }).click();
  await expect(page).toHaveURL(START);
  await expect(report).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Imports du projet" })).toBeVisible();
});

test("refuses in the form a file larger than an import takes, before anything is sent", async ({
  page,
}) => {
  const sent: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST") {
      sent.push(request.url());
    }
  });
  await openHydrated(page, START);
  const imports = page.getByRole("region", { name: "Importer un fichier" });
  await imports.getByRole("button", { name: "Importer un planning MS Project" }).click();
  const form = imports.getByRole("form", { name: "Importer un planning MS Project" });
  const field = form.getByLabel("Fichier à importer");
  // Eleven mebibytes: past the ten an import takes, under the bound of the server actions.
  await field.setInputFiles({
    name: "planning-poste-de-commande.xml",
    mimeType: "application/xml",
    buffer: Buffer.alloc(11 * 1024 * 1024),
  });
  await form.getByRole("button", { name: "Analyser le fichier" }).click();
  await expect(form.getByRole("alert")).toHaveText(
    "Le fichier dépasse 10 Mio, la plus grande taille qu’un import admet.",
  );
  await expect(field).toBeFocused();
  await expect(page).toHaveURL(START);
  expect(sent).toEqual([]);
});

test("the estimate and the remaining to commit lead to the one screen of the imports, in the same context, when the project lists their import (#521)", async ({
  page,
}) => {
  // A costing engineer who does not read the planning reaches the imports so; the fake back
  // grants every permission, and lists both imports available.
  const estimate = `/projects/${PROJECT}/revisions/${REVISION}/estimate?as_of=2026-05-31`;
  const remaining = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
  await compile(page.request, START, remaining);
  await page.goto(estimate);
  await page.getByRole("main").getByRole("link", { name: "Imports et exports" }).click();
  await expect(page).toHaveURL(START);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Imports et exports");
  await page.goto(remaining);
  await expect(
    page.getByRole("main").getByRole("link", { name: "Imports et exports" }),
  ).toHaveAttribute("href", `/projects/${PROJECT}/revisions/${REVISION}/exchanges`);
});

test("exports the planning as MS Project XML, downloads it once, and imports it back with no difference, as the project manager of the run @shared [WF-DAT-0120-A] [WF-INTF-0010-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  // WF-INTF-0010-A (FLX-01): the account of the run, holding « Chef de projet » beside « Manager », exports
  // the planning and imports the MS Project file back, to the report, on a project it created.
  // The project manager account reaches the exchange screen; an export downloaded to the end is no
  // longer available (WF-DAT-0120-A); the report of the analysis of the planning imported back shows no
  // difference of dates or durations. The full round trip is proved by the back's `test_msproject_export.py`.
  test.skip(
    !inService,
    "the service keeps the file made and the import applied, the fake back not",
  );
  test.slow();
  const seeded = await seedPlanning(page, browser, request, manager, "Échanges", { links: true });
  const screen = `${seeded.revision}/exchanges`;
  await openHydrated(page, screen);

  // The export of the schedule, the first the revision offers: a task followed in the shell.
  const exports = page.getByRole("region", { name: "Demander un export" });
  await expect(
    exports.getByRole("combobox", { name: "Fichier à exporter" }).getByRole("option").first(),
  ).toHaveText("Planning MS Project", { timeout: WORKING });
  await exports.getByRole("button", { name: "Demander l’export" }).click();
  await page.getByRole("button", { name: /^Tâches et messages\s:/ }).click();
  const panel = page.getByRole("dialog", { name: "Tâches et messages" });
  const tasks = panel.getByRole("region", { name: "Tâches de fond" });
  const link = tasks.getByRole("link", { name: /^Télécharger le résultat/ });
  await expect(link).toBeVisible({ timeout: WORKING });
  const result = await link.getAttribute("href");
  expect(result).toMatch(/^\/tasks\/[0-9a-f-]{36}\/result\?/);

  // Downloaded: a file named after the project, which is the XML of MS Project.
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  expect(download.suggestedFilename()).toMatch(/^ms-project(-.+)?\.xml$/);
  const xml = await readFile(await download.path());
  const text = xml.toString("utf8");
  expect(text).toContain("<Project");
  for (const label of ["Études de détail", "Revue de conception", "Mise en service"]) {
    expect(text).toContain(label);
  }

  // The service deletes the object and marks the result consumed after the last byte: wait for it
  // (`result_url` null) before the second navigation, or it could download again.
  const task = /^\/tasks\/([0-9a-f-]{36})\/result\?/.exec(result ?? "")?.[1] ?? "";
  await expect(async () => {
    const read = await request.get(`${API}/tasks/${task}`, { headers: seeded.headers });
    expect(read.status(), "GET task").toBe(200);
    expect(((await read.json()) as { result_url: string | null }).result_url).toBeNull();
  }).toPass({ timeout: WORKING });

  // The result is gone once downloaded to the end: the route follows to the screen it left, and the
  // task tells the refusal.
  await page.evaluate((address) => {
    window.location.assign(address);
  }, result ?? "");
  await expect(page).toHaveURL(screen, { timeout: WORKING });
  await expect(page.getByRole("region", { name: "Tâches de fond" }).getByRole("alert")).toBeVisible(
    { timeout: WORKING },
  );
  await page.keyboard.press("Escape");

  // Imported back: analysed, the report reads every task, with no difference to the planning.
  const imports = page.getByRole("region", { name: "Importer un fichier" });
  await imports.getByRole("button", { name: "Importer un planning MS Project" }).click();
  const form = imports.getByRole("form", { name: "Importer un planning MS Project" });
  await form.getByLabel("Fichier à importer").setInputFiles({
    name: download.suggestedFilename(),
    mimeType: "application/xml",
    buffer: xml,
  });
  await form.getByRole("button", { name: "Analyser le fichier" }).click();
  await expect(page).toHaveURL(/[?&]import=[0-9a-f-]{36}/, { timeout: WORKING });
  const report = page.getByRole("region", {
    name: `Compte rendu de l’import « ${download.suggestedFilename()} »`,
  });
  // The analysis is a task of the background: the report comes when the screen is read anew.
  await expect(async () => {
    if ((await report.getByText(/lignes lues\./).count()) === 0) {
      await page.reload();
    }
    await expect(report.getByText(/lignes lues\./)).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  await expect(report.getByText("Aucun écart avec les données existantes")).toBeVisible();
  await expect(report.getByRole("table", { name: "Lignes rejetées" })).toHaveCount(0);
  await expect(
    report.getByRole("table", { name: "Tâches datées autrement par le fichier" }),
  ).toHaveCount(0);
  // Exported and imported by the same installation, the file bears its constants: nothing to signal.
  await expect(
    report.getByText(catalogue.exchanges.report.unitConstants.split("{", 1).join("").trim()),
  ).toHaveCount(0);
});
