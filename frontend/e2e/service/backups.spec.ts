// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * A backup taken from the screen and downloaded, against the service (US-0440): the administrator
 * of the installation presses « Sauvegarder maintenant »; the worker backs the platform up and the
 * tracker follows the task to its end (WF-ADM-0150); the screen read anew lists the backup,
 * verified, which the administrator downloads through the front, that hands the archive on.
 */
import { stat } from "node:fs/promises";

import { expect, type Locator, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { WORKING } from "../hydration";
import { heldToTheContract } from "./contract";
import { ADMINISTRATOR, signIn } from "./realm";

heldToTheContract();

const BACKUPS = "/admin/backups";
const ANY_BACKUP = `${BACKUPS}/01926f3a-7c00-7000-8000-000000000907/content`;

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", BACKUPS, ANY_BACKUP);
});

/**
 * Press a command that hands a task over to the tracker, on a page that may not be hydrated yet:
 * again until React answered — a press answered is never repeated, which would ask a second task.
 */
async function handOver(command: Locator, entries: Locator): Promise<void> {
  await expect(async () => {
    if ((await command.getAttribute("aria-busy")) !== "true" && (await entries.count()) === 0) {
      await command.click();
    }
    await expect
      .poll(
        async () =>
          (await command.getAttribute("aria-busy")) === "true" || (await entries.count()) > 0,
        { timeout: 1_000 },
      )
      .toBe(true);
  }).toPass({ timeout: WORKING });
}

test("a backup taken from the screen, followed to its end, then downloaded through the front [WF-ADM-0150-A]", async ({
  page,
}, testInfo) => {
  // A backup by the worker, then its verification: minutes, not seconds.
  test.setTimeout(240_000);
  await signIn(page, ADMINISTRATOR, BACKUPS);

  // The backup, followed by the tracker until the worker has taken and verified it.
  const tasks = page.getByRole("region", { name: "Tâches de fond" });
  const entries = tasks.getByRole("listitem");
  await handOver(page.getByRole("button", { name: "Sauvegarder maintenant" }), entries);
  await expect(entries.getByText("Réussie")).toBeVisible({ timeout: 180_000 });
  await entries.getByRole("button", { name: "Recharger l’écran" }).click();
  const newest = page.getByRole("table", { name: "Sauvegardes" }).getByRole("row").nth(1);
  await expect(newest).toContainText("Vérifiée");

  // Downloaded through the front, which hands the archive on under its name.
  const downloading = page.waitForEvent("download");
  await newest.getByRole("link", { name: "Télécharger" }).click();
  const download = await downloading;
  expect(download.suggestedFilename()).not.toBe("");
  const archive = testInfo.outputPath(download.suggestedFilename());
  await download.saveAs(archive);
  expect((await stat(archive)).size).toBeGreaterThan(0);
});
