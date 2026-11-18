// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { WORKING } from "./bounds";
import { compile } from "./compile";
import { pngSize } from "./download";
import { openHydrated, openMenu } from "./hydration";
import { test } from "./mode";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/workload`;
const ORG_NODE = "01926f3a-7c00-7000-8000-000000000471";
const PLANNING = `/projects/${PROJECT}/revisions/${REVISION}/planning`;
// A task of the first role of the detail of the witness, at the third level of its planning, under
// « Approvisionnements — Ligne d'essais », under « Approvisionnements ».
const TASK = "Revue 1.2.11";
const TASK_NODE = "01926f3a-7c00-7000-8000-000100000311";

test.use({ colorScheme: "light" });

test("leads from the estimate to the workload on the reference budget, drawn in stacked bars, the capacity in its table, which a node of organisation filters at the server's @shared [WF-DEV-0070-A]", async ({
  page,
}) => {
  // Three bounds of a screen of grid (`WORKING`): the estimate of the witness, the workload read
  // from its lines, and the workload read again for the node chosen — more than the thirty seconds
  // of a test.
  test.slow();
  await compile(page.request, SCREEN);
  await openHydrated(page, `${ESTIMATE}?as_of=2026-03-16`);
  await page.getByRole("main").getByRole("link", { name: "Plan de charge" }).click();
  // The arrival on the workload keeps the bound of a screen of grid (`WORKING`), as the paths of
  // the screens follow a link, because the measure of the departure (`departure.spec.ts`, US-0800,
  // #1230) covers neither the departure from the estimate nor the arrival on the workload.
  await expect(page).toHaveURL(`${SCREEN}?as_of=2026-03-16&basis=reference_budget`, {
    timeout: WORKING,
  });
  await expect(page.getByRole("heading", { level: 1, name: "Plan de charge" })).toBeVisible({
    timeout: WORKING,
  });
  const region = page.getByRole("region", { name: "Plan de charge du projet" });
  const figure = region.getByRole("figure", { name: "Charge par rôle et par mois" });
  await expect(
    figure.getByRole("img", { name: /^Barres empilées de la charge/ }).locator("svg"),
  ).toBeVisible();
  // The capacity of each role in the table of the values, in regard of its load; no ratio of the
  // load to it in the plan of a project (#375, option b) [WF-DEV-0070-A].
  await figure.getByText("Valeurs du graphique").click();
  await expect(figure.getByRole("table").getByRole("columnheader")).toHaveText([
    "Rôle",
    "Mois",
    "Charge (h)",
    "Capacité (h par mois)",
    "Zone",
  ]);
  await region.getByLabel("Nœud d’organisation").selectOption(ORG_NODE);
  await region.getByRole("button", { name: "Afficher" }).click();
  // The choice is an address, the context kept: the server asks the API, the front filters nothing.
  await expect(page).toHaveURL(
    new RegExp(
      `^[^?]*${SCREEN}\\?as_of=2026-03-16&basis=reference_budget&.*org_node_id=${ORG_NODE}$`,
    ),
    { timeout: WORKING },
  );
});

// The load of the lines of the witness, filtered by the node chosen, is read again by the server:
// here the context is kept and the node read again.
test("reads the workload of the revision under way from its address, the context kept, the node of organisation chosen read again @shared [WF-DEV-0070-A]", async ({
  page,
}) => {
  await openHydrated(page, `${SCREEN}?as_of=2026-03-16`);
  const region = page.getByRole("region", { name: "Plan de charge du projet" });
  await expect(page.getByRole("heading", { level: 1, name: "Plan de charge" })).toBeVisible({
    timeout: WORKING,
  });
  await expect(region.getByText(/^Base : /)).toBeVisible();
  await region.getByLabel("Nœud d’organisation").selectOption(ORG_NODE);
  await region.getByRole("button", { name: "Afficher" }).click();
  await expect(page).toHaveURL(new RegExp(`as_of=2026-03-16&.*org_node_id=${ORG_NODE}$`), {
    timeout: WORKING,
  });
  // The node is read again by the server, which names it: the reading follows the filter.
  await expect(region.getByLabel("Nœud d’organisation")).toHaveValue(ORG_NODE);
  await expect(region.getByText(/^Base : /)).toBeVisible();
});

test("exports the workload, at the keyboard, as a PNG image drawn on a canvas, named after the project @shared [WF-IHM-0130-A]", async ({
  page,
}) => {
  await openHydrated(page, SCREEN);
  const figure = page.getByRole("figure", { name: "Charge par rôle et par mois" });
  const command = figure.getByRole("button", { name: "Exporter en PNG" });
  await command.focus();
  await expect(command).toBeFocused();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.keyboard.press("Enter"),
  ]);
  expect(download.suggestedFilename()).toBe("plan-de-charge-PRJ-001.png");
  // The signature of a PNG checked, then the width and the height of its header: an image of its
  // own size, twice as dense as the screen, whatever the size of the window.
  expect(await pngSize(download)).toEqual([2560, 1440]);
  // The instance out of the screen is gone with its canvas.
  await expect(page.locator("canvas")).toHaveCount(0);
});

test("offers the revision under way and only the other bases the project admits, the marked revision chosen with its basis alone @shared [WF-DEV-0070-A]", async ({
  page,
}) => {
  await openHydrated(page, `${SCREEN}?basis=current_remaining`);
  const region = page.getByRole("region", { name: "Plan de charge du projet" });
  const bases = await region
    .getByLabel("Base", { exact: true })
    .locator("option")
    .evaluateAll((options) => options.map((option) => (option as HTMLOptionElement).value));
  // A basis the project does not admit is absent, never offered to be refused (409, 422). The
  // witness PRJ-001 has a reference revision (the offer 100, designated by the loader) and marked
  // ones (100, 101), as the fake back's project does: both offer the three bases, the reference
  // budget first.
  expect(bases).toEqual(["reference_budget", "marked_remaining", "current_remaining"]);
  await expect(region.getByLabel("Révision marquée")).toHaveCount(1);
});

test("presents the detail of the plan under its chart, a tree grid from the role to the task with a column for each month, read only @shared [WF-DEV-0090-A]", async ({
  page,
}) => {
  // Propre à l'US : l'écran du plan de charge présente ce détail sous l'histogramme, en grille
  // arborescente du rôle à la tâche, une colonne par mois, en lecture seule, sans réglage propre.
  // Against the service, before US-2040/L2 (#3512), each role details no task: the roles alone.
  await openHydrated(page, SCREEN);
  const chart = page.getByRole("figure", { name: "Charge par rôle et par mois" });
  const region = page.getByRole("region", { name: "Détail par rôle et par tâche" });
  const detail = region.getByRole("treegrid", {
    name: "Détail du plan de charge par rôle et par tâche",
  });
  await expect(detail).toBeVisible({ timeout: WORKING });
  const [above, below] = await Promise.all([chart.boundingBox(), detail.boundingBox()]);
  expect(below?.y ?? 0).toBeGreaterThan((above?.y ?? 0) + (above?.height ?? 0));
  // A role at the first level of the tree, a column for each month after those of the task.
  await expect(detail.getByRole("row").nth(1)).toHaveAttribute("aria-level", "1");
  expect(await detail.getByRole("columnheader").count()).toBeGreaterThan(5);
  // No choice of its own: the basis and the node are those of the chart, above it.
  await expect(region.getByRole("combobox")).toHaveCount(0);
  await expect(region.getByRole("searchbox")).toHaveCount(0);
});

test("leads from a task of the detail to its row in the planning grid of the revision read, unfolded down to it and aimed at @shared [WF-DEV-0090-A]", async ({
  page,
}) => {
  // Depuis une tâche du détail, l'utilisateur atteint cette tâche dans la grille de planning, la
  // révision conservée. Three bounds of a screen of grid: the planning, the workload, the planning.
  test.slow();
  await compile(page.request, SCREEN);
  // The tree of the planning folded whole in the session, as the menu « Arbre » leaves it.
  await openHydrated(page, PLANNING);
  const menu = page.getByRole("menu");
  await openMenu(page.getByRole("button", { name: "Arbre" }), menu);
  await menu.getByRole("menuitem", { name: "Tout plier" }).click();
  const planning = page.getByRole("treegrid", { name: "Grille de planning" });
  const target = planning.getByRole("gridcell").filter({ hasText: new RegExp(`^${TASK}$`) });
  await expect(target).toHaveCount(0);

  await openHydrated(page, `${SCREEN}?as_of=2026-03-16`);
  const detail = page
    .getByRole("region", { name: "Détail par rôle et par tâche" })
    .getByRole("treegrid");
  await detail.getByRole("link", { name: TASK }).first().click();
  // The revision the basis reads, the context kept, the task named.
  await expect(page).toHaveURL(`${PLANNING}?as_of=2026-03-16&task=${TASK_NODE}`, {
    timeout: WORKING,
  });
  // Shown — its summaries unfolded — and aimed at: the active cell, the focus on it, in view.
  await expect(target).toBeFocused({ timeout: WORKING });
  await expect(target).toBeInViewport();
  const label = page.getByRole("gridcell").filter({ hasText: new RegExp(`^${TASK}$`) });
  await expect(planning.getByRole("row").filter({ has: label })).toHaveAttribute("aria-level", "3");
});
