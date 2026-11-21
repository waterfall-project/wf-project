// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import { expect } from "@playwright/test";

import { WORKING } from "../bounds";
import { downloaded } from "../download";
import { seedEstimate } from "../estimate-seed";
import { openHydrated } from "../hydration";
import { inService, test } from "../mode";
import { sql } from "./realm";

// A failed import is followed in the logs of the platform by the one identifier its message gives
// (WF-OBS-0020-A, US-2900): the project manager of the run exports the estimate of a project she
// creates and imports it back; the report read, the application is made to break in the database,
// as a fault of the platform would — a trigger of the table of the imports, for this project alone —,
// and the worker fails the task with an unexpected error. The message of the shell gives the
// reference of the failure; the search of the logs of the platform by that reference, as the
// operator makes it (`make service-logs-search CORRELATION=`), finds the deposit of the file, the
// opening of the import, the start of the task and its failure.

/** Break, in the database, the application of the imports of a project, until `repaired`. */
function breakApplications(project: string): string {
  const name = `e2e_break_${project.replaceAll("-", "")}`;
  sql(
    `create function :"name"() returns trigger language plpgsql as $body$
begin raise exception 'the application of an import is broken on purpose'; end $body$;
create trigger :"name" before update on import_report for each row
  when (new.status = 'applied' and new.project_id = :'project') execute function :"name"();
`,
    { name, project },
  );
  return name;
}

/** Repair what `breakApplications` broke. */
function repaired(name: string): void {
  sql(`drop trigger if exists :"name" on import_report; drop function if exists :"name"();`, {
    name,
  });
}

/** The story the logs of the platform tell of an identifier, as `make service-logs-search` prints. */
function story(identifier: string): string {
  const { MAKEFLAGS: _flags, MFLAGS: _mflags, MAKELEVEL: _level, ...environment } = process.env;
  return execFileSync(
    "make",
    ["--no-print-directory", "-C", resolve(process.cwd(), ".."), "service-logs-search"],
    {
      env: { ...environment, CORRELATION: identifier },
      encoding: "utf8",
      maxBuffer: 256 * 1024 * 1024,
    },
  );
}

test("an import that fails in the worker is followed in the logs, from the deposit of its file to the failure of its task, by the one reference its message gives [WF-OBS-0020-A] [US-2900]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, "the logs are those of the platform of the service, the fake back has none");
  test.slow();
  const seeded = await seedEstimate(page, browser, request, manager, "Trace");
  await openHydrated(page, `${seeded.revision}/exchanges`);

  // The workbook of the estimate, exported by the screen.
  const exports = page.getByRole("region", { name: "Demander un export" });
  const kinds = exports.getByRole("combobox", { name: "Fichier à exporter" });
  await expect(kinds.getByRole("option", { name: "Devis" })).toHaveCount(1, { timeout: WORKING });
  await kinds.selectOption({ label: "Devis" });
  const made = page.waitForEvent("download", { timeout: WORKING });
  await exports.getByRole("button", { name: "Demander l’export" }).click();
  const download = await made;
  const filename = download.suggestedFilename();
  const workbook = await downloaded(download);

  // Imported back: the report is read before anything is applied.
  const imports = page.getByRole("region", { name: "Importer un fichier" });
  await imports.getByRole("button", { name: "Importer un devis" }).click();
  const form = imports.getByRole("form", { name: "Importer un devis" });
  await form.getByLabel("Fichier à importer").setInputFiles({
    name: filename,
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: workbook,
  });
  await form.getByRole("button", { name: "Analyser le fichier" }).click();
  await expect(page).toHaveURL(/[?&]import=[0-9a-f-]{36}/, { timeout: WORKING });
  const report = page.getByRole("region", { name: `Compte rendu de l’import « ${filename} »` });
  await expect(async () => {
    if ((await report.getByText(/lues?\./).count()) === 0) {
      await page.reload();
      await page.waitForLoadState("domcontentloaded");
    }
    await expect(report.getByText(/lues?\./)).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING, intervals: [500, 1_000, 2_000] });

  // The application breaks in the worker.
  const trigger = breakApplications(seeded.ids.project);
  let reference: string;
  try {
    await report.getByRole("button", { name: "Appliquer l’import" }).click();
    await report
      .getByRole("form", { name: "Confirmation de l’application" })
      .getByRole("button", { name: "Confirmer l’application" })
      .click();
    await page.getByRole("button", { name: /^Tâches et messages\s:/ }).click();
    const panel = page.getByRole("dialog", { name: "Tâches et messages" });
    const message = panel
      .getByRole("region", { name: "Messages" })
      .getByRole("listitem")
      .filter({ hasText: "Erreur inattendue du service." });
    await expect(message).toContainText(/Référence\s:\s[0-9a-f-]{8,}/, { timeout: WORKING });
    const text = (await message.first().textContent()) ?? "";
    reference = /Référence\s:\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/.exec(text)?.[1] ?? "";
  } finally {
    repaired(trigger);
  }
  expect(reference, "the reference of the message").toMatch(/^[0-9a-f-]{36}$/);

  // That one reference finds the whole story in the logs of the platform.
  const events = (name: string) => story(reference).split("\n").filter((line) => line.includes(`"${name}"`));
  await expect(async () => {
    const found = story(reference);
    for (const event of ["upload.deposited", "import.opened", "task.started", "task.failed"]) {
      expect(found, event).toContain(`"${event}"`);
    }
  }).toPass({ timeout: WORKING, intervals: [500, 1_000, 2_000] });
  expect(events("task.failed").some((line) => line.includes(reference))).toBe(true);
});
