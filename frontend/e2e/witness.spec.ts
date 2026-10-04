// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { compile } from "./compile";

const PROJECT = "/projects/01926f3a-7c00-7000-8000-000000000001";
const REFERENCE = `${PROJECT}/revisions/01926f3a-7c00-7000-8000-000000000101`;

test("opens the list of projects, a project, and reads its planning and its estimate [WF-QUA-0050-A]", async ({
  page,
}) => {
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
  // the structure of the volumes of §4.6.2 (EP-02/L2): its first rows are in view.
  // The redirect, then the six thousand rows the server renders for the planning: more than the
  // five seconds of an assertion on a loaded runner, the time this one is given (#315).
  await page.getByRole("link", { name: "Référence" }).click();
  await expect(page).toHaveURL(new RegExp(`${REFERENCE}/planning`), { timeout: 15_000 });
  const planning = page.getByRole("grid", { name: "Grille de planning" });
  await expect(planning.getByRole("gridcell", { name: /Préparation 1\.1\.1$/ })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Planification");

  // The estimate, from the sidebar: the header, the six thousand rows of the structure — only
  // those in view rendered, the row count says them all —, the totals of the answer.
  await page.getByRole("link", { name: "Chiffrage et devis" }).click();
  const estimate = page.getByRole("grid", { name: "Grille de devis" });
  await expect(estimate).toHaveAttribute("aria-rowcount", "6002");
  await expect(estimate.getByRole("columnheader", { name: "Libellé" })).toBeVisible();
  await expect(estimate.getByRole("row", { name: /^4 .*Heures d'ingénierie/ })).toBeVisible();
  await expect(
    estimate.getByRole("gridcell", { name: /^Total — 1\s000 tâches, 5\s000 lignes$/ }),
  ).toBeVisible();
  // The indicators are there, with their figures: their first example is summed from the same
  // lines as the structure the grid shows (EP-02/L2), and says the same total.
  const indicators = page.getByRole("region", { name: "Indicateurs du devis" });
  await expect(indicators.getByRole("term").first()).toHaveText("Total du devis");
  await expect(indicators).toContainText(/60\s553\s621,36/);
});
