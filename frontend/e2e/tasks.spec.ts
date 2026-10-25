// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, type Route, test } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated } from "./hydration";

// The fake back serves the first example of each operation: the current revision, a draft
// whose marking is available; the marking queued; and, read two seconds later, the marking
// succeeded. A marking still running, then failed, is an example it does not serve first: the
// tests of the tracker show them (`task-tracker.dom.test.tsx`, `mark-command.dom.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
// The task of the marking queued (`task_mark_queued`), which the tracker reads by its id.
const TASK = "01926f3a-7c00-7000-8000-000000000931";

/**
 * The line under the bar that says the last task handed over or ended, apart from the log of the
 * ends, which says the same to a reader of the screen.
 */
function said(page: Page, text: RegExp) {
  return page.locator("p:not([role=log] p)", { hasText: text });
}

test("marking a revision gives the hand back, shows its progress, and tells on another screen its end, which comes after the change, kept in the history with a link back [WF-IHM-0080-A]", async ({
  page,
}) => {
  // The read of the task comes when the test lets it come — after the change of screen, not
  // before —: the server action that reads it is held until then. The clock of the page is left
  // alone: frozen, it held the new screen too, as its skeleton — React throttles the reveal of a
  // loaded boundary by a timer, which a frozen clock never lets fire (#165). The read held must
  // have left before the click: Next holds a navigation behind the server actions sent after it
  // (defect 15 of `docs/dev/typescript.md`), and one held until the new screen shows would hold
  // the screen too.
  let release!: () => void;
  const released = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/projects/**", async (route: Route) => {
    if (route.request().postData()?.includes(TASK) === true) {
      await released;
    }
    await route.fallback();
  });
  // The screen reached by a click, compiled first.
  await compile(page.request, `/projects/${PROJECT}/lifecycle?revision_id=${REVISION}`);
  await openHydrated(page, `/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const commands = page.getByRole("main").getByRole("region", { name: "Commandes" });
  const read = page.waitForRequest((request) => request.postData()?.includes(TASK) === true);
  await commands.getByRole("button", { name: "Marquer la révision" }).click();
  await commands.getByRole("textbox", { name: "Nom de version" }).fill("V2");
  await commands.getByRole("button", { name: "Marquer", exact: true }).click();

  // The hand is back at once: the form has closed, the line under the bar says the marking
  // started, and the panel, opened by its button, follows it with its progress.
  await expect(commands.getByRole("form")).toHaveCount(0);
  await expect(said(page, /^Tâche lancée\s: Marquage d’une révision «\sV2\s»\.$/)).toBeVisible();
  const button = page.getByRole("button", { name: /^Tâches et messages\s: 1 tâche suivie/ });
  await button.click();
  const panel = page.getByRole("dialog", { name: "Tâches et messages" });
  const tasks = panel.getByRole("region", { name: "Tâches de fond" });
  await expect(tasks.getByText("Marquage d’une révision « V2 »")).toBeVisible();
  await expect(
    tasks.getByRole("progressbar", { name: "Marquage d’une révision « V2 »" }),
  ).toBeVisible();
  // Escape closes it, the focus back on its button.
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await expect(button).toBeFocused();
  // So does a click outside it, on the page its overlay covers, the focus back on its button.
  await button.click();
  await expect(panel).toBeVisible();
  await page.mouse.click(10, 200);
  await expect(panel).toHaveCount(0);
  await expect(button).toBeFocused();

  // The user goes to another screen meanwhile, within the application — the document stays,
  // as the marker left on it shows —; the end of the marking is announced there.
  await page.evaluate(() => {
    document.documentElement.dataset.visited = "revisions";
  });
  await read;
  await page
    .getByRole("navigation", { name: "Fonctions" })
    .getByRole("link", { name: "Cycle de vie du projet" })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Cycle de vie du projet");
  // On the new screen, its read still held, the marking still runs: nothing has been read out.
  const log = page.getByRole("log");
  await expect(log).toBeEmpty();

  release();
  const ended = /^Tâche terminée\s: Marquage d’une révision «\sV2\s»\.$/;
  await expect(log).toHaveText(ended);
  await expect(said(page, ended)).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-visited", "revisions");

  // The panel shows the task ended, and the history keeps the end with a link back to the screen
  // it was started from.
  await button.click();
  await expect(tasks.getByText("Réussie")).toBeVisible();
  const last = panel.getByRole("region", { name: "Messages" }).getByRole("listitem").first();
  await expect(last).toContainText("Tâche terminée");
  const back = last.getByRole("link", {
    name: "Gestion des révisions — Modernisation du poste de commande",
  });
  await expect(back).toHaveAttribute(
    "href",
    `/projects/${PROJECT}/revisions?revision_id=${REVISION}`,
  );
  await back.click();
  await expect(panel).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Gestion des révisions");
});

test("tells, by the entry of its task, the refusal of a result the browser came back with from its route, and takes it away from the address (#416)", async ({
  page,
}) => {
  // The route of the result sent the browser back to the screen it left: the result expired. The
  // fake back serves the first example of the read of a task, whatever the task asked.
  const screen = `/projects/${PROJECT}/revisions?revision_id=${REVISION}`;
  await openHydrated(page, `${screen}&refused_task=${TASK}&refusal=409%3ASTATE_FORBIDS_OPERATION`);
  const panel = page.getByRole("region", { name: "Tâches de fond" });
  await expect(panel.getByRole("alert")).toContainText(
    "L’état actuel ne permet pas cette opération.",
  );
  await expect(page).toHaveURL(screen);
});

test("the route of a result hands on the file the fake back serves, as the attachment it names, the browser kept on its screen (#416)", async ({
  page,
}) => {
  // The fake back serves the result of the export of the estimate, whatever the task asked. The
  // route is followed from the address alone: the read of a task the fake back serves first is a
  // marking, which made no result, so no entry offers the link — the component tests prove the
  // link of the entry and the screen it leaves from (`task-result.dom.test.tsx`).
  const screen = `/projects/${PROJECT}/revisions?revision_id=${REVISION}`;
  await openHydrated(page, screen);
  const result = `/tasks/01926f3a-7c00-7000-8000-000000000935/result?from=${encodeURIComponent(screen)}`;
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.evaluate((address) => {
      window.location.assign(address);
    }, result),
  ]);
  expect(download.suggestedFilename()).toBe("devis-poste-de-commande.xlsx");
  await expect(page).toHaveURL(screen);
});
