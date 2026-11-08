// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { columnsOf } from "./columns";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { EARLY, SEEDED, seedPlanning } from "./planning-seed";
import { isServerAction } from "./server-action";

// What the fake back cannot replay: it keeps nothing of what is written, and the witness holds no task
// in the service before its filler (US-1480). The paths below play against the service on a planning
// the run writes (`planning-seed.ts`), the six tasks of the plan, and are tagged `@shared`.
const SERVICE_ONLY = "the service keeps what is written, which the fake back does not";

test("reads from the service the columns of the planning, the three kinds of task, a task not started, and the physical progress of a leaf @shared [WF-PLA-0080-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const seeded = await seedPlanning(page, browser, request, manager, "Planning lu");
  await openHydrated(page, seeded.planning);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  // Chacune des colonnes citées est présente.
  for (const name of [
    "N°",
    "Libellé",
    "Description",
    "Mode de planification",
    "Durée",
    "Début",
    "Fin",
    "Prédécesseurs",
    "Avancement",
    "Calculé Avancement physique",
    "Calculé Marge",
    "Rattachement",
    "Démarrée le",
    "Terminée le",
    "Gantt",
  ]) {
    await expect(grid.getByRole("columnheader", { name, exact: true })).toBeVisible({
      timeout: WORKING,
    });
  }
  // Les trois sortes de tâches se distinguent sans lire leur durée.
  const summary = grid.getByRole("row", { name: new RegExp(`^1 .*${SEEDED[1]}`) });
  await expect(summary.getByRole("img", { name: "Tâche récapitulative" })).toBeVisible();
  const leaf = grid.getByRole("row", { name: new RegExp(`^2 .*${SEEDED[2]}`) });
  await expect(leaf.getByRole("img", { name: "Tâche", exact: true })).toBeVisible();
  const milestone = grid.getByRole("row", { name: new RegExp(`^4 .*${SEEDED[4]}`) });
  await expect(milestone.getByRole("img", { name: "Jalon", exact: true })).toBeVisible();
  // Une tâche terminée se distingue d’une tâche démarrée sans lire de colonne: against the service,
  // a task not started is told by its icon. A started and a completed task cannot be seeded before
  // EP-07: `setTaskProgress` needs a project in progress, which needs a reference revision that
  // bears lines (`revision_has_tasks_and_lines`); both icons are played against the fake back above.
  await expect(leaf.getByRole("img", { name: "Non démarrée" })).toBeVisible();
  // Une feuille ne porte pas d’avancement physique: its cell is empty, and the summary's is not.
  const at = await columnsOf(grid, { physical: "Calculé Avancement physique" });
  await expect(leaf.getByRole("gridcell").nth(at.physical)).toHaveText("");
  await expect(summary.getByRole("gridcell").nth(at.physical)).not.toHaveText("");
});

test("draws the links and the hierarchy of the planning, the critical path the service says, the successor an entry redates and the link in conflict @shared [WF-PLA-0090-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  // The seed links 2 → 3 → 4 → 5, finish to start, and adds a 7th task, manual and dated long before
  // the finish of 5, which it follows: a link in conflict. Task 6, linked to none, is off the path.
  const seeded = await seedPlanning(page, browser, request, manager, "Planning lié", {
    links: true,
  });
  await openHydrated(page, seeded.planning);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, {
    predecessors: "Prédécesseurs",
    start: "Début",
    gantt: "Gantt",
  });
  const row = (number: number, label: string) =>
    grid.getByRole("row", { name: new RegExp(`^${String(number)} .*${label}`) });
  const bar = (number: number, label: string) =>
    row(number, label).getByRole("gridcell").nth(at.gantt).getByRole("img");

  // Les liaisons et la hiérarchie sont visibles: the predecessors by their row number in the grid,
  // each link drawn in the Gantt by its arrow in the row of the successor, the hierarchy by the level.
  await expect(row(3, SEEDED[3])).toBeVisible({ timeout: WORKING });
  for (const [number, label, predecessor] of [
    [3, SEEDED[3], "2"],
    [4, SEEDED[4], "3"],
    [5, SEEDED[5], "4"],
  ] as const) {
    await expect(row(number, label).getByRole("gridcell").nth(at.predecessors)).toHaveText(
      new RegExp(`^${predecessor}`),
    );
    await expect(
      row(number, label)
        .getByRole("gridcell")
        .nth(at.gantt)
        .locator("g.stroke-muted-foreground polygon"),
    ).toHaveCount(1);
  }
  await expect(row(2, SEEDED[2])).toHaveAttribute("aria-level", "2");
  await expect(row(1, SEEDED[1])).toHaveAttribute("aria-level", "1");

  // …ainsi que le chemin critique: the tasks the service says are on it, by their icon and by the
  // name of their bar; the task linked to none is not.
  for (const [number, label] of [
    [2, SEEDED[2]],
    [3, SEEDED[3]],
    [4, SEEDED[4]],
    [5, SEEDED[5]],
  ] as const) {
    await expect(row(number, label).getByRole("img", { name: "Chemin critique" })).toBeVisible();
    await expect(bar(number, label)).toHaveAccessibleName(/ — critique/);
  }
  await expect(row(6, SEEDED[6]).getByRole("img", { name: "Chemin critique" })).toHaveCount(0);
  await expect(bar(6, SEEDED[6])).not.toHaveAccessibleName(/critique/);

  // The link in conflict the service renders, on the manual task and named in its bar.
  const early = row(7, EARLY);
  await expect(
    early.getByRole("img", { name: /^Liaison en conflit : 5FD vers la ligne 7$/ }),
  ).toBeVisible();
  await expect(bar(7, EARLY)).toHaveAccessibleName(
    /\s—\sLiaison en conflit\s:\s5FD vers la ligne 7$/,
  );

  // A task redated by a write: lengthening the duration of row 2 moves row 3, which follows it, as
  // the service answers; the front dates nothing.
  const startBefore = await row(3, SEEDED[3]).getByRole("gridcell").nth(at.start).innerText();
  const barBefore = await bar(3, SEEDED[3]).getAttribute("aria-label");
  const durations = await columnsOf(grid, { duration: "Durée" });
  await row(2, SEEDED[2]).getByRole("gridcell").nth(durations.duration).click();
  await page.keyboard.press("F2");
  await grid.getByRole("textbox", { name: "Durée" }).fill("9 j");
  await page.keyboard.press("Enter");
  await expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
  await expect(row(3, SEEDED[3]).getByRole("gridcell").nth(at.start)).not.toHaveText(startBefore, {
    timeout: WORKING,
  });
  expect(await bar(3, SEEDED[3]).getAttribute("aria-label")).not.toBe(barBefore);
});

test("enters a label, a duration and the predecessors of a task against the service, which redates the successor, and resolves a row number the search left out @shared [WF-PLA-0020-A] [WF-PLA-0030-A] [WF-PLA-0080-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const seeded = await seedPlanning(page, browser, request, manager, "Planning saisi");
  await openHydrated(page, seeded.planning);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, {
    label: "Libellé",
    duration: "Durée",
    start: "Début",
    predecessors: "Prédécesseurs",
  });
  const settled = () => expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
  const row = (number: number, label: string) =>
    grid.getByRole("row", { name: new RegExp(`^${String(number)} .*${label}`) });

  // The label, written by `updateTaskFacet`, is the one the row rendered shows.
  await row(5, SEEDED[5]).getByRole("gridcell").nth(at.label).click();
  await page.keyboard.press("F2");
  await grid.getByRole("textbox", { name: "Libellé" }).fill("Installation et essais");
  await page.keyboard.press("Enter");
  await expect(row(5, "Installation et essais")).toBeVisible({ timeout: WORKING });
  await settled();

  // The duration with its unit.
  await row(5, "Installation et essais").getByRole("gridcell").nth(at.duration).click();
  await page.keyboard.press("F2");
  await grid.getByRole("textbox", { name: "Durée" }).fill("3 sem");
  await page.keyboard.press("Enter");
  await settled();
  await expect(
    row(5, "Installation et essais").getByRole("gridcell").nth(at.duration),
  ).toContainText("3");

  // The predecessor « 5FD+2 j » on the commissioning: the service dates it after the installation.
  const commissioning = row(6, SEEDED[6]);
  const before = await commissioning.getByRole("gridcell").nth(at.start).innerText();
  await commissioning.getByRole("gridcell").nth(at.predecessors).click();
  await page.keyboard.press("F2");
  await grid.getByRole("textbox", { name: "Prédécesseurs" }).fill("5FD+2 j");
  await page.keyboard.press("Enter");
  await settled();
  await expect(commissioning.getByRole("gridcell").nth(at.predecessors)).toHaveText(/^5FD\+2\s*j$/);
  await expect(commissioning.getByRole("gridcell").nth(at.start)).not.toHaveText(before);

  // A number the search left out of the rows read is asked of the service (`resolveRowNumber`),
  // which names the task that bears it.
  const search = page.getByRole("searchbox", { name: "Rechercher un libellé" });
  await search.fill("Mise en service");
  await search.press("Enter");
  await expect(grid.getByRole("row", { name: /Installation et essais/ })).toHaveCount(0, {
    timeout: WORKING,
  });
  await commissioning.getByRole("gridcell").nth(at.predecessors).click();
  await page.keyboard.press("F2");
  await grid.getByRole("textbox", { name: "Prédécesseurs" }).fill("2");
  await page.keyboard.press("Enter");
  await settled();
  await expect(commissioning.getByRole("gridcell").nth(at.predecessors)).toHaveText(/^2/);

  // A number no task bears is refused at the cell, which stays open: the service answers 404.
  await commissioning.getByRole("gridcell").nth(at.predecessors).click();
  await page.keyboard.press("F2");
  await grid.getByRole("textbox", { name: "Prédécesseurs" }).fill("99");
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Aucune tâche de la structure ne porte l’un de ces numéros."),
  ).toBeVisible({ timeout: WORKING });
  await expect(grid.getByRole("textbox", { name: "Prédécesseurs" })).toHaveAttribute(
    "aria-invalid",
    "true",
  );
});

test("attaches tasks to the order items of the work breakdown from their cell, and the filter on an order item keeps the task that bears it, its subtree and its parents @shared [WF-PLA-0080-A] [WF-PLA-0170-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  // The work breakdown « Lot A » with « Poste A1 » and « Poste A2 » is written by `setWorkBreakdown`
  // in the seed; the attachment is written from the cell by `updateTaskFacet`.
  const seeded = await seedPlanning(page, browser, request, manager, "Planning rattaché", {
    breakdown: true,
  });
  const first = seeded.orderItems["Poste A1"] ?? "";
  const second = seeded.orderItems["Poste A2"] ?? "";
  await openHydrated(page, seeded.planning);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { attachment: "Rattachement" });
  const row = (number: number, label: string) =>
    grid.getByRole("row", { name: new RegExp(`^${String(number)} .*${label}`) });
  const attach = async (number: number, label: string, item: string, name: string) => {
    const cell = row(number, label).getByRole("gridcell").nth(at.attachment);
    await cell.click();
    await expect(cell).toBeFocused();
    await page.keyboard.press("F2");
    await page.getByRole("combobox", { name: "Rattachement" }).selectOption(item);
    const sent = page.waitForRequest(isServerAction);
    await page.keyboard.press("Enter");
    await sent;
    await expect(cell).toHaveText(name, { timeout: WORKING });
  };
  await attach(1, SEEDED[1], first, "Poste A1");
  await attach(3, SEEDED[3], second, "Poste A2");
  await page.reload();

  // Le filtre sur un poste ne laisse voir que la tâche qui le porte, son sous-arbre et ses parents:
  // « Poste A1 » is borne by the summary, whose subtree is rows 2 to 4.
  const filter = page.getByRole("combobox", { name: "Lot ou poste" });
  await filter.selectOption({ label: "Poste\u00a0: Poste A1" });
  await expect(page).toHaveURL(new RegExp(`order_item_id=${first}`), { timeout: WORKING });
  for (const [number, label] of [
    [1, SEEDED[1]],
    [2, SEEDED[2]],
    [3, SEEDED[3]],
    [4, SEEDED[4]],
  ] as const) {
    await expect(row(number, label)).toBeVisible({ timeout: WORKING });
  }
  await expect(grid.getByRole("row", { name: new RegExp(SEEDED[5]) })).toHaveCount(0);
  await expect(grid.getByRole("row", { name: new RegExp(SEEDED[6]) })).toHaveCount(0);

  // « Poste A2 » is borne by row 3, a leaf: it and its parent, the summary, and none of its siblings.
  await filter.selectOption({ label: "Poste\u00a0: Poste A2" });
  await expect(page).toHaveURL(new RegExp(`order_item_id=${second}`), { timeout: WORKING });
  await expect(row(3, SEEDED[3])).toBeVisible({ timeout: WORKING });
  await expect(row(1, SEEDED[1])).toBeVisible();
  await expect(grid.getByRole("row", { name: new RegExp(SEEDED[2]) })).toHaveCount(0);
  await expect(grid.getByRole("row", { name: new RegExp(SEEDED[4]) })).toHaveCount(0);
  await expect(grid.getByRole("row", { name: new RegExp(SEEDED[5]) })).toHaveCount(0);
});

test("searches the labels on the server, keeping the tasks that match and their parents, and changes the planning start date against the service @shared [WF-PLA-0080-A] [WF-PLA-0020-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const seeded = await seedPlanning(page, browser, request, manager, "Planning cherché");
  await openHydrated(page, seeded.planning);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  // La recherche sur un libellé ne laisse voir que les tâches correspondantes et leurs parents.
  const search = page.getByRole("searchbox", { name: "Rechercher un libellé" });
  await search.fill("Revue");
  await search.press("Enter");
  await expect(grid.getByRole("row", { name: new RegExp(SEEDED[3]) })).toBeVisible({
    timeout: WORKING,
  });
  await expect(grid.getByRole("row", { name: new RegExp(`^1 .*${SEEDED[1]}`) })).toBeVisible();
  await expect(grid.getByRole("row", { name: new RegExp(SEEDED[2]) })).toHaveCount(0);
  await expect(grid.getByRole("row", { name: new RegExp(SEEDED[6]) })).toHaveCount(0);

  // The start date of the plan, changed against `updateCostStructure`: the date answered is shown.
  const start = page.getByRole("region", { name: "Date de début de planning" });
  await start.getByRole("button", { name: "Modifier la date de début de planning" }).click();
  const form = start.getByRole("form", { name: "Modifier la date de début de planning" });
  await form.getByLabel("Date de début de planning").fill("2030-02-04");
  await form.getByRole("button", { name: "Confirmer la date" }).click();
  await expect(start).toContainText("04/02/2030", { timeout: WORKING });
  await page.reload();
  await expect(start).toContainText("04/02/2030", { timeout: WORKING });
});

test("draws the Gantt of the planning from the service, modifies no task from it, and folds a summary with the grid @shared [WF-PLA-0090-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const seeded = await seedPlanning(page, browser, request, manager, "Gantt servi");
  await openHydrated(page, seeded.planning);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { label: "Libellé", gantt: "Gantt" });
  const gantt = (number: number, label: string) =>
    grid
      .getByRole("row", { name: new RegExp(`^${String(number)} .*${label}`) })
      .getByRole("gridcell")
      .nth(at.gantt);
  await expect(gantt(2, SEEDED[2]).getByRole("img")).toHaveAccessibleName(
    /^Du \d\d\/\d\d\/\d{4} au \d\d\/\d\d\/\d{4}/,
    { timeout: WORKING },
  );
  await expect(gantt(4, SEEDED[4]).getByRole("img")).toHaveAccessibleName(
    /^Jalon le \d\d\/\d\d\/\d{4}/,
  );

  // Aucune action de la souris ou du clavier ne modifie une tâche depuis le Gantt.
  const sent: string[] = [];
  page.on("request", (request) => {
    if (request.method() !== "GET") {
      sent.push(`${request.method()} ${request.url()}`);
    }
  });
  const cell = gantt(2, SEEDED[2]);
  await cell.click();
  await expect(cell).toHaveAttribute("aria-readonly", "true");
  for (const key of ["Enter", "F2", "5", "Delete"]) {
    await page.keyboard.press(key);
  }
  await expect(grid.getByRole("textbox")).toHaveCount(0);
  // A drag of the mouse over a bar, from its start to the bar of another task: no date moves, and
  // nothing is sent.
  const barBefore = await cell.getByRole("img").getAttribute("aria-label");
  const box = await cell.boundingBox();
  const target = await gantt(5, SEEDED[5]).boundingBox();
  if (box === null || target === null) {
    throw new Error("the bars of the Gantt are laid out");
  }
  await page.mouse.move(box.x + box.width / 4, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(target.x + target.width / 2, target.y + target.height / 2, { steps: 8 });
  await page.mouse.up();
  await expect(cell.getByRole("img")).toHaveAttribute("aria-label", barBefore ?? "");
  // No write left with the drag: checked now, not only at the end of the path.
  // Wait for the network to settle so that a late write would have left already.
  await page.waitForLoadState("networkidle", { timeout: 5_000 });
  expect(sent).toEqual([]);

  // Une récapitulative pliée dans la grille l’est dans le Gantt, et réciproquement.
  const summary = grid.getByRole("row", { name: new RegExp(`^1 .*${SEEDED[1]}`) });
  const child = grid.getByRole("row", { name: new RegExp(`^2 .*${SEEDED[2]}`) });
  await summary.getByRole("gridcell").nth(at.label).getByRole("button", { name: "Plier" }).click();
  await expect(summary).toHaveAttribute("aria-expanded", "false");
  await expect(child).toHaveCount(0);
  await gantt(1, SEEDED[1]).getByRole("button", { name: "Déplier" }).click();
  await expect(summary).toHaveAttribute("aria-expanded", "true");
  await expect(child).toBeVisible();
  expect(sent).toEqual([]);
});

test("the account of the run, holding « Chef de projet » beside « Manager », creates a project and reaches its planning and the exchanges of the planning, FLX-01 and FLX-02, against the service @shared [WF-INTF-0010-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  // Un utilisateur porteur du rôle « chef de projet » crée un projet et atteint, sur un projet où il
  // est habilité, la planification (FBS-4.3) et l’échange des fichiers FLX-01 et FLX-02 : the rest of
  // the table of the flows is EP-07 to EP-10's.
  const seeded = await seedPlanning(page, browser, request, manager, "Chef de projet");
  await openHydrated(page, seeded.planning);
  await expect(page.getByRole("treegrid", { name: "Grille de planning" })).toBeVisible({
    timeout: WORKING,
  });
  await page.getByRole("main").getByRole("link", { name: "Imports et exports" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Imports et exports", {
    timeout: WORKING,
  });
  // FLX-02: the export of the schedule is offered to her. FLX-01, the import of a schedule, is played
  // by US-1430/L4 (#2589), with the import in two steps.
  const exports = page.getByRole("region", { name: "Demander un export" });
  await expect(
    exports.getByRole("combobox", { name: "Fichier à exporter" }).getByRole("option"),
  ).toContainText(["Planning MS Project"], { timeout: WORKING });
  await expect(exports.getByRole("button", { name: "Demander l’export" })).toBeVisible();
});
