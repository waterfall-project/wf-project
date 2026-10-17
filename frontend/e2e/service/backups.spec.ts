// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * A backup taken from the screen, downloaded, deposited again and restored, against the service
 * (US-0440): the administrator of the installation presses « Sauvegarder maintenant »; the worker
 * backs the platform up and the tracker follows the task to its end (WF-ADM-0150); the screen read
 * anew lists the backup, which the administrator downloads, then deposits as the archive of another
 * installation would be (#350), and restores at the date its manifest says, confirmed (WF-ADM-0160).
 * The screen gives way to that of the maintenance, every user signed out, until the restoration is
 * done; the administrator signs in again, with the password of the backup, and finds the screen.
 *
 * The service platform is one installation: the backup is restored where it was taken, the second
 * installation of US-0440 being the service's own proof
 * (`test_uploads.py::test_a_backup_copied_deposited_and_restored_on_another_installation_makes_it_a_copy`).
 * The restoration replaces the whole platform and closes every session: the path plays alone, last
 * (`playwright.config.ts`, the project `restoration`).
 */
import { stat } from "node:fs/promises";

import { expect, type Locator, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { WORKING } from "../hydration";
import { heldToTheContract } from "./contract";
import { ADMINISTRATOR, giveIdentifiers, signIn } from "./realm";

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

test(
  "a backup taken, downloaded, deposited and restored: the screen says the maintenance, every user signed out, and the administrator signs in again [WF-ADM-0150-A] [WF-ADM-0160-A]",
  { tag: "@platform-wide" },
  async ({ page }, testInfo) => {
    // A backup by the worker, its verification, then a restoration that replaces both databases
    // and applies the realm again: minutes, not seconds.
    test.setTimeout(600_000);
    await signIn(page, ADMINISTRATOR, BACKUPS);

    // The backup, followed by the tracker until the worker has taken and verified it.
    const tasks = page.getByRole("region", { name: "Tâches de fond" });
    const entries = tasks.getByRole("listitem");
    await handOver(page.getByRole("button", { name: "Sauvegarder maintenant" }), entries);
    await expect(entries.getByText("Réussie")).toBeVisible({ timeout: 180_000 });
    await entries.getByRole("button", { name: "Recharger l’écran" }).click();
    const newest = page.getByRole("table", { name: "Sauvegardes" }).getByRole("row").nth(1);
    await expect(newest).toContainText("Vérifiée");
    // Listed with its date, the instant it was taken, which the browser writes in its local time,
    // and with its size.
    const taken = newest.locator("time");
    await expect(taken).not.toBeEmpty();
    const takenAt = Date.parse((await taken.getAttribute("datetime")) ?? "");
    expect(Math.abs(Date.now() - takenAt)).toBeLessThan(240_000);
    await expect(newest.getByRole("cell").nth(1)).toHaveText(
      /^\d+(,\d)?\s(octet|kilooctet|mégaoctet|gigaoctet)s?$/,
    );

    // Downloaded through the front, which hands the archive on under its name.
    const downloading = page.waitForEvent("download");
    await newest.getByRole("link", { name: "Télécharger" }).click();
    const download = await downloading;
    expect(download.suggestedFilename()).not.toBe("");
    const archive = testInfo.outputPath(download.suggestedFilename());
    await download.saveAs(archive);
    expect((await stat(archive)).size).toBeGreaterThan(0);

    // Deposited as the archive of another installation, which says the date of its backup.
    const deposit = page.getByRole("region", {
      name: "Restaurer une sauvegarde d’une autre installation",
    });
    await deposit.getByLabel("Archive de la sauvegarde").setInputFiles(archive);
    await deposit.getByRole("button", { name: "Déposer" }).click();
    const restore = deposit.getByRole("button", { name: "Restaurer cette sauvegarde" });
    await expect(restore).toBeVisible({ timeout: 60_000 });
    const deposited = await deposit.getByRole("time").getAttribute("datetime");
    expect(Date.parse(deposited ?? "")).toBe(takenAt);

    // Restored once its date is confirmed: the screen of the maintenance, then its end.
    await restore.click();
    const dialog = page.getByRole("alertdialog", { name: "Restaurer la plateforme entière" });
    await expect(dialog.getByRole("time").first()).toHaveAttribute("datetime", deposited ?? "");
    await dialog.getByRole("button", { name: /^Restaurer la sauvegarde du/ }).click();
    const maintenance = page.getByRole("status", {
      name: "Restauration de la plateforme en cours",
    });
    await expect(maintenance).toContainText("tous les utilisateurs ont été déconnectés");
    await expect(maintenance).toContainText("Restauration terminée", { timeout: 420_000 });

    // Signed out by the restoration, the administrator signs in again, and finds the screen.
    await maintenance.getByRole("link", { name: "Se connecter" }).click();
    await giveIdentifiers(page, ADMINISTRATOR);
    await expect(page).toHaveURL(BACKUPS);
    await expect(page.getByRole("table", { name: "Sauvegardes" })).toBeVisible();
  },
);
