// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

import { columnsOf } from "./columns";
import { openHydrated, WORKING } from "./hydration";
import { scrollToPosition } from "./scroll";

// The inscription of a task to a timeline, from the menu of its cell (US-0480, WF-PLA-0060), against
// the fake back. It keeps nothing: it serves the first example of each read, and the first of
// `setNodeTracking` whatever was sent, the task « Revue de conception » inscribed to the timeline
// « Revue client » — the answer the grid shows in place of the row it read. What the grid sends is
// proven by `choice-menu.dom.test.tsx`; the journey proves the menu, the answer shown in the column
// that the account shows, and the sentence the screen says, in a browser. The journey reads the
// structure by a mark the generator writes (`test_the_marks_the_journeys_read`): row 5, the task
// « Revue de conception », not yet inscribed to a timeline.
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

  const review = await scrollToPosition(grid, 5);
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
  const removal = page.waitForRequest(
    (request) => request.method() === "POST" && request.headers()["next-action"] !== undefined,
  );
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
  const milestone = await scrollToPosition(grid, 6);
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
  const task = await scrollToPosition(grid, 5);
  const others = await openTimelines(page, task, at.label);
  await expect(others.getByRole("menuitemcheckbox", { name: "Suivi temps/temps" })).toHaveCount(0);
});

// The frieze of the steering committee (US-0530, #1068), against the fake back: the studies and the
// commissioning, which overlap nowhere, in the first lane; the two receptions, milestones, across.
// The fake back keeps no preference: the journey proves the moves on the screen and what the frieze
// sends. A move refused for an overlap is proven by `timeline-chart.dom.test.tsx`: no timeline of
// the witness holds two rectangles that overlap.
const MOVED = "01926f3a-7c00-7000-8000-000000000565";

test("lays out the frieze of a timeline by the keyboard and the mouse, and records the lanes", async ({
  page,
}) => {
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
    (request) =>
      request.method() === "POST" &&
      request.headers()["next-action"] !== undefined &&
      (request.postData() ?? "").includes("lanes"),
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

test("exports the frieze of a timeline as a PNG image, named after the project [WF-PLA-0140-A]", async ({
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
