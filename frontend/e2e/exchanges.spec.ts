// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Route, test } from "@playwright/test";

// The fake back serves the first example of each operation: the file deposited, its import
// opened, its analysis under way; the report the address then names, analysed — two lines
// rejected —; the application queued; the abandonment. It keeps no state: the component and page
// tests prove the other states of an import (`exchanges.dom.test.tsx`, `page.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IMPORT = "01926f3a-7c00-7000-8000-000000000a11";
const START = `/projects/${PROJECT}/exchanges?revision_id=${REVISION}`;
// The task of the application queued (`task_import_queued`), which the tracker reads by its id.
const APPLICATION = "01926f3a-7c00-7000-8000-000000000902";

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
  await page.goto(START);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Échanges de fichiers");
  const imports = page.getByRole("region", { name: "Importer un fichier" });
  await imports.getByRole("button", { name: "Importer un devis" }).click();
  const form = imports.getByRole("form", { name: "Importer un devis" });
  await form.getByLabel("Fichier à importer").setInputFiles({
    name: "devis-poste-de-commande.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: Buffer.from("devis"),
  });
  await form.getByRole("button", { name: "Analyser le fichier" }).click();

  // The report of the import the analysis opened, its lines rejected each with its motive.
  await expect(page).toHaveURL(`${START}&import=${IMPORT}`);
  const report = page.getByRole("region", {
    name: "Compte rendu de l’import « devis-poste-de-commande.xlsx »",
  });
  const rejected = report.getByRole("table", { name: "Lignes rejetées" }).getByRole("row");
  await expect(rejected).toHaveText([
    /Ligne\s*Motif/,
    /7\s*Tâche inconnue\./,
    /12\s*Rôle de ressource inconnu\./,
  ]);
  await expect(report.getByText("24 lignes lues.")).toBeVisible();

  // Nothing is applied before the confirmation; confirmed, the application is a task followed.
  const read = page.waitForRequest((request) => request.postData()?.includes(APPLICATION) === true);
  await report.getByRole("button", { name: "Appliquer l’import" }).click();
  const confirmation = report.getByRole("form", { name: "Confirmation de l’application" });
  await confirmation.getByRole("button", { name: "Confirmer l’application" }).click();
  await expect(confirmation).toHaveCount(0);
  const tasks = page.getByRole("region", { name: "Tâches de fond" });
  const application = "Application d’un import « devis-poste-de-commande.xlsx »";
  await expect(tasks.getByText(application)).toBeVisible();
  await expect(tasks.getByRole("progressbar", { name: application })).toBeVisible();
  await read;
  release();

  // Abandoned, the import leaves the screen as it was before it.
  await report.getByRole("button", { name: "Abandonner l’import" }).click();
  await expect(page).toHaveURL(START);
  await expect(report).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Imports du projet" })).toBeVisible();
});
