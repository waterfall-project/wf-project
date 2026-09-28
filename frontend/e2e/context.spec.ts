// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

// The fake back serves the first example of each operation: the project in progress, its
// current revision — a draft, without a version name —, and its two sub-projects. A marked
// revision is shown by the tests of the banner, from the example the contract names.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;

/** The banner of the reading context of the page. */
function banner(page: Page) {
  return page.getByRole("region", { name: "Contexte de lecture" });
}

test("each screen of the data of a project names the project and the revision shown [WF-IHM-0020-A]", async ({
  page,
}) => {
  await page.goto(`${IN_REVISION}/remaining`);
  await expect(banner(page).getByRole("definition")).toHaveText([
    "Modernisation du poste de commande",
    "Révision en cours",
    "En cours d’élaboration",
  ]);

  // From one function of the revision to the next, the banner names the same context.
  await page
    .getByRole("navigation", { name: "Fonctions" })
    .getByRole("link", { name: "Gestion des risques" })
    .click();
  await expect(page).toHaveURL(`${IN_REVISION}/risks`);
  await expect(banner(page)).toContainText("Modernisation du poste de commande");
  await expect(banner(page)).toContainText("Révision en cours");

  // The page of the project itself names it too.
  await page.goto(`/projects/${PROJECT}`);
  await expect(banner(page).getByRole("definition")).toHaveText([
    "Modernisation du poste de commande",
  ]);
});

test("an active filter is visible without opening the panel of filters [WF-IHM-0020-A]", async ({
  page,
}) => {
  await page.goto(`${IN_REVISION}/remaining?subproject_id=${SUBPROJECT}&as_of=2026-05-31`);
  const chips = banner(page).getByRole("list", { name: "Filtres actifs" }).getByRole("listitem");
  await expect(chips).toHaveText([
    "Sous-projet : SP-CMD — Poste de commande",
    "Date de calcul : 31 mai 2026",
  ]);
  await expect(chips.first()).toBeVisible();
  await expect(chips.last()).toBeVisible();

  // A chip lifts its filter, and the other one stays in the address and in the banner.
  await banner(page)
    .getByRole("link", { name: "Lever le filtre « Date de calcul : 31 mai 2026 »" })
    .click();
  await expect(page).toHaveURL(`${IN_REVISION}/remaining?subproject_id=${SUBPROJECT}`);
  await expect(chips).toHaveText(["Sous-projet : SP-CMD — Poste de commande"]);
});
