// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page } from "@playwright/test";

import { compile } from "./compile";
import { setExpanded, WORKING } from "./hydration";
import { inService, test } from "./mode";

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

// Played in service too (`@shared`, EP-05): the reference is served. The role « Manager » of
// `mode.ts` holds no permission of the administration: the reference is read from one setting to
// the next (the administration has its own path, below).
test("a user who opened no project reads the cost settings, then the resource settings of the reference [WF-IHM-0010-A] @shared", async ({
  page,
}) => {
  // The screens of their own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, "/reference/costs", "/reference/resources");
  await page.goto("/reference/costs");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Paramètres de coûts");
  await open(page, "Paramètres de ressources");
  await expect(page).toHaveURL("/reference/resources");
  // No project was opened: there is none to go back to.
  await expect(page.getByRole("link", { name: "Retour au projet" })).toHaveCount(0);
});

// Against the fake back only: the service serves no portfolio (EP-11 lifts it) and no status
// screen (EP-13 lifts it, #2307); the administration is read elsewhere, under `@administration`
// (listed as not replayed in the guide).
test("a user who opened no project reaches the portfolio, the administration and the status screen from `/` [WF-IHM-0010-A]", async ({
  page,
}) => {
  // The screens of their own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, "/portfolio/projects", "/reference/costs");
  await page.goto("/");
  await open(page, "Portefeuille de projets", "Portefeuille");
  await expect(page).toHaveURL("/portfolio/projects");
  await open(page, "Paramètres de coûts", "Paramètres applicatifs");
  // No project was opened: there is none to go back to.
  await expect(page.getByRole("link", { name: "Retour au projet" })).toHaveCount(0);
});

// Played in service too (`@shared @administration`, US-1330): the account that reads the administration
// and the state, opened from the screen it signed in at.
test("a user who opened no project reaches the administration and the status screen from the navigation [WF-IHM-0010-A] @shared @administration", async ({
  page,
}) => {
  // The screens of their own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, "/admin/users", ...(inService ? [] : ["/system"]));
  await page.goto("/account");
  await open(page, "Gestion des utilisateurs", "Administration");
  await expect(page).toHaveURL("/admin/users");
  if (inService) {
    // The service does not serve the state of the system before EP-13 (`getSystemStatus`): its link
    // is offered, and the screen is read against the fake back alone.
    await expect(
      page.getByRole("navigation", { name: "Fonctions" }).getByRole("link", {
        name: "Surveillance de l’état du système",
      }),
    ).toBeVisible();
    return;
  }
  await open(page, "Surveillance de l’état du système", "Administration");
  await expect(page).toHaveURL("/system");
  await expect(page).toHaveTitle("Surveillance de l’état du système — Waterfall");
  // No project was opened: there is none to go back to.
  await expect(page.getByRole("link", { name: "Retour au projet" })).toHaveCount(0);
});

// Against the fake back only: it leads to the remaining and to the risks of PRJ-001, screens the
// service serves with EP-09 and EP-08 (listed as not replayed in the guide).
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

// Played in service too (`@shared`, EP-06): it leads to the planning of PRJ-001, which the service serves.
test("the address of a project leads to its revision, the reading context and its filters kept, the way to the screens of the revision then offered [WF-IHM-0010-A] @shared", async ({
  page,
}) => {
  await compile(page.request, `${IN_PROJECT}/planning`);
  await page.goto(`/projects/${PROJECT}${CONTEXT}`);
  await expect(page).toHaveURL(`${IN_PROJECT}/planning${CONTEXT}`);
  // The planning of the thousand tasks of the witness is read from the service: the bound of a
  // screen of grid, which five seconds of an assertion do not give it under several workers.
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Planification", {
    timeout: WORKING,
  });
});

// Played in service too (`@shared`, EP-04): the settings and the lifecycle of PRJ-001 are served,
// read by the account of the run, a reader of every project.
test("a screen of the project itself, read without a revision, offers the functions of the project itself (the project's own address leads to its revision, US-0720) [WF-IHM-0010-A] @shared", async ({
  page,
}) => {
  // The lifecycle, a screen of its own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, `/projects/${PROJECT}/settings`, `/projects/${PROJECT}/lifecycle`);
  await page.goto(`/projects/${PROJECT}/settings`);
  await open(page, "Cycle de vie du projet");
  await expect(page).toHaveURL(`/projects/${PROJECT}/lifecycle`);
  await expect(
    page
      .getByRole("navigation", { name: "Fonctions" })
      .getByRole("link", { name: "Planification" }),
  ).toHaveCount(0);
});

// Played in service too (`@shared`, EP-04): the home is served (US-0920/L2).
test("the tab bears the icon of the product @shared", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Projets — Waterfall");
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute("href", /^\/icon\.svg/);
});
