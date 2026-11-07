// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { randomBytes } from "node:crypto";

import { expect } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";

// The cycle of the revisions, against the fake back and, tagged `@shared`, against the service.
//
// The fake back keeps no state: it serves the project in progress, its current revision and the
// history of three revisions, and answers each write with the first example of its operation. The
// commands are therefore read as the server lists them — the opening unavailable while a revision is
// current, the designation unavailable once the reference cannot be corrected —, and the abandon,
// available, is played to its end. The chain of the states — marked, designated, code entered, in
// progress, opened, the remaining entered — needs a service that remembers: each step is proved on
// the examples of the contract by the tests of the commands (`revision-commands.dom.test.tsx`).
//
// The service remembers (#1350): the cycle is played there on a project the account of the run
// creates, and manages as its creator — created, a revision opened, marked by the worker, another
// opened and abandoned (US-0970) —, never on the witness, whose revisions every other path reads.
// The rest of the cycle — reopened, the code entered, the exit, the designation refused — is
// US-0990/L2's.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

// What the service does not replay of the witness yet, as the guide lists it (« Un parcours de bout
// en bout »): the commands of PRJ-001 are listed to its project managers alone, and its reference is
// designated by US-0980/L2.
const NOT_REPLAYED_IN_SERVICE =
  "by decision the account of the run is not a project manager of PRJ-001 (#2193, option A), and US-0980/L2 designates its reference";

// The abandon of the witness's current revision would take it from every other path: the service
// plays the abandon on the project the cycle creates.
const WITNESS_KEPT = "the service abandons the revision of the project the cycle creates";

// The cycle needs a service that remembers what it wrote.
const SERVICE_ONLY = "the fake back keeps nothing of what is written";

// A project is created once the minimal reference holds an active role of resources (WF-CYC-0120),
// which US-0850 (EP-05) serves and loads with the witness: until it reaches this epic, the service
// refuses the creation, and the cycle does not play (#2194).
const BEFORE_US0850 = "the service creates no project before US-0850 serves the roles of resources";

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

test("a project created, a revision opened then marked by the worker, which keeps it marked, another opened then abandoned, back to the marked one (US-0970) @shared [WF-REV-0020-A] [WF-IHM-0080-A] [WF-REV-0090-A] [WF-REV-0010-A]", async ({
  page,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.skip(inService, BEFORE_US0850);
  test.slow();
  const main = page.getByRole("main");

  // Created from the home, its creator its project manager (WF-PRJ-0060). No project is opened
  // there, nothing witnesses the hydration: the creation is pressed again until React opens its
  // form, and never once it is open.
  await page.goto("/");
  const creation = page.getByRole("dialog", { name: "Créer un projet" });
  await expect(async () => {
    if (!(await creation.isVisible())) {
      await main.getByRole("button", { name: "Créer un projet" }).click();
    }
    await expect(creation).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  const label = `Cycle des révisions ${randomBytes(4).toString("hex")}`;
  await creation.getByRole("textbox", { name: "Libellé" }).fill(label);
  await creation.getByRole("button", { name: "Créer", exact: true }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/, { timeout: WORKING });
  const project = new URL(page.url()).pathname;

  // A revision opened: the screen leads to it.
  await openHydrated(page, `${project}/revisions`);
  const commands = main.getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Ouvrir une révision en cours" }).click();
  await expect(page).toHaveURL(/\?revision_id=[0-9a-f-]{36}$/, { timeout: WORKING });
  const opened = page.url();

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
  // opening is available again, the marking is not offered any more (WF-REV-0090).
  const history = main.getByRole("table", { name: "Historique des révisions" });
  await expect(history.getByRole("row")).toHaveCount(2, { timeout: WORKING });
  const marked = history.getByRole("row").nth(1);
  await expect(marked).toContainText("v1.0");
  await expect(marked).toContainText("Marquée");
  await expect(page).toHaveURL(opened);
  await expect(commands.getByRole("button", { name: "Marquer la révision" })).toHaveCount(0);
  const open = commands.getByRole("button", { name: "Ouvrir une révision en cours" });
  await expect(open).not.toHaveAttribute("aria-disabled", "true");

  // Another opened, then abandoned, confirmed: the project is back to its last marked revision,
  // which stays marked (WF-REV-0010, WF-REV-0090).
  await open.click();
  await expect(page).not.toHaveURL(opened, { timeout: WORKING });
  await expect(page).toHaveURL(/\?revision_id=[0-9a-f-]{36}$/);
  await expect(history.getByRole("row")).toHaveCount(3);
  await commands.getByRole("button", { name: "Abandonner la révision en cours" }).click();
  const abandon = commands.getByRole("form", { name: "Abandonner la révision en cours" });
  await abandon.getByRole("button", { name: "Confirmer l’abandon" }).click();
  await expect(page).toHaveURL(`${project}/revisions`, { timeout: WORKING });
  await expect(history.getByRole("row")).toHaveCount(2);
  await expect(history.getByRole("row").nth(1)).toContainText("v1.0");
  await expect(history.getByRole("row").nth(1)).toContainText("Marquée");
});
