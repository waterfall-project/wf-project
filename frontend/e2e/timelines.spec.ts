// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page } from "@playwright/test";

import { columnsOf } from "./columns";
import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { scrollToPosition } from "./scroll";
import { inService, test } from "./mode";
import { isServerAction } from "./server-action";

// The timelines screen is served by the service (US-1400): the paths tagged `@shared` play against
// it, the witness' two timelines read and the one the path makes itself written; the others keep
// to the fake back, which keeps nothing of what they write.
//
// The inscription of a task to a timeline, from the menu of its cell (US-0480, WF-PLA-0060), against
// the fake back. It keeps nothing: it serves the first example of each read, and the first of
// `setNodeTracking` whatever was sent, the task « Revue de conception » inscribed to the timeline
// « Revue client » — the answer the grid shows in place of the row it read. What the grid sends is
// proven by `choice-menu.dom.test.tsx`; the journey proves the menu, the answer shown in the column
// that the account shows, and the sentence the screen says, in a browser. The journey reads the
// structure by a mark the generator writes (`test_the_marks_the_journeys_read`): row 5, the task
// « Revue de conception », not yet inscribed to a timeline; and by ranks among the tasks, which
// `test_the_ranks_among_the_tasks_the_planning_journeys_read` holds (tools/tests/
// test_mockstructure.py): row 5 is the 4th task, row 6, the milestone after it, the 5th.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;
const SAID = "Chronologies de « Revue de conception » mises à jour.";

/** Open the submenu « Chronologies » of the menu of the cell of a row's label. */
async function openTimelines(page: Page, row: Locator, label: number): Promise<Locator> {
  await row.getByRole("gridcell").nth(label).click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Chronologies" })
    .click();
  return page.getByRole("menu", { name: "Chronologies" });
}

test("inscribes a task to a timeline from the menu of its cell, sees it in the column that is shown, and takes it out [WF-PLA-0060-A]", async ({
  page,
}) => {
  // Une tâche inscrite apparaît dans la chronologie et disparaît lorsqu'elle est retirée.
  test.slow();
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  // The column of the timelines starts hidden, and is shown from the menu of the columns.
  await expect(grid.getByRole("columnheader", { name: "Chronologies" })).toHaveCount(0);
  await page.getByRole("button", { name: "Colonnes" }).click();
  await page.getByRole("menuitemcheckbox", { name: "Chronologies" }).click();
  await page.keyboard.press("Escape");
  const at = await columnsOf(grid, { label: "Libellé", timelines: "Chronologies" });

  const review = await scrollToPosition(grid, 4);
  await expect(review).toHaveAccessibleName(/^5 .*Revue de conception/);
  await expect(review.getByRole("gridcell").nth(at.timelines)).toHaveText("");

  // The boxes are the timelines of the project, none checked for this task.
  const boxes = await openTimelines(page, review, at.label);
  await expect(boxes.getByRole("menuitemcheckbox")).toHaveText([
    "Comité de pilotage",
    "Revue client",
  ]);
  await expect(boxes.getByRole("menuitemcheckbox", { name: "Revue client" })).toHaveAttribute(
    "aria-checked",
    "false",
  );
  await boxes.getByRole("menuitemcheckbox", { name: "Revue client" }).click();
  await expect(page.getByText(SAID)).toBeVisible({ timeout: WORKING });
  await expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
  // The row answered stands in place of the row read: the task is in the column, and its box checked.
  await expect(review.getByRole("gridcell").nth(at.timelines)).toHaveText("Revue client", {
    timeout: WORKING,
  });
  const again = await openTimelines(page, review, at.label);
  await expect(again.getByRole("menuitemcheckbox", { name: "Revue client" })).toHaveAttribute(
    "aria-checked",
    "true",
  );

  // Taken out: the same menu unchecks it, and the screen says the timelines were updated again.
  // The write is a server action, the one of the second click: the whole list, empty once the task is
  // taken out.
  const removal = page.waitForRequest(isServerAction);
  await again.getByRole("menuitemcheckbox", { name: "Revue client" }).click();
  expect((await removal).postData()).toContain('"entries":[]');
  await expect(page.getByText(SAID)).toBeVisible({ timeout: WORKING });
  await expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
  await expect(page.getByRole("alert")).toBeEmpty();
});

test("offers the time/time tracking of a milestone beside its timelines, checked as the milestone is inscribed [WF-PLA-0060-A]", async ({
  page,
}) => {
  // Le diagramme temps/temps ne suit que les jalons inscrits.
  test.slow();
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { label: "Libellé" });
  // Row 6 of the example, « Réception des études », a milestone inscribed to both timelines and to
  // the tracking.
  const milestone = await scrollToPosition(grid, 5);
  await expect(milestone).toHaveAccessibleName(/^6 .*Réception des études/);
  const boxes = await openTimelines(page, milestone, at.label);
  await expect(boxes.getByRole("menuitemcheckbox")).toHaveText([
    "Comité de pilotage",
    "Revue client",
    "Suivi temps/temps",
  ]);
  await expect(boxes.getByRole("menuitemcheckbox", { name: "Suivi temps/temps" })).toHaveAttribute(
    "aria-checked",
    "true",
  );
  await page.keyboard.press("Escape");
  await page.keyboard.press("Escape");
  // A task that is no milestone is offered the timelines alone.
  const task = await scrollToPosition(grid, 4);
  const others = await openTimelines(page, task, at.label);
  await expect(others.getByRole("menuitemcheckbox", { name: "Suivi temps/temps" })).toHaveCount(0);
});

// The frieze of the steering committee (US-0530, #1068), against the fake back: the studies and the
// commissioning, which overlap nowhere, in the first lane; the two receptions, milestones, across.
// The fake back keeps no preference: the journey proves the moves on the screen and what the frieze
// sends. A move refused for an overlap is proven by `timeline-chart.dom.test.tsx`: no timeline of
// the witness holds two rectangles that overlap.
const MOVED = "01926f3a-7c00-7000-8000-000000000565";

test("lays out the frieze of a timeline by the keyboard and the mouse, and records the lanes @shared", async ({
  page,
}) => {
  // The fake back renders, whatever the timeline, the whole volume of six thousand nodes: the lanes
  // and the last rectangle are not those of the timeline, which the service alone filters (#463).
  test.skip(!inService, "the fake back draws every node, not the tasks inscribed to the timeline");
  // The timelines read the structure of a thousand tasks: the bound of a grid.
  test.slow();
  await openHydrated(page, `${IN_REVISION}/timelines`);
  const frieze = page.getByRole("group", { name: /^Frise de la chronologie/ });
  await expect(frieze).toBeVisible({ timeout: WORKING });
  const commissioning = (lane: number) =>
    page.getByRole("img", {
      name: `Mise en service, du 21/12/2026 au 01/01/2027, couloir ${String(lane)}`,
    });
  await expect(
    page.getByRole("img", { name: "Études, du 02/03/2026 au 24/04/2026, couloir 1" }),
  ).toBeVisible();
  await expect(commissioning(1)).toBeVisible();
  await expect(
    page.getByRole("img", { name: "Réception des études, jalon le 24/04/2026" }),
  ).toBeAttached();

  // The keyboard: the last rectangle, a lane down — the lanes shown recorded after a pause.
  const recorded = page.waitForRequest(
    (request) => isServerAction(request) && (request.postData() ?? "").includes("lanes"),
  );
  await frieze.focus();
  await page.keyboard.press("End");
  await page.keyboard.press("Alt+ArrowDown");
  await expect(commissioning(2)).toBeVisible();
  const said = page.getByRole("status").filter({ hasText: "Mise en service" });
  await expect(said).toHaveText("« Mise en service » est dans le couloir 2.");
  expect((await recorded).postData() ?? "").toContain(`"${MOVED}":1`);
  // Alone in the last lane, it goes no lower: said, and nothing moves.
  await page.keyboard.press("Alt+ArrowDown");
  await expect(said).toHaveText("« Mise en service » est seule dans le dernier couloir.");
  await expect(commissioning(2)).toBeVisible();

  // The mouse: dragged a lane up, back beside the studies.
  const box = await commissioning(2).boundingBox();
  expect(box).not.toBeNull();
  const x = (box?.x ?? 0) + Math.min((box?.width ?? 0) / 2, 8);
  const y = (box?.y ?? 0) + (box?.height ?? 0) / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x, y - 32, { steps: 4 });
  await page.mouse.up();
  await expect(commissioning(1)).toBeVisible();
  await expect(said).toHaveText("« Mise en service » est dans le couloir 1.");
});

test("keeps the rectangle the keyboard reaches in view on a zoomed axis, and cuts a name the rectangle cannot hold [WF-IHM-0100-A] @shared", async ({
  page,
}) => {
  // Le focus reste visible.
  test.skip(
    !inService,
    "the fake back draws every node: the last rectangle is not the commissioning",
  );
  test.slow();
  await openHydrated(page, `${IN_REVISION}/timelines`);
  const frieze = page.getByRole("group", { name: /^Frise de la chronologie/ });
  await expect(frieze).toBeVisible({ timeout: WORKING });
  const commissioning = page.getByRole("img", { name: /^Mise en service, du 21\/12\/2026/ });
  await expect(commissioning).toBeVisible();
  // Fitted to the project, the rectangle of eleven days is narrow: its name is cut on the screen,
  // and whole in its accessible name and its text.
  await expect(commissioning).toHaveText("Mise en service");
  expect(await commissioning.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(
    true,
  );
  // Zoomed in until the axis outgrows the frame, the first rectangle is in view and the last is not.
  const zoomIn = page.getByRole("button", { name: "Zoom avant" });
  // The finest level is the day: the button is unavailable once it is reached, reached still to say
  // why in its tooltip (US-0580).
  while ((await zoomIn.getAttribute("aria-disabled")) !== "true") {
    await zoomIn.click();
  }
  await frieze.focus();
  await page.keyboard.press("Home");
  await expect(page.getByRole("img", { name: /^Études, du 02\/03\/2026/ })).toBeInViewport();
  await expect(commissioning).not.toBeInViewport();
  // End makes the last active, and the axis scrolls to it.
  await page.keyboard.press("End");
  await expect(commissioning).toBeInViewport({ ratio: 1 });
});

test("exports the frieze of a timeline as a PNG image, named after the project @shared [WF-PLA-0140-A]", async ({
  page,
}) => {
  // L'export produit un fichier PNG de la chronologie affichée.
  test.slow();
  await openHydrated(page, `${IN_REVISION}/timelines`);
  const figure = page.getByRole("figure", { name: "Comité de pilotage" });
  await expect(figure).toBeVisible({ timeout: WORKING });
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    figure.getByRole("button", { name: "Exporter en PNG" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe("chronologie-PRJ-001.png");
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) {
    chunks.push(chunk as Buffer);
  }
  // The signature of a PNG, then the width and the height of its header, twice as dense as the
  // screen.
  const image = Buffer.concat(chunks);
  expect(image.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
  expect([image.readUInt32BE(16), image.readUInt32BE(20)]).toEqual([2560, 1440]);
});

test("leads from the planning to the timelines of the project, read only", async ({ page }) => {
  // Three bounds of a screen of grid (`WORKING`): more than the thirty seconds of a test.
  test.slow();
  await compile(page.request, `${IN_REVISION}/timelines`);
  await openHydrated(page, `${IN_REVISION}/planning`);
  await page.getByRole("main").getByRole("link", { name: "Chronologies" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/timelines`, { timeout: WORKING });
  await expect(page).toHaveTitle("Chronologies · Modernisation du poste de commande — Waterfall");
  await expect(page.getByRole("region", { name: "Contexte de lecture" })).toContainText(
    "Modernisation du poste de commande",
  );
  // The timelines of the project; the screen asks the tasks of the one shown (`timeline_id`) and
  // draws what it is given. The fake back answers the same volume whatever the timeline: this path
  // proves the navigation, not the selection (the paths @shared above prove it against the service).
  // They read the structure of a thousand tasks: the bound of a grid.
  await expect(page.getByRole("link", { name: "Comité de pilotage" })).toHaveAttribute(
    "aria-current",
    "true",
    { timeout: WORKING },
  );
  // Another timeline, by the address: the structure read anew, in the bound of a grid.
  await page.getByRole("link", { name: "Revue client" }).click();
  await expect(page.getByRole("link", { name: "Revue client" })).toHaveAttribute(
    "aria-current",
    "true",
    { timeout: WORKING },
  );
  // The fake back's volume is drawn whole, its first rows holding « Réception usine »: the path
  // holds only because of that order, and says nothing of the customer's own selection.
  await expect(page.getByRole("main")).toContainText("Réception usine");
  await expect(
    page.getByText("Aucune tâche de cette révision n’est inscrite à cette chronologie."),
  ).toHaveCount(0);
});

test("creates a timeline by its name, and deletes the one shown once confirmed, the screen showing the first one left (EP-14/L44f)", async ({
  page,
}) => {
  // Two readings of the structure of a thousand tasks, each in the bound of a grid.
  test.slow();
  await openHydrated(page, `${IN_REVISION}/timelines`);
  const steering = page.getByRole("link", { name: "Comité de pilotage" });
  await expect(steering).toHaveAttribute("aria-current", "true", { timeout: WORKING });
  await expect(page.getByRole("note")).toHaveCount(0);
  await page.getByRole("button", { name: "Nouvelle chronologie" }).click();
  const form = page.getByRole("dialog", { name: "Nouvelle chronologie" });
  await form.getByRole("textbox", { name: "Nom" }).fill("Réunion de chantier");
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(form).toHaveCount(0);
  await expect(page.getByText("Chronologie « Réunion de chantier » créée.")).toBeVisible();

  await page
    .getByRole("button", { name: "Supprimer la chronologie «\u00a0Comité de pilotage\u00a0»" })
    .click();
  const confirmation = page.getByRole("dialog", { name: /^Supprimer la chronologie/ });
  await expect(confirmation).toContainText("les tâches et les jalons gardent leurs dates");
  await confirmation.getByRole("button", { name: "Supprimer" }).click();
  await expect(page.getByText("Chronologie « Comité de pilotage » supprimée.")).toBeVisible();
  await expect(steering).toHaveCount(0);
  await expect(page).toHaveURL(
    `${IN_REVISION}/timelines?timeline=01926f3a-7c00-7000-8000-000000001001`,
    { timeout: WORKING },
  );
  await expect(page.getByRole("link", { name: "Revue client" })).toHaveAttribute(
    "aria-current",
    "true",
    { timeout: WORKING },
  );
});

// What the service serves of the witness: the steering committee (`…1000`) holds the studies, the
// two receptions and the commissioning; the customer review (`…1001`), the two receptions alone.
const STEERING = "01926f3a-7c00-7000-8000-000000001000";
const CUSTOMER = "01926f3a-7c00-7000-8000-000000001001";
const STUDIES = /^Études, du /;
const RECEPTION = /^Réception usine, jalon le /;

/** The rectangle or the line a frieze draws for a task, named by its label. */
const drawn = (page: Page, name: RegExp) => page.getByRole("img", { name });

test("shows two timelines of a project with distinct selections, found again by another visit @shared [WF-PLA-0140-A]", async ({
  page,
}) => {
  // Deux chronologies d'un même projet portent des sélections distinctes et se retrouvent d'une
  // session à l'autre.
  test.slow();
  const steering = `${IN_REVISION}/timelines?timeline=${STEERING}`;
  const customer = `${IN_REVISION}/timelines?timeline=${CUSTOMER}`;
  await openHydrated(page, steering);
  await expect(drawn(page, STUDIES)).toBeVisible({ timeout: WORKING });
  await expect(drawn(page, RECEPTION)).toBeAttached();
  await expect(page.getByRole("note")).toHaveCount(0);
  await openHydrated(page, customer);
  await expect(drawn(page, RECEPTION)).toBeAttached({ timeout: WORKING });
  // The selection is the service's: the fake back draws all its nodes, whatever the timeline.
  if (inService) {
    await expect(drawn(page, STUDIES)).toHaveCount(0);
  }

  // Another visit — the page opened anew, then reloaded — reads the same two selections.
  await openHydrated(page, steering);
  await expect(drawn(page, STUDIES)).toBeVisible({ timeout: WORKING });
  await page.reload();
  await expect(drawn(page, STUDIES)).toBeVisible({ timeout: WORKING });
  await openHydrated(page, customer);
  await expect(drawn(page, RECEPTION)).toBeAttached({ timeout: WORKING });
  // The selection is the service's: the fake back draws all its nodes, whatever the timeline.
  if (inService) {
    await expect(drawn(page, STUDIES)).toHaveCount(0);
  }
});

/** Delete the timeline of the path from the screen, if it was made: the cleanup of a failed path too. */
async function removeTimeline(page: Page, label: string): Promise<void> {
  await openHydrated(page, `${IN_REVISION}/timelines`);
  const link = page.getByRole("link", { name: label });
  if ((await link.count()) === 0) {
    return;
  }
  await link.click();
  await page
    .getByRole("button", { name: `Supprimer la chronologie «\u00a0${label}\u00a0»` })
    .click();
  await page
    .getByRole("dialog", { name: /^Supprimer la chronologie/ })
    .getByRole("button", { name: "Supprimer" })
    .click();
  await expect(page.getByText(`Chronologie « ${label} » supprimée.`)).toBeVisible();
}

test("shows a task once inscribed to a timeline the path made, and no longer once taken out @shared [WF-PLA-0060-A]", async ({
  page,
}) => {
  // Une tâche inscrite apparaît dans la chronologie et disparaît lorsqu'elle est retirée.
  test.skip(!inService, "the fake back keeps no inscription: the grid test above proves the menu");
  test.slow();
  const label = `Chronologie de parcours ${String(Date.now())}`;
  const EMPTY = "Aucune tâche de cette révision n’est inscrite à cette chronologie.";
  try {
    await openHydrated(page, `${IN_REVISION}/timelines`);
    await page.getByRole("button", { name: "Nouvelle chronologie" }).click();
    const form = page.getByRole("dialog", { name: "Nouvelle chronologie" });
    await form.getByRole("textbox", { name: "Nom" }).fill(label);
    await form.getByRole("button", { name: "Créer" }).click();
    await expect(page.getByText(`Chronologie « ${label} » créée.`)).toBeVisible();
    await page.getByRole("link", { name: label }).click();
    await expect(page.getByRole("link", { name: label })).toHaveAttribute("aria-current", "true", {
      timeout: WORKING,
    });
    await expect(page.getByText(EMPTY)).toBeVisible({ timeout: WORKING });

    // Inscribed from the menu of the cell of « Revue de conception », not yet inscribed to any.
    await openHydrated(page, `${IN_REVISION}/planning`);
    const grid = page.getByRole("treegrid", { name: "Grille de planning" });
    const at = await columnsOf(grid, { label: "Libellé" });
    const review = await scrollToPosition(grid, 4);
    await expect(review).toHaveAccessibleName(/^5 .*Revue de conception/);
    const boxes = await openTimelines(page, review, at.label);
    await boxes.getByRole("menuitemcheckbox", { name: label }).click();
    await expect(page.getByText(SAID)).toBeVisible({ timeout: WORKING });
    await expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });

    // It appears in the timeline, and is found again once the page is read anew.
    const shown = `${IN_REVISION}/timelines`;
    await openHydrated(page, shown);
    await page.getByRole("link", { name: label }).click();
    await expect(drawn(page, /^Revue de conception, du /)).toBeVisible({ timeout: WORKING });
    await page.reload();
    await expect(drawn(page, /^Revue de conception, du /)).toBeVisible({ timeout: WORKING });

    // Taken out by the same menu, it disappears from the timeline.
    await openHydrated(page, `${IN_REVISION}/planning`);
    const again = await scrollToPosition(grid, 4);
    const menu = await openTimelines(page, again, at.label);
    await expect(menu.getByRole("menuitemcheckbox", { name: label })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    await menu.getByRole("menuitemcheckbox", { name: label }).click();
    await expect(page.getByText(SAID)).toBeVisible({ timeout: WORKING });
    await expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
    await openHydrated(page, shown);
    await page.getByRole("link", { name: label }).click();
    await expect(page.getByText(EMPTY)).toBeVisible({ timeout: WORKING });
    await expect(drawn(page, /^Revue de conception/)).toHaveCount(0);
  } finally {
    // The timeline the path made is deleted with it, an inscription with it, the witness left as it
    // was found — even when the path failed.
    await removeTimeline(page, label);
  }
});
