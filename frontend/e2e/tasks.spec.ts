// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

// The fake back serves the first example of each operation: the current revision, a draft
// whose marking is available; the marking queued; and, read two seconds later, the marking
// succeeded. A marking still running, then failed, is an example it does not serve first: the
// tests of the tracker show them (`task-tracker.dom.test.tsx`, `mark-command.dom.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

test("marking a revision gives the hand back, shows its progress, and announces on another screen its end, which comes after the change [WF-IHM-0080-A]", async ({
  page,
}) => {
  // The time of the page is the test's: the read of the task comes when the test lets it come,
  // after the change of screen, not before.
  await page.clock.install();
  await page.goto(`/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const commands = page.getByRole("main").getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Marquer la révision" }).click();
  await commands.getByRole("textbox", { name: "Nom de version" }).fill("V2");
  await commands.getByRole("button", { name: "Marquer", exact: true }).click();

  // The hand is back at once: the form has closed, and the task is followed with its progress.
  await expect(commands.getByRole("form")).toHaveCount(0);
  const tasks = page.getByRole("region", { name: "Tâches de fond" });
  await expect(tasks.getByText("Marquage d’une révision « V2 »")).toBeVisible();
  await expect(
    tasks.getByRole("progressbar", { name: "Marquage d’une révision « V2 »" }),
  ).toBeVisible();

  // The user goes to another screen meanwhile, within the application — the document stays,
  // as the marker left on it shows —; the end of the marking is announced there.
  await page.evaluate(() => {
    document.documentElement.dataset.visited = "revisions";
  });
  await page
    .getByRole("navigation", { name: "Fonctions" })
    .getByRole("link", { name: "Cycle de vie du projet" })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Cycle de vie du projet");
  // On the new screen, the marking still runs: nothing has been read out yet.
  await expect(tasks.getByRole("log")).toBeEmpty();
  await expect(tasks.getByRole("progressbar")).toBeVisible();

  await page.clock.runFor(2000);
  await expect(tasks.getByRole("log")).toHaveText(
    /^Tâche terminée\s: Marquage d’une révision «\sV2\s»\.$/,
  );
  await expect(tasks.getByText("Réussie")).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-visited", "revisions");
});
