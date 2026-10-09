// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { compile } from "./compile";
import { WORKING } from "./hydration";

const PROJECT = "/projects/01926f3a-7c00-7000-8000-000000000001";
const REFERENCE = `${PROJECT}/revisions/01926f3a-7c00-7000-8000-000000000101`;

test("opens the list of projects, a project, and reads its planning and its estimate [WF-QUA-0050-A]", async ({
  page,
}) => {
  // Three screens of grids, each given the bound of one (`WORKING`): more than the thirty seconds
  // of a test, which the path is given three times of.
  test.slow();
  // Every screen after the first is reached by a click, and awaited five seconds: compiled
  // first. The revision itself is a route of its own, which sends on to its planning: the planning
  // is compiled too, as the redirect does not compile it in the browser's stead.
  await compile(page.request, PROJECT, REFERENCE, `${REFERENCE}/planning`, `${REFERENCE}/estimate`);
  await page.goto("/");
  await page.getByRole("link", { name: "Modernisation du poste de commande" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Modernisation du poste de commande",
  );
  // A revision opens on its planning, the first function of a revision. The fake back serves
  // the structure of the witness at the sizes of §4.6.2, its core first: its first rows in view.
  // The redirect, then the six thousand rows the server renders for the planning: more than the
  // five seconds of an assertion on a loaded runner, the time this one is given (#315).
  await page.getByRole("link", { name: "Référence" }).click();
  await expect(page).toHaveURL(new RegExp(`${REFERENCE}/planning`), { timeout: WORKING });
  const planning = page.getByRole("treegrid", { name: "Grille de planning" });
  await expect(planning.getByRole("gridcell", { name: /Études de détail$/ })).toBeVisible({
    timeout: WORKING,
  });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Planification");

  // The estimate, from the sidebar: the header, the six thousand rows of the structure — only
  // those in view rendered, the row count says them all —, the totals of the answer. The six
  // thousand rows the server renders, given the time of a screen of grid (#315).
  await page.getByRole("link", { name: "Chiffrage et devis" }).click();
  const estimate = page.getByRole("treegrid", { name: "Grille de devis" });
  await expect(estimate).toHaveAttribute("aria-rowcount", "6002", { timeout: WORKING });
  await expect(estimate.getByRole("columnheader", { name: "Libellé" })).toBeVisible();
  await expect(
    estimate.getByRole("row", { name: /^10 .*Raccordement des borniers/ }),
  ).toBeVisible();
  await expect(
    estimate.getByRole("gridcell", { name: /^Total — 1\s000 tâches, 5\s000 lignes$/ }),
  ).toBeVisible();
  // The indicators are there, with their figures: their first example is summed from the same
  // lines as the structure the grid shows (EP-02/L2), and says the same total.
  const indicators = page.getByRole("region", { name: "Indicateurs du devis" });
  await expect(indicators.getByRole("term").first()).toHaveText("Total du devis");
  await expect(indicators).toContainText(/65\s605\s723,89/);
});
