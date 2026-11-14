// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only

import { readFileSync } from "node:fs";

import {
  type APIRequestContext,
  expect,
  type Locator,
  type Page,
  type Request,
  type Route,
} from "@playwright/test";

import catalogue from "../messages/fr.json" with { type: "json" };
import type { components } from "../src/api/generated/schema";
import type { Answer } from "./answer";
import { compile } from "./compile";
import { downloaded } from "./download";
import { seedEstimate } from "./estimate-seed";
import { openHydrated, WORKING } from "./hydration";
import { takeInProgress } from "./in-progress";
import { inService, test } from "./mode";
import { employRole, wiringService } from "./own-project";
import { seedPlanning } from "./planning-seed";
import { API } from "./service/realm";

const gap = catalogue.exchanges.report.calendarGap;
const rules = catalogue.enums.ImportDurationRule;

// The last two paths below are the service's, tagged `@shared`, on a project the run creates: the
// export of the planning in MS Project XML, downloaded once, and imported back (US-1430); and the
// import of an estimate in two steps (US-1550) — exported in Excel, downloaded, imported back, its
// report read, its application confirmed —, a file that is no estimate refused before it. The
// others keep to the fake back, which serves the examples of the operations without keeping any
// state: the first, the lines rejected by the report of an import in two steps, and its abandonment.
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

type Schemas = components["schemas"];

/** What `applyAndFollow` is given: the screen it acts on, and the import it reads back. */
interface Application {
  readonly page: Page;
  /** The report of the import, which carries the command that applies it. */
  readonly report: Locator;
  /** The background tasks of the shell, where the application is followed. */
  readonly tasks: Locator;
  /** The name of the file imported, as the task names it. */
  readonly filename: string;
  /** The context that reads the import back, at `address`, under `headers`. */
  readonly request: APIRequestContext;
  readonly address: string;
  readonly headers: Readonly<Record<string, string>>;
}

/**
 * Apply the import of a report and confirm it, follow the application as a task of the shell to its
 * success, and wait for the service to hold the import applied.
 */
async function applyAndFollow({
  page,
  report,
  tasks,
  filename,
  request,
  address,
  headers,
}: Application): Promise<void> {
  await report.getByRole("button", { name: "Appliquer l’import" }).click();
  const confirmation = report.getByRole("form", { name: "Confirmation de l’application" });
  await confirmation.getByRole("button", { name: "Confirmer l’application" }).click();
  await expect(confirmation).toHaveCount(0);
  await page.getByRole("button", { name: /^Tâches et messages\s:/ }).click();
  const application = tasks
    .getByRole("listitem")
    .filter({ hasText: `Application d’un import « ${filename} »` });
  await expect(application.getByText("Réussie")).toBeVisible({ timeout: WORKING });
  await page.keyboard.press("Escape");
  await expect(async () => {
    const applied = await request.get(address, { headers });
    expect(applied.status(), "GET import").toBe(200);
    expect(((await applied.json()) as Schemas["ImportDetail"]).status).toBe("applied");
  }).toPass({ timeout: WORKING });
}

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

test("offers no choice of the duration rule on the report of an import without a calendar gap, the first example of the fake back [WF-PLA-0160-A] [WF-INTF-0080-A]", async ({
  page,
}) => {
  // The fake back serves the first example of each read, which no calendar gap marks: the report of
  // the import carries none, so neither the gap nor the choice is on the screen — what a file
  // exported by Waterfall shows. The report in gap, and the change of rule, are proved by
  // `calendar-gap.dom.test.tsx` on the examples of the contract (`import_planning_calendar_gap`,
  // `import_duration_rule_set`): prism cannot be asked another example of a server read.
  await openHydrated(page, `${START}&import=${IMPORT}`);
  const report = page.getByRole("region", { name: /^Compte rendu de l’import/ });
  await expect(report.getByText("5 lignes lues.")).toBeVisible();
  await expect(report.getByRole("radio")).toHaveCount(0);
  await expect(report.getByText(gap.title)).toHaveCount(0);
  await expect(report.getByRole("button", { name: "Appliquer l’import" })).toBeVisible();
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

test("exports the planning as MS Project XML, downloads it once, and imports it back with no difference, as the project manager of the run @shared [WF-DAT-0120-A] [WF-INTF-0010-A] [WF-PLA-0160-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  // WF-INTF-0010-A (FLX-01): the account of the run, holding « Chef de projet » beside « Manager », exports
  // the planning and imports the MS Project file back, to the report, on a project it created.
  // The project manager account reaches the exchange screen; an export downloaded to the end is no
  // longer available (WF-DAT-0120-A); the report of the analysis of the planning imported back shows no
  // difference of dates or durations; the import confirmed is applied, its task followed in the shell.
  // The full round trip is proved by the back's `test_msproject_export.py`.
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
  const xml = await downloaded(download);
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
    expect(((await read.json()) as Schemas["BackgroundTaskRef"]).result_url).toBeNull();
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
  const opened = new URL(page.url()).searchParams.get("import") ?? "";
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

  // No calendar gap, so no choice of the duration rule (WF-PLA-0160-A): the service's report, which
  // the fake back's example cannot prove for this path, carries none.
  await expect(report.getByRole("radio")).toHaveCount(0);
  await expect(report.getByText(gap.title)).toHaveCount(0);

  // Confirmed, the application is a task followed in the shell, to its success (WF-INTF-0010-A: the
  // account leads the flow to its end, #2683), and the service holds the import applied.
  const address = `${API}/projects/${seeded.ids.project}/imports/${opened}`;
  await applyAndFollow({
    page,
    report,
    tasks,
    filename: download.suggestedFilename(),
    request,
    address,
    headers: seeded.headers,
  });
});

test("exports the estimate as an Excel file, downloads it, sees a file that is no estimate refused, then imports the file back in two steps — the report without a difference, the application confirmed and followed in the shell, the lines identical — as the project manager of the run @shared [WF-INTF-0070-A] [WF-INTF-0110-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  // The criterion proper to US-1550: the screen of the exchanges imports and exports an estimate
  // against the service, and the import in two steps is played on a project the run creates.
  // WF-INTF-0110-A: the export of the estimate is a task of the shell, its file named after the
  // revision; exported, then imported back without a change into the revision in progress, the
  // report says no difference, and the lines are the same. The report comes before any
  // confirmation, and the application confirmed is followed in the shell; the lines a report
  // rejects and the abandonment, which WF-INTF-0080-A verifies, stay with the fake back (« imports
  // a file in two steps », above), the exported workbook having no line to reject. The workbook
  // goes to the browser and back to the API byte for byte: the proxy of the contract carries the
  // bytes of a body that is not JSON past Prism (`bench/contract-proxy.ts`, #2687).
  test.skip(
    !inService,
    "the service keeps the file made and the import applied, the fake back not",
  );
  test.slow();
  const seeded = await seedEstimate(page, browser, request, manager, "Devis");
  const screen = `${seeded.revision}/exchanges`;
  const nodes = `${API}/projects/${seeded.ids.project}/revisions/${seeded.ids.revision}/structures/${seeded.ids.structure}/nodes`;
  const lines = async (): Promise<unknown[]> => {
    const read = await request.get(nodes, { headers: seeded.headers });
    expect(read.status(), "GET nodes").toBe(200);
    return ((await read.json()) as Answer<"listNodes">).items.filter(
      ({ kind }) => kind === "estimate_line",
    );
  };
  const before = await lines();
  expect(before).toHaveLength(1);
  await openHydrated(page, screen);

  // The export of the estimate: chosen in the list of the files, followed in the shell.
  const exports = page.getByRole("region", { name: "Demander un export" });
  const kinds = exports.getByRole("combobox", { name: "Fichier à exporter" });
  await expect(kinds.getByRole("option", { name: "Devis" })).toHaveCount(1, { timeout: WORKING });
  await kinds.selectOption({ label: "Devis" });
  await exports.getByRole("button", { name: "Demander l’export" }).click();
  await page.getByRole("button", { name: /^Tâches et messages\s:/ }).click();
  const panel = page.getByRole("dialog", { name: "Tâches et messages" });
  const tasks = panel.getByRole("region", { name: "Tâches de fond" });
  const link = tasks.getByRole("link", { name: /^Télécharger le résultat/ });
  await expect(link).toBeVisible({ timeout: WORKING });
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  const filename = download.suggestedFilename();
  expect(filename).toMatch(/-devis\.xlsx$/);
  // A workbook is a zip archive, whose bytes past 0x7f Prism would have rewritten.
  const workbook = await downloaded(download);
  expect(workbook.subarray(0, 4)).toEqual(Buffer.from([0x50, 0x4b, 0x03, 0x04]));
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);

  // A file that is no estimate is refused at the analysis, under the form, with the format and the
  // version the service expects (WF-INTF-0070-A); the project is untouched, the screen as it was.
  const imports = page.getByRole("region", { name: "Importer un fichier" });
  await imports.getByRole("button", { name: "Importer un devis" }).click();
  const form = imports.getByRole("form", { name: "Importer un devis" });
  const field = form.getByLabel("Fichier à importer");
  await field.setInputFiles({
    name: "pas-un-devis.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: Buffer.from("pas un classeur"),
  });
  await form.getByRole("button", { name: "Analyser le fichier" }).click();
  await expect(form.getByRole("alert")).toHaveText(
    "Le format du fichier est illisible. Format attendu : Devis. Version attendue : 1.",
    { timeout: WORKING },
  );
  await expect(page).not.toHaveURL(/[?&]import=/);
  // The project is unchanged: the form stays open, no report is shown, and the service holds no
  // import for the project.
  await expect(form).toBeVisible();
  await expect(page.getByRole("region", { name: /^Compte rendu/ })).toHaveCount(0);
  const listed = await request.get(`${API}/projects/${seeded.ids.project}/imports`, {
    headers: seeded.headers,
  });
  expect(listed.status(), "GET imports").toBe(200);
  expect(((await listed.json()) as Answer<"listImports">).items).toEqual([]);

  // The workbook exported, imported back as it is: analysed, the report reads its lines, every one
  // unchanged, with no difference and no line rejected — before anything is applied.
  await field.setInputFiles({
    name: filename,
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: workbook,
  });
  await form.getByRole("button", { name: "Analyser le fichier" }).click();
  await expect(page).toHaveURL(/[?&]import=[0-9a-f-]{36}/, { timeout: WORKING });
  const opened = new URL(page.url()).searchParams.get("import") ?? "";
  const report = page.getByRole("region", { name: `Compte rendu de l’import « ${filename} »` });
  // The analysis is a task of the background: the report comes when the screen is read anew.
  await expect(async () => {
    if ((await report.getByText(/lues?\./).count()) === 0) {
      await page.reload();
      await page.waitForLoadState("domcontentloaded");
    }
    await expect(report.getByText(/lues?\./)).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING, intervals: [500, 1_000, 2_000] });
  await expect(report.getByText("Aucun écart avec les données existantes")).toBeVisible();
  await expect(report.getByRole("table", { name: "Lignes rejetées" })).toHaveCount(0);
  const address = `${API}/projects/${seeded.ids.project}/imports/${opened}`;
  const analysed = await request.get(address, { headers: seeded.headers });
  expect(analysed.status(), "GET import").toBe(200);
  const { report: read } = (await analysed.json()) as Schemas["ImportDetail"];
  if (read === null) {
    throw new Error("the import analysed carries its report");
  }
  expect(read.read_count).toBeGreaterThan(0);
  expect(read.unchanged_count).toBe(read.read_count);
  expect(read.differences).toEqual([]);
  expect(await lines()).toEqual(before);

  // Confirmed, the application is a task followed in the shell, to its success.
  await applyAndFollow({
    page,
    report,
    tasks,
    filename,
    request,
    address,
    headers: seeded.headers,
  });

  // The lines obtained are the lines exported: the same, lineage and amounts.
  expect(await lines()).toEqual(before);
});

test("imports a planning typed at seven hours a day: the calendar gap is on the report before the confirmation, keeping the durations is the default, keeping the dates analyses again and the screen follows, the rule in force changes nothing, and the abandonment leaves the project unchanged, as the project manager of the run @shared [WF-INTF-0080-A] [WF-PLA-0160-A] [WF-INTF-0040-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  // Against the service only: the read of `?import=` and the `PUT …/duration-rule` leave the server
  // of Next, which `page.route` does not see, and Prism serves the first example (no gap).
  // #3153: the conversion under « Garder les dates » (two days of 7 h are 16 h or 15 h) and the
  // comparison of the differences of dates in gap are not settled: no duration converted and no
  // number of differences is asserted here, only the hours, the option and the choice.
  test.skip(!inService, "the service reads the import and changes its rule, the fake back not");
  test.slow();
  const seeded = await seedPlanning(page, browser, request, manager, "Écart");
  const screen = `${seeded.revision}/exchanges`;
  const base = `${API}/projects/${seeded.ids.project}`;
  const nodes = `${base}/revisions/${seeded.ids.revision}/structures/${seeded.ids.structure}/nodes`;
  const tasksOfProject = async (): Promise<unknown[]> => {
    const read = await request.get(nodes, { headers: seeded.headers });
    expect(read.status(), "GET nodes").toBe(200);
    return ((await read.json()) as Answer<"listNodes">).items;
  };
  const before = await tasksOfProject();
  expect(before.length).toBeGreaterThan(0);
  await openHydrated(page, screen);

  const imports = page.getByRole("region", { name: "Importer un fichier" });
  await imports.getByRole("button", { name: "Importer un planning MS Project" }).click();
  const form = imports.getByRole("form", { name: "Importer un planning MS Project" });
  const filename = "14-calendar-gap-seven-hours.xml";
  await form.getByLabel("Fichier à importer").setInputFiles({
    name: filename,
    mimeType: "application/xml",
    buffer: readFileSync(`${import.meta.dirname}/../../fixtures/msproject/${filename}`),
  });
  await form.getByRole("button", { name: "Analyser le fichier" }).click();
  await expect(page).toHaveURL(/[?&]import=[0-9a-f-]{36}/, { timeout: WORKING });
  const opened = new URL(page.url()).searchParams.get("import") ?? "";
  const address = `${base}/imports/${opened}`;
  const report = page.getByRole("region", { name: `Compte rendu de l’import « ${filename} »` });
  const keep = {
    durations: report.getByRole("radio", { name: new RegExp(`^${rules.keep_durations}`) }),
    dates: report.getByRole("radio", { name: new RegExp(`^${rules.keep_dates}`) }),
  };
  const reportRead = async () => {
    // The analysis is a task of the background: the report comes when the screen is read anew.
    await expect(async () => {
      if ((await report.getByText(/lignes lues\./).count()) === 0) {
        await page.reload();
        await page.waitForLoadState("domcontentloaded");
      }
      await expect(report.getByText(/lignes lues\./)).toBeVisible({ timeout: 1_000 });
    }).toPass({ timeout: WORKING, intervals: [500, 1_000, 2_000] });
  };
  await reportRead();

  // The gap is on the report, before any confirmation: the hours a day of the file (7) and of the
  // installation (8), the calendar of the file said ignored, the tasks on another calendar named.
  await expect(report.getByText(gap.title)).toBeVisible();
  const days = report.getByRole("table", {
    name: gap.daysTable,
  });
  const monday = days.getByRole("row", { name: /^Lundi/ });
  await expect(monday.getByRole("cell", { name: "7", exact: true })).toBeVisible();
  await expect(monday.getByRole("cell", { name: "8", exact: true })).toBeVisible();
  await expect(report.getByText(gap.ignored)).toBeVisible();
  const own = report.getByRole("table", {
    name: gap.tasksTable,
  });
  for (const label of ["Peinture", "Fabrication"]) {
    await expect(own.getByRole("cell", { name: label, exact: true })).toBeVisible();
  }
  await expect(report.getByRole("button", { name: "Appliquer l’import" })).toBeVisible();
  const detail = async (): Promise<Schemas["ImportDetail"]> => {
    const read = await request.get(address, { headers: seeded.headers });
    expect(read.status(), "GET import").toBe(200);
    return (await read.json()) as Schemas["ImportDetail"];
  };
  expect((await detail()).report?.calendar_gap?.duration_rule).toBe("keep_durations");

  // Keeping the durations is the default.
  await expect(keep.durations).toBeChecked();
  await expect(keep.dates).not.toBeChecked();

  // Keeping the dates analyses the import again (202), which the screen follows to the new report,
  // that carries the new option; the project is unchanged.
  await keep.dates.click();
  await expect(keep.dates).toBeChecked({ timeout: WORKING });
  await expect(async () => {
    expect((await detail()).report?.calendar_gap?.duration_rule).toBe("keep_dates");
  }).toPass({ timeout: WORKING });
  await reportRead();
  // The import went through a new analysis: it is analysed again, with the new report.
  expect((await detail()).status).toBe("analysed");
  await expect(keep.dates).toBeChecked();
  await expect(keep.durations).not.toBeChecked();
  await expect(report.getByText(gap.title)).toBeVisible();

  // The rule already in force answers 200 and changes nothing. The call of the screen leaves the
  // server of Next, which the browser does not see, and a radio already checked sends nothing: the
  // 200 is read by the same call made directly to the API, which then returns the import as it is.
  const again = await request.put(`${address}/duration-rule`, {
    headers: seeded.headers,
    data: { duration_rule: "keep_dates" },
  });
  expect(again.status(), "PUT duration-rule, the rule in force").toBe(200);
  const kept = (await again.json()) as Schemas["ImportDetail"];
  expect(kept.status).toBe("analysed");
  expect(kept.report?.calendar_gap?.duration_rule).toBe("keep_dates");
  await page.reload();
  await expect(keep.dates).toBeChecked({ timeout: WORKING });

  // Abandoned after the change, the import leaves the project as it was.
  await report.getByRole("button", { name: "Abandonner l’import" }).click();
  await expect(page).not.toHaveURL(/[?&]import=/, { timeout: WORKING });
  await expect(async () => {
    expect((await detail()).status).toBe("abandoned");
  }).toPass({ timeout: WORKING });
  expect(await tasksOfProject()).toEqual(before);
});

test("exports the remaining to commit as an Excel file, imports it back in two steps, leaves the screen of the exchanges while it is applied, and reads its outcome in the shell, as the project manager of the run @shared [WF-IHM-0080-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  // WF-IHM-0080-A: « Un utilisateur qui change d’écran pendant un import est informé de son
  // aboutissement. » The remaining to commit exported and imported back without a change, the
  // application confirmed is a task of the shell, which the user keeps reading from another screen:
  // the shell tells its success there, and the service holds the import applied. The project is
  // the run's own (#2193).
  test.skip(
    !inService,
    "the service keeps the file made and the import applied, the fake back not",
  );
  test.slow();
  // The import of a remaining to commit is offered to a project in progress: the project of the
  // run is taken there, by the operations a user leads it by, and its current revision opened.
  const seeded = await seedPlanning(page, browser, request, manager, "Reste");
  const employed = seeded.nodes[6];
  if (employed === undefined) {
    throw new Error("the planning seeded has no task 6, which the line of labour is attached to");
  }
  await employRole(request, seeded.headers, seeded.ids, employed, wiringService());
  const current = await takeInProgress(
    request,
    seeded,
    `RAE-${seeded.own.label.slice(-8).toUpperCase()}`,
  );
  const screen = `${seeded.own.path}/revisions/${current.revision}/exchanges`;
  await openHydrated(page, screen);

  // The export of the remaining to commit: chosen in the list of the files, followed in the shell.
  const exports = page.getByRole("region", { name: "Demander un export" });
  const kinds = exports.getByRole("combobox", { name: "Fichier à exporter" });
  await expect(kinds.getByRole("option", { name: "Reste à engager" })).toHaveCount(1, {
    timeout: WORKING,
  });
  await kinds.selectOption({ label: "Reste à engager" });
  await exports.getByRole("button", { name: "Demander l’export" }).click();
  await page.getByRole("button", { name: /^Tâches et messages\s:/ }).click();
  const panel = page.getByRole("dialog", { name: "Tâches et messages" });
  const tasks = panel.getByRole("region", { name: "Tâches de fond" });
  const link = tasks.getByRole("link", { name: /^Télécharger le résultat/ });
  await expect(link).toBeVisible({ timeout: WORKING });
  // The task of the export, which the shell has followed: its reads are not the application's.
  const href = (await link.getAttribute("href")) ?? "";
  const exported = /^\/tasks\/([0-9a-f-]{36})\/result/.exec(href)?.[1];
  if (exported === undefined) {
    throw new Error(`the link of the result names no task: ${href}`);
  }
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  const filename = download.suggestedFilename();
  expect(filename).toMatch(/-reste-a-engager\.xlsx$/);
  const workbook = await downloaded(download);
  expect(workbook.subarray(0, 4)).toEqual(Buffer.from([0x50, 0x4b, 0x03, 0x04]));
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);

  // Imported back as it is: the report comes before any confirmation.
  const imports = page.getByRole("region", { name: "Importer un fichier" });
  await imports.getByRole("button", { name: "Importer un reste à engager" }).click();
  const form = imports.getByRole("form", { name: "Importer un reste à engager" });
  await form.getByLabel("Fichier à importer").setInputFiles({
    name: filename,
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: workbook,
  });
  await form.getByRole("button", { name: "Analyser le fichier" }).click();
  await expect(page).toHaveURL(/[?&]import=[0-9a-f-]{36}/, { timeout: WORKING });
  const opened = new URL(page.url()).searchParams.get("import") ?? "";
  const report = page.getByRole("region", { name: `Compte rendu de l’import « ${filename} »` });
  // The analysis is a task of the background: the report comes when the screen is read anew.
  await expect(async () => {
    if ((await report.getByText(/lues?\./).count()) === 0) {
      await page.reload();
      await page.waitForLoadState("domcontentloaded");
    }
    await expect(report.getByText(/lues?\./)).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING, intervals: [500, 1_000, 2_000] });
  await expect(report.getByText("Aucun écart avec les données existantes")).toBeVisible();
  await expect(report.getByRole("table", { name: "Lignes rejetées" })).toHaveCount(0);
  const address = `${API}/projects/${seeded.ids.project}/imports/${opened}`;
  // The task of the analysis, the last of the import until it is applied: the shell may still be
  // reading it.
  const analysed = await request.get(address, { headers: seeded.headers });
  expect(analysed.status(), "GET import").toBe(200);
  const analysis = ((await analysed.json()) as Schemas["ImportDetail"]).task.task_id;

  // Confirmed, the application is a task; the user leaves the screen of the exchanges at once. The
  // read of the application's task by the shell (a server action carrying the sole identifier of
  // the task) waits for the test to let it, in the browser: the application is then still followed
  // when the screen is left, however small the file, and the service itself is left to its own pace.
  // The read held is the application's alone, the one task the confirmation starts, and the screen
  // is left once it has been sent (#3066). Next runs the server actions of a page one at a time: a
  // read of the analysis held before the confirmation kept the confirmation from being sent at all
  // (#3003); and a read of the application sent after the click — the first comes two seconds after
  // the confirmation — joined the navigation, which was then never shown (n° 15 and 16 of the
  // defects already met, `docs/dev/typescript.md`).
  let release!: () => void;
  const released = new Promise<void>((resolve) => {
    release = resolve;
  });
  let sent!: () => void;
  const held = new Promise<void>((resolve) => {
    sent = resolve;
  });
  const readTask = (request: Request) =>
    request.headers()["next-action"] === undefined
      ? undefined
      : /^\["([0-9a-f-]{36})"\]$/.exec(request.postData() ?? "")?.[1];
  await page.route("**/*", async (route: Route) => {
    const task = readTask(route.request());
    if (task !== undefined && task !== analysis && task !== exported) {
      sent();
      await released;
    }
    await route.fallback();
  });
  await report.getByRole("button", { name: "Appliquer l’import" }).click();
  const confirmation = report.getByRole("form", { name: "Confirmation de l’application" });
  await confirmation.getByRole("button", { name: "Confirmer l’application" }).click();
  await expect(confirmation).toHaveCount(0);
  await held;
  await page
    .getByRole("navigation", { name: "Fonctions" })
    .getByRole("link", { name: "Projets", exact: true })
    .click();
  await expect(page).not.toHaveURL(/\/exchanges/);
  await expect(report).toHaveCount(0);

  // From the other screen, the shell shows the application still followed, its read held.
  await page.getByRole("button", { name: /^Tâches et messages\s:/ }).click();
  const application = tasks
    .getByRole("listitem")
    .filter({ hasText: `Application d’un import « ${filename} »` });
  await expect(application.getByText(/^(En cours|En attente)$/)).toBeVisible();
  await expect(application.getByText("Réussie")).toHaveCount(0);

  // The read let go, the shell tells the outcome of the application.
  release();
  await expect(application.getByText("Réussie")).toBeVisible({ timeout: WORKING });
  await page.keyboard.press("Escape");
  await expect(async () => {
    const applied = await request.get(address, { headers: seeded.headers });
    expect(applied.status(), "GET import").toBe(200);
    expect(((await applied.json()) as Schemas["ImportDetail"]).status).toBe("applied");
  }).toPass({ timeout: WORKING });
});
