// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The reading of the accounts of the identity provider asked from the screen of the accounts,
 * against the service (US-0370): an administrator of the accounts — the person of the directory —
 * presses « Lire les comptes »; the service queues the task and gives the hand back at once, the
 * worker reads the realm, and the tracker of the shell follows the task to its end, which it
 * announces (WF-ARC-0090); the screen read anew shows the report of that reading, ended after it
 * was asked (WF-ADM-0070).
 *
 * The roles of the person of the directory are written in the database of the platform once her
 * account is Waterfall's (`accountAdministrator`), as an administrator would give them.
 */
import { expect, type Locator, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { WORKING } from "../hydration";
import { heldToTheContract } from "./contract";
import { accountAdministrator, DIRECTORY, signIn } from "./realm";

heldToTheContract();

const USERS = "/admin/users";

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

test("the reading of the accounts asked from the screen gives the hand back at once, and the administrator sees it end, then its report [WF-ARC-0090-A] [WF-ADM-0070-A]", async ({
  browser,
  page,
  playwright,
}) => {
  // The worker reads the realm after the directory has been synchronised: a minute at most.
  test.setTimeout(120_000);
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const administrator = await accountAdministrator(browser, calls);
  try {
    await signIn(page, DIRECTORY, USERS);
    const reading = page.getByRole("region", {
      name: "Lecture des comptes du fournisseur d’identité",
    });
    const tasks = page.getByRole("region", { name: "Tâches de fond" });
    const entries = tasks.getByRole("listitem");
    const asked = Date.now();
    await handOver(reading.getByRole("button", { name: "Lire les comptes" }), entries);

    // Followed by the tracker until the worker has read the accounts, then announced.
    await expect(entries).toHaveCount(1);
    await expect(entries.getByText("Réussie")).toBeVisible({ timeout: 90_000 });
    await expect(tasks.getByRole("log")).toContainText(
      "Tâche terminée : Lecture des comptes du fournisseur d’identité.",
    );
    // A report to read on the screen, not a file to download.
    await expect(entries.getByRole("link", { name: /Télécharger/ })).toHaveCount(0);

    // The screen read anew shows the report of a reading that ended after it was asked.
    await entries.getByRole("button", { name: "Recharger l’écran" }).click();
    const ended = reading.locator("time");
    await expect(async () => {
      const at = Date.parse((await ended.getAttribute("datetime")) ?? "");
      expect(at).toBeGreaterThanOrEqual(asked - 5_000);
    }).toPass({ timeout: WORKING });
    await expect(reading).toContainText("Dernière lecture achevée le");
    await expect(
      reading.getByRole("button", { name: "Détails de la dernière lecture" }),
    ).toBeVisible();
  } finally {
    administrator.done();
    await calls.dispose();
  }
});
