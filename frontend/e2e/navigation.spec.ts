// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

import { compile } from "./compile";
import { setExpanded } from "./hydration";

// The session of the fake back grants the whole catalogue of permissions: every function
// of the navigation is offered.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_PROJECT = `/projects/${PROJECT}/revisions/${REVISION}`;
// A sub-project of the project, in the examples of the contract (`subprojects.json`).
const CONTEXT = "?subproject_id=01926f3a-7c00-7000-8000-000000000801&as_of=2026-05-31";

/**
 * Follow a link of the navigation — opening first the block of the FBS it is in, outside any
 * project, once React answers the press (`setExpanded`) —, and check the screen it leads to names
 * its function.
 */
async function open(page: Page, name: string, block?: string) {
  const nav = page.getByRole("navigation", { name: "Fonctions" });
  if (block !== undefined) {
    await setExpanded(nav.getByRole("button", { name: block, exact: true }), true);
  }
  await nav.getByRole("link", { name }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(name);
}

test("a user who opened no project reaches the portfolio, the reference, the administration and the status screen [WF-IHM-0010-A]", async ({
  page,
}) => {
  // The screens of their own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, "/portfolio/projects", "/reference/costs", "/admin/users", "/system");
  await page.goto("/");
  await open(page, "Portefeuille de projets", "Portefeuille");
  await expect(page).toHaveURL("/portfolio/projects");
  await open(page, "Paramètres de coûts", "Paramètres applicatifs");
  await open(page, "Gestion des utilisateurs", "Administration");
  await open(page, "Surveillance de l’état du système", "Administration");
  await expect(page).toHaveURL("/system");
  await expect(page).toHaveTitle("Surveillance de l’état du système — Waterfall");
  // No project was opened: there is none to go back to.
  await expect(page.getByRole("link", { name: "Retour au projet" })).toHaveCount(0);
});

test("the way back to the previous project from a function outside any project finds the same context [WF-IHM-0010-A]", async ({
  page,
}) => {
  // The screens of their own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, "/portfolio/projects", `${IN_PROJECT}/risks`);
  await page.goto(`${IN_PROJECT}/remaining${CONTEXT}`);
  await open(page, "Gestion des risques");
  await expect(page).toHaveURL(`${IN_PROJECT}/risks${CONTEXT}`);
  await expect(page).toHaveTitle(
    "Gestion des risques · Modernisation du poste de commande — Waterfall",
  );

  await open(page, "Portefeuille de projets", "Portefeuille");
  await page.getByRole("link", { name: "Retour au projet" }).click();
  await expect(page).toHaveURL(`${IN_PROJECT}/risks${CONTEXT}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Gestion des risques");

  // The context outlives the page: a new visit to a function outside any project leads
  // back to it, from the cookie of the front.
  await page.goto("/system");
  await page.getByRole("link", { name: "Retour au projet" }).click();
  await expect(page).toHaveURL(`${IN_PROJECT}/risks${CONTEXT}`);
});

test("a project opened without a revision to read in offers the functions of the project itself", async ({
  page,
}) => {
  // The lifecycle, a screen of its own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, `/projects/${PROJECT}/lifecycle`);
  await page.goto(`/projects/${PROJECT}`);
  await open(page, "Cycle de vie du projet");
  await expect(page).toHaveURL(`/projects/${PROJECT}/lifecycle`);
  await expect(
    page
      .getByRole("navigation", { name: "Fonctions" })
      .getByRole("link", { name: "Planification" }),
  ).toHaveCount(0);
});

test("the tab bears the icon of the product", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Projets — Waterfall");
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute("href", /^\/icon\.svg/);
});
