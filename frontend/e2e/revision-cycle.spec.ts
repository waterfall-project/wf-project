// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { createOwnProject, createService, employRole, openRevision } from "./own-project";
import { seedPlanning } from "./planning-seed";

// The cycle of the revisions, against the fake back and, tagged `@shared`, against the service.
//
// The fake back keeps no state: it serves the project in progress, its current revision and the
// history of three revisions, and answers each write with the first example of its operation. The
// commands are therefore read as the server lists them — the opening unavailable while a revision
// is current, the designation unavailable once the reference cannot be corrected —, and the
// abandon, available, is played to its end. The chain of the states — marked, designated, code
// entered, in progress, opened, the remaining entered — needs a service that remembers: each step
// is proved on the examples of the contract by the tests of the commands
// (`revision-commands.dom.test.tsx`).
//
// The service remembers (#1350): the cycle is played there on a project the account of the run
// creates (`own-project.ts`), and manages as its creator, never on the witness, whose revisions
// every other path reads — created, a revision opened, marked by the worker, the designation
// refused for the lack of tasks, another opened and abandoned (US-0970), opened again, the code
// entered, the project left (US-0990/L2). EP-07 reverses the refusal (US-1540): a reference that
// bears a task and a line is designated, and the code entered then takes the project to In
// progress.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

// What the service does not replay of the witness yet, as the guide lists it (« Un parcours de bout
// en bout »): the commands of PRJ-001 are listed to its project managers alone, and its reference
// stays undesignated until its tasks and lines are served (EP-07).
const NOT_REPLAYED_IN_SERVICE =
  "by decision the account of the run is not a project manager of PRJ-001 (#2193, option A), and its reference waits for its tasks and lines (EP-07)";

// The abandon of the witness's current revision would take it from every other path: the service
// plays the abandon on the project the cycle creates.
const WITNESS_KEPT = "the service abandons the revision of the project the cycle creates";

// The cycle needs a service that remembers what it wrote.
const SERVICE_ONLY = "the fake back keeps nothing of what is written";

// How long the worker is given to mark: a task taken from the queue, one transaction.
const MARKING = 60_000;

test("the opening of a second current revision and the designation beyond the correction are unavailable, naming their condition @shared [WF-REV-0010-A] [WF-REV-0040-A]", async ({
  page,
}) => {
  test.skip(inService, NOT_REPLAYED_IN_SERVICE);
  await openHydrated(page, `/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const main = page.getByRole("main");
  const commands = main.getByRole("region", { name: "Commandes" });
  const create = commands.getByRole("button", { name: "Ouvrir une révision en cours" });
  await expect(create).toHaveAttribute("aria-disabled", "true");
  await expect(create).toHaveAccessibleDescription(
    /^Condition non remplie\s: aucune révision en cours d’élaboration\.$/,
  );

  const designation = main.getByRole("region", { name: "Désignation de la référence" });
  const offer = designation.getByRole("listitem", { name: "Offre v1.0" });
  const designate = offer.getByRole("button", { name: "Désigner comme référence" });
  await expect(designate).toHaveAttribute("aria-disabled", "true");
  await expect(designate).toHaveAccessibleDescription(/référence encore corrigeable/);
  // Pressed from the keyboard, as the order of the keyboard keeps it, it does nothing.
  await designate.focus();
  await page.keyboard.press("Enter");
  await expect(designation.getByRole("form")).toHaveCount(0);
});

test("abandoning the current revision asks for a confirmation that says the return and the irreversibility, then leaves the revision @shared [WF-REV-0010-A]", async ({
  page,
}) => {
  test.skip(inService, WITNESS_KEPT);
  await openHydrated(page, `/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const main = page.getByRole("main");
  const commands = main.getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Abandonner la révision en cours" }).click();
  const form = commands.getByRole("form", { name: "Abandonner la révision en cours" });
  await expect(form).toContainText("dernière révision marquée");
  await expect(form).toContainText("irréversible");
  await form.getByRole("button", { name: "Confirmer l’abandon" }).click();
  // The screen leaves the address of the revision, which is no more, and its commands with it: the
  // history of the messages, in the shell, keeps what was told.
  await expect(page).toHaveURL(`/projects/${PROJECT}/revisions`);
  await page.getByRole("button", { name: /^Tâches et messages/ }).click();
  const told = page
    .getByRole("dialog", { name: "Tâches et messages" })
    .getByRole("region", { name: "Messages" })
    .getByRole("listitem")
    .first();
  await expect(told).toContainText("La révision en cours est abandonnée");
});

test("a project created, a revision opened, marked by the worker, the designation refused for the lack of tasks, another opened and abandoned, opened again, the code entered, the project left (#1350) @shared [WF-REV-0020-A] [WF-IHM-0080-A] [WF-REV-0090-A] [WF-REV-0010-A] [WF-CYC-0030-A] [WF-CYC-0090-A]", async ({
  page,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const main = page.getByRole("main");

  // Created from the home, its creator its project manager (WF-PRJ-0060), and a revision opened:
  // the screen leads to it.
  const own = await createOwnProject(page, "Cycle des révisions");
  await openRevision(page, own);
  const opened = page.url();
  const commands = main.getByRole("region", { name: "Commandes" });

  // Marked: without a version name, refused before anything is asked (WF-REV-0020); named, the
  // hand is back at once, and the tracker follows the task of the worker to its end (WF-IHM-0080).
  await commands.getByRole("button", { name: "Marquer la révision" }).click();
  const marking = commands.getByRole("form");
  await marking.getByRole("button", { name: "Marquer", exact: true }).click();
  await expect(marking.getByRole("textbox", { name: "Nom de version" })).toBeFocused();
  await marking.getByRole("textbox", { name: "Nom de version" }).fill("v1.0");
  await marking.getByRole("button", { name: "Marquer", exact: true }).click();
  await expect(commands.getByRole("form")).toHaveCount(0);
  const followed = page.getByRole("button", { name: /^Tâches et messages\s: 1 tâche suivie/ });
  await followed.click();
  const tasks = page
    .getByRole("dialog", { name: "Tâches et messages" })
    .getByRole("region", { name: "Tâches de fond" });
  const task = tasks.getByRole("listitem").filter({ hasText: "Marquage d’une révision « v1.0 »" });
  await expect(task.getByText("Réussie")).toBeVisible({ timeout: MARKING });
  await task.getByRole("button", { name: "Recharger l’écran" }).click();

  // Read anew, the revision is marked under its name, and the project has no current revision: the
  // opening is available again, the marking is refused, naming its condition (WF-REV-0090).
  const history = main.getByRole("table", { name: "Historique des révisions" });
  await expect(history.getByRole("row")).toHaveCount(2, { timeout: WORKING });
  const marked = history.getByRole("row").nth(1);
  await expect(marked).toContainText("v1.0");
  await expect(marked).toContainText("Marquée");
  await expect(page).toHaveURL(opened);
  const marker = commands.getByRole("button", { name: "Marquer la révision" });
  await expect(marker).toHaveAttribute("aria-disabled", "true");
  await expect(marker).toHaveAccessibleDescription(
    /^Condition non remplie\s: révision en cours d’élaboration\.$/,
  );
  const open = commands.getByRole("button", { name: "Ouvrir une révision en cours" });
  await expect(open).not.toHaveAttribute("aria-disabled", "true");

  // The designation of the marked revision is refused for the lack of tasks and lines, and says so
  // (WF-CYC-0030): pressed from the keyboard, it opens nothing. A reference that bears them is
  // designated by the next path.
  const designation = main.getByRole("region", { name: "Désignation de la référence" });
  const designate = designation
    .getByRole("listitem")
    .filter({ hasText: "v1.0" })
    .getByRole("button", { name: "Désigner comme référence" });
  await expect(designate).toHaveAttribute("aria-disabled", "true");
  await expect(designate).toHaveAccessibleDescription(
    /révision portant au moins une tâche et une ligne de devis/,
  );
  await designate.focus();
  await page.keyboard.press("Enter");
  await expect(designation.getByRole("form")).toHaveCount(0);

  // Another opened, then abandoned, confirmed: the project is back to its last marked revision,
  // which stays marked (WF-REV-0010, WF-REV-0090).
  await open.click();
  await expect(page).not.toHaveURL(opened, { timeout: WORKING });
  await expect(page).toHaveURL(/\?revision_id=[0-9a-f-]{36}$/);
  await expect(history.getByRole("row")).toHaveCount(3);
  await commands.getByRole("button", { name: "Abandonner la révision en cours" }).click();
  const abandon = commands.getByRole("form", { name: "Abandonner la révision en cours" });
  await abandon.getByRole("button", { name: "Confirmer l’abandon" }).click();
  await expect(page).toHaveURL(`${own.path}/revisions`, { timeout: WORKING });
  await expect(history.getByRole("row")).toHaveCount(2);
  await expect(history.getByRole("row").nth(1)).toContainText("v1.0");
  await expect(history.getByRole("row").nth(1)).toContainText("Marquée");

  // Opened again: a current revision once more, the history counting the marked one and it.
  await open.click();
  await expect(page).toHaveURL(/\?revision_id=[0-9a-f-]{36}$/, { timeout: WORKING });
  await expect(history.getByRole("row")).toHaveCount(3);

  // The code entered on the settings, kept once the page is read anew. Without a reference the
  // project stays in pricing, and the designation stays refused (WF-CYC-0030-A).
  await openHydrated(page, `${own.path}/settings`);
  await main.getByRole("button", { name: "Modifier le projet" }).click();
  const identity = page.getByRole("dialog", { name: /^Modifier/ });
  const code = `CYC-${own.label.slice(-4).toUpperCase()}`;
  await identity.getByRole("textbox", { name: /^Code projet/ }).fill(code);
  await identity.getByRole("button", { name: "Enregistrer" }).click();
  await expect(identity).toBeHidden({ timeout: WORKING });
  await page.reload();
  await expect(main.getByLabel("Paramètres du projet")).toContainText(code);
  await openHydrated(page, `${own.path}/lifecycle`);
  const states = main.getByRole("table", { name: "Historique des états" });
  await expect(states.getByRole("row")).toHaveCount(3);
  await expect(states.getByRole("row").last()).toContainText("Chiffrage");
  await openHydrated(page, `${own.path}/revisions`);
  await expect(designate).toHaveAttribute("aria-disabled", "true");
  // The project has no reference: no row of the history carries the mark (WF-CYC-0030-A).
  await expect(history).not.toContainText("Référence");

  // Left to Lost, from pricing, the current revision abandoned with it (WF-CYC-0090): the project
  // is terminal and lists no command.
  await openHydrated(page, `${own.path}/lifecycle`);
  const lifecycle = main.getByRole("region", { name: "Commandes" });
  await lifecycle.getByRole("button", { name: "Déclarer le projet perdu" }).click();
  const exit = lifecycle.getByRole("form", { name: "Déclarer le projet perdu" });
  await exit.getByRole("radio", { name: /^Abandonner la révision en cours/ }).check();
  await exit.getByRole("button", { name: "Confirmer la sortie" }).click();
  // The screen shows the state the service answered; the commands go with it, and with them the
  // note of the exit.
  await expect(main.getByRole("img", { name: "Perdu" }).first()).toBeVisible({ timeout: WORKING });
  await page.reload();
  await expect(states.getByRole("row").last()).toContainText("Perdu");
  await expect(lifecycle.getByRole("button")).toHaveCount(0);
  // The revision in progress went with the exit: the history keeps the marked one alone, and none
  // is still in progress (WF-CYC-0090-A).
  await openHydrated(page, `${own.path}/revisions`);
  await expect(history.getByRole("row")).toHaveCount(2);
  await expect(history.getByRole("row").nth(1)).toContainText("v1.0");
  await expect(history.getByRole("row").nth(1)).toContainText("Marquée");
  await expect(history).not.toContainText("En cours d’élaboration");
});

test("a reference that bears a task and a line is designated, the project stays in pricing until the code is entered and then passes In progress (US-1540) @shared [WF-CYC-0020-A] [WF-CYC-0030-A] [WF-CYC-0050-A] [WF-PRJ-0010-A]", async ({
  browser,
  page,
  playwright,
  manager,
}) => {
  if (!inService || manager === undefined) {
    test.skip(true, SERVICE_ONLY);
    return;
  }
  test.slow();
  const main = page.getByRole("main");
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    // A project of its own, its revision opened and its tasks written, and a line under one of
    // them, which employs the role of a service of its own (a project is chiffré without a code,
    // WF-PRJ-0010).
    const seeded = await seedPlanning(page, browser, calls, manager, "Passage En cours");
    const service = await createService(browser, calls, manager, "Passage");
    await employRole(calls, seeded.headers, seeded.ids, seeded.nodes[6] ?? "", service);

    // In pricing, the next state names what the project lacks, the line included (WF-CYC-0050).
    await openHydrated(page, `${seeded.own.path}/lifecycle`);
    const next = main.getByRole("region", { name: "Prochain état" });
    await expect(next).toContainText("révision portant au moins une tâche et une ligne de devis");
    await expect(next).toContainText("code projet renseigné");
    await expect(next).toContainText("révision de référence désignée");

    // The revision is marked by the worker.
    await openHydrated(page, `${seeded.own.path}/revisions?revision_id=${seeded.ids.revision}`);
    const commands = main.getByRole("region", { name: "Commandes" });
    await commands.getByRole("button", { name: "Marquer la révision" }).click();
    const marking = commands.getByRole("form");
    await marking.getByRole("textbox", { name: "Nom de version" }).fill("v1.0");
    await marking.getByRole("button", { name: "Marquer", exact: true }).click();
    await expect(commands.getByRole("form")).toHaveCount(0);
    await page.getByRole("button", { name: /^Tâches et messages\s: 1 tâche suivie/ }).click();
    const task = page
      .getByRole("dialog", { name: "Tâches et messages" })
      .getByRole("region", { name: "Tâches de fond" })
      .getByRole("listitem")
      .filter({ hasText: "Marquage d’une révision « v1.0 »" });
    await expect(task.getByText("Réussie")).toBeVisible({ timeout: MARKING });
    await task.getByRole("button", { name: "Recharger l’écran" }).click();

    // Carrying a task and a line, the marked revision is designated: no refusal (WF-CYC-0030).
    const designation = main.getByRole("region", { name: "Désignation de la référence" });
    const offer = designation.getByRole("listitem").filter({ hasText: "v1.0" });
    const designate = offer.getByRole("button", { name: "Désigner comme référence" });
    await expect(designate).not.toHaveAttribute("aria-disabled", "true", { timeout: WORKING });
    await designate.click();
    await designation.getByRole("button", { name: "Confirmer la désignation" }).click();
    const history = main.getByRole("table", { name: "Historique des révisions" });
    await expect(history.getByRole("row").nth(1)).toContainText("Référence", { timeout: WORKING });

    // Without a code the project stays in pricing, and the next state names the code alone.
    await openHydrated(page, `${seeded.own.path}/lifecycle`);
    const states = main.getByRole("table", { name: "Historique des états" });
    await expect(states.getByRole("row").last()).toContainText("Chiffrage");
    await expect(next).toContainText("code projet renseigné");
    await expect(next).not.toContainText("révision de référence désignée");
    // The revision now bears a task and a line: the condition is no longer named (WF-CYC-0050-A).
    await expect(next).not.toContainText(
      "révision portant au moins une tâche et une ligne de devis",
    );

    // The code entered takes the project In progress, without another action (WF-CYC-0020).
    await openHydrated(page, `${seeded.own.path}/settings`);
    await main.getByRole("button", { name: "Modifier le projet" }).click();
    const identity = page.getByRole("dialog", { name: /^Modifier/ });
    const code = `ENC-${seeded.own.label.slice(-8).toUpperCase()}`;
    await identity.getByRole("textbox", { name: /^Code projet/ }).fill(code);
    await identity.getByRole("button", { name: "Enregistrer" }).click();
    await expect(identity).toBeHidden({ timeout: WORKING });
    await openHydrated(page, `${seeded.own.path}/lifecycle`);
    await expect(states.getByRole("row").last()).toContainText("En cours", { timeout: WORKING });
  } finally {
    await calls.dispose();
  }
});
