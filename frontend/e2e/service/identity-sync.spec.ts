// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The reading of the accounts of the identity provider asked from the screen of the accounts,
 * against the service (US-0370): an administrator of the accounts — a local account of the path —
 * presses « Lire les comptes »; the service queues the task and gives the hand back at once, the
 * worker reads the realm, and the tracker of the shell follows the task to its end, which it
 * announces (WF-ARC-0090); the screen read anew shows the report of that reading, ended after the
 * one it showed before (WF-ADM-0070).
 *
 * The local account is created by the administrator of the installation, its password set by its
 * link (`localAccount`); its role — reading the accounts and modifying them, which the command asks
 * — is given by the administrator (`Administrator.give`), and withdrawn at the end.
 */
import { expect, type Locator, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { WORKING } from "../hydration";
import { heldToTheContract } from "./contract";
import { accountAdministrator, localAccount, signIn, withdrawRoles } from "./realm";

heldToTheContract();

const USERS = "/admin/users";
const SYNCHRONISER = "Lecture des comptes du fournisseur (parcours)";

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", USERS);
});

/**
 * Press a command that hands a task over to the tracker, on a page that may not be hydrated yet:
 * pressed only while the command is not busy and the tracker follows no task, and again until one
 * of them says React answered — a press answered is never repeated, which would ask a second task.
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

test("the reading of the accounts asked from the screen gives the hand back at once, and the administrator sees it end, then its report [WF-ARC-0090-A]", async ({
  browser,
  page,
  playwright,
}) => {
  // An account created and its password set, then the worker reads the realm after the directory
  // has been synchronised: a minute at most.
  test.setTimeout(150_000);
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const administrator = await accountAdministrator(browser, calls);
  const holder = await localAccount(browser, administrator);
  try {
    await administrator.give(holder.id, SYNCHRONISER, ["users.read", "users.write"]);
    await signIn(page, holder, USERS);
    const reading = page.getByRole("region", {
      name: "Lecture des comptes du fournisseur d’identité",
    });
    const tasks = page.getByRole("region", { name: "Tâches de fond" });
    const entries = tasks.getByRole("listitem");
    // The end of the last reading shown before the press — none yet, or one the platform asked —,
    // to which the report read anew is later: no clock but the service's.
    const ended = reading.getByRole("time");
    await expect(
      ended.or(reading.getByText("Aucune lecture des comptes n’a encore abouti.")),
    ).toBeVisible();
    const before = (await ended.count()) === 0 ? null : await ended.getAttribute("datetime");
    await handOver(reading.getByRole("button", { name: "Lire les comptes" }), entries);

    // Followed by the tracker until the worker has read the accounts, then announced.
    await expect(entries).toHaveCount(1);
    await expect(entries.getByText("Réussie")).toBeVisible({ timeout: 90_000 });
    await expect(tasks.getByRole("log")).toContainText(
      "Tâche terminée : Lecture des comptes du fournisseur d’identité.",
    );
    // A report to read on the screen, not a file to download.
    await expect(entries.getByRole("link", { name: /Télécharger/ })).toHaveCount(0);

    // The screen read anew shows the report of a reading that ended after the one shown before.
    await entries.getByRole("button", { name: "Recharger l’écran" }).click();
    await expect(async () => {
      const after = await ended.getAttribute("datetime", { timeout: 1_000 });
      expect(after).not.toBeNull();
      if (before !== null) {
        expect(Date.parse(after ?? "")).toBeGreaterThan(Date.parse(before));
      }
    }).toPass({ timeout: WORKING });
    await expect(reading).toContainText("Dernière lecture achevée le");
    await expect(
      reading.getByRole("button", { name: "Détails de la dernière lecture" }),
    ).toBeVisible();
  } finally {
    withdrawRoles(holder.email);
    await calls.dispose();
  }
});
