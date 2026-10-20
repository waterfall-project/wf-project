// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * A backup taken from the screen, downloaded, deposited again and restored, against the service
 * (US-0440): the administrator of the installation presses « Sauvegarder maintenant »; the worker
 * backs the platform up and the tracker follows the task to its end (WF-ADM-0150); the screen read
 * anew lists the backup, which the administrator downloads, then deposits as the archive of another
 * installation would be (#350), and the deposit says the date its manifest says. The backup of the
 * list is then restored, its identifier typed, the confirmation naming its date (WF-ADM-0160). The screen gives way to that of the
 * maintenance, every user signed out, until the restoration is done; the administrator signs in
 * again, with the password of the backup, and finds the screen.
 *
 * The proxy of the contract between the front and the API, Prism, reads every body as text: the
 * bytes of the archive past 0x7f reach the browser, and the deposit the API, each replaced by
 * U+FFFD. Its manifest, the first member and plain JSON, comes through, and with it the date the
 * deposit says; the dumps do not, and a deposit restored here would be refused as unreadable
 * (`FILE_FORMAT_UNREADABLE`) before any maintenance. The path restores the backup of the list,
 * whose bytes never leave the service; the restoration of a deposit, its bytes intact, is the
 * service's own proof, on a second installation
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
const JOURNAL = "/admin/audit-log";
const ANY_BACKUP = `${BACKUPS}/01926f3a-7c00-7000-8000-000000000907/content`;

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", BACKUPS, ANY_BACKUP, JOURNAL);
});

/**
 * Press a command that hands a task over to the tracker, on a page that may not be hydrated yet:
 * again until React answered — a press answered is never repeated, which would ask a second task.
 * `followed` is the button of the panel once it counts a task.
 */
async function handOver(command: Locator, followed: Locator): Promise<void> {
  await expect(async () => {
    if ((await command.getAttribute("aria-busy")) !== "true" && (await followed.count()) === 0) {
      await command.click();
    }
    await expect
      .poll(
        async () =>
          (await command.getAttribute("aria-busy")) === "true" || (await followed.count()) > 0,
        { timeout: 1_000 },
      )
      .toBe(true);
  }).toPass({ timeout: WORKING });
}

test(
  "a backup taken, downloaded, deposited and restored: the screen says the restoration waiting, then its end, and the administrator signs in again [WF-ADM-0150-A] [WF-ADM-0160-A]",
  { tag: "@platform-wide" },
  async ({ page }, testInfo) => {
    // A backup by the worker, its verification, then a restoration that replaces both databases
    // and applies the realm again: minutes, not seconds.
    test.setTimeout(600_000);
    await signIn(page, ADMINISTRATOR, BACKUPS);

    // The backup, followed by the tracker until the worker has taken and verified it.
    const followed = page.getByRole("button", { name: /^Tâches et messages\s: 1 tâche suivie/ });
    const tasks = page.getByRole("region", { name: "Tâches de fond" });
    const entries = tasks.getByRole("listitem");
    await handOver(page.getByRole("button", { name: "Sauvegarder maintenant" }), followed);
    await followed.click();
    await expect(entries.getByText("Réussie")).toBeVisible({ timeout: 180_000 });
    await entries.getByRole("button", { name: "Recharger l’écran" }).click();
    const newest = page.getByRole("grid", { name: "Sauvegardes" }).getByRole("row").nth(1);
    // Listed first, once the screen is read anew, with its date, the instant it was taken, which
    // the browser writes in its local time — a backup of a run before may be listed until then —,
    // and with its size.
    const taken = newest.locator("time");
    const instant = async () => Date.parse((await taken.getAttribute("datetime")) ?? "");
    await expect.poll(async () => Math.abs(Date.now() - (await instant()))).toBeLessThan(240_000);
    await expect(newest).toContainText("Vérifiée");
    await expect(taken).not.toBeEmpty();
    const takenIso = (await taken.getAttribute("datetime")) ?? "";
    const takenAt = Date.parse(takenIso);
    await expect(newest).toContainText(/\d+(,\d)?\s(octet|kilooctet|mégaoctet|gigaoctet)s?/);

    // Downloaded through the front, which hands the archive on under its name.
    const downloading = page.waitForEvent("download");
    await newest.getByRole("link", { name: /^Télécharger la sauvegarde du / }).click();
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

    // The backup of the list restored once its identifier is typed, the confirmation naming its
    // date — not the deposit, whose dumps Prism altered —: first the restoration waiting, no one
    // signed out yet.
    // The date as the list writes it, read before the dialog opens: modal, it hides the page
    // behind it, the grid with it.
    const takenText = await taken.innerText();
    const confirmed = Date.now();
    await newest
      .getByRole("button", { name: /^Restaurer la plateforme depuis la sauvegarde du / })
      .click();
    const dialog = page.getByRole("dialog", { name: "Restaurer la plateforme" });
    await expect(dialog).toContainText(`sauvegarde du ${takenText}`);
    const identifier = await dialog.locator("code").innerText();
    await dialog
      .getByRole("textbox", { name: "Pour confirmer, saisissez l’identifiant de la sauvegarde" })
      .fill(identifier);
    await dialog.getByRole("button", { name: "Restaurer", exact: true }).click();
    const maintenance = page.getByRole("status", {
      name: "Restauration de la plateforme en cours",
    });
    await expect(maintenance).toContainText("La restauration est en attente");
    // Then its end: done, once the probe said the maintenance — every user signed out — and its
    // end. A restoration this small may hold the maintenance between two reads of the probe: the
    // screen then sees the session closed and nothing more, and says that alone, without
    // affirming the restoration done: the journal of audit says it, after the sign-in.
    const signedOut = page.getByRole("status", { name: "Session terminée" });
    const ended = maintenance.getByText("Restauration terminée").or(signedOut);
    // A restoration refused before the maintenance gives the page back with its motive: said at
    // once, rather than waited for until the end of the path.
    const refused = page.getByRole("main").getByRole("alert");
    await expect(ended.or(refused)).toBeVisible({ timeout: 420_000 });
    await expect(refused).toHaveCount(0);

    // Signed out by the restoration, the administrator signs in again, and finds the screen.
    await page.getByRole("link", { name: "Se connecter" }).click();
    await giveIdentifiers(page, ADMINISTRATOR);
    await expect(page).toHaveURL(BACKUPS);
    await expect(page.getByRole("grid", { name: "Sauvegardes" })).toBeVisible();

    // Whatever end the screen saw, the restoration took place and succeeded: the last inscription
    // of the journal of audit is the restoration itself, of the backup, which the service writes
    // only once the task succeeded, the maintenance lifted after it (WF-ADM-0160). The
    // administrator, « Administrateur », reads the journal.
    await page.goto(JOURNAL);
    const last = page.getByRole("grid", { name: "Journal d’audit" }).getByRole("row").nth(1);
    await expect(last).toContainText("Restauration", { timeout: WORKING });
    await expect(last).toContainText("Sauvegarde");
    await expect(last).not.toContainText("Sauvegarde déposée");
    const restoredAt = Date.parse((await last.locator("time").getAttribute("datetime")) ?? "");
    expect(restoredAt).toBeGreaterThanOrEqual(confirmed - 60_000);
  },
);
