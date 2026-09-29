// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

// The session of the fake back is Camille Martin's, whose role grants the whole catalogue of
// permissions: every function is offered, and the menu of the account.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

test("the side bar folds into a rail of icons, whose entries keep their names in a tooltip, and stays folded", async ({
  page,
}) => {
  await page.goto("/portfolio/projects");
  const bar = page.getByRole("banner");
  const nav = page.getByRole("navigation", { name: "Fonctions" });
  await bar.getByRole("button", { name: "Replier la barre latérale" }).click();

  // Folded, the bar is a rail as wide as its icons, and each entry still names itself.
  await expect.poll(async () => (await nav.boundingBox())?.width).toBeLessThanOrEqual(48);
  await nav.getByRole("link", { name: "Projets", exact: true }).hover();
  await expect(page.getByRole("tooltip")).toHaveText("Projets");

  // The next visit finds it as the user left it; a block pressed in the rail unfolds it on its
  // functions.
  await page.reload();
  await expect(bar.getByRole("button", { name: "Déplier la barre latérale" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await nav.getByRole("button", { name: "Administration" }).click();
  await expect(bar.getByRole("button", { name: "Replier la barre latérale" })).toBeVisible();
  await nav.getByRole("link", { name: "Gestion des utilisateurs" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Gestion des utilisateurs");
});

test("an open block of the FBS is not painted as the page shown", async ({ page }) => {
  await page.goto("/portfolio/projects");
  const nav = page.getByRole("navigation", { name: "Fonctions" });
  const block = nav.getByRole("button", { name: "Portefeuille", exact: true });
  const current = nav.getByRole("link", { name: "Portefeuille de projets" });
  await expect(block).toHaveAttribute("aria-expanded", "true");
  await expect(current).toHaveAttribute("aria-current", "page");
  // Nothing under the pointer: each shows its own background.
  await page.mouse.move(900, 600);
  const background = (element: HTMLElement) => getComputedStyle(element).backgroundColor;
  expect(await block.evaluate(background)).not.toBe(await current.evaluate(background));
});

test("the bar keeps the search, the tasks and the account at its right where the address leads nowhere", async ({
  page,
}) => {
  await page.goto("/admin/nobody");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Introuvable");
  const bar = page.getByRole("banner");
  await expect(bar.getByRole("navigation", { name: "Fil d’Ariane" })).toHaveCount(0);
  const account = await bar.getByRole("button", { name: "Compte de Camille Martin" }).boundingBox();
  const width = page.viewportSize()?.width ?? 0;
  expect((account?.x ?? 0) + (account?.width ?? 0)).toBeGreaterThan(width - 40);
});

test("the bar shows where the page sits, and the side bar names the project its screen reads", async ({
  page,
}) => {
  await page.goto(`/projects/${PROJECT}/revisions/${REVISION}/risks`);
  const crumbs = page.getByRole("banner").getByRole("navigation", { name: "Fil d’Ariane" });
  await expect(crumbs.getByRole("link", { name: "Projets" })).toHaveAttribute("href", "/projects");
  await expect(
    crumbs.getByRole("link", { name: "Modernisation du poste de commande" }),
  ).toHaveAttribute("href", `/projects/${PROJECT}?revision_id=${REVISION}`);
  await expect(crumbs.getByText("Gestion des risques")).toHaveAttribute("aria-current", "page");
  await expect(
    page.getByRole("button", { name: "Modernisation du poste de commande PRJ-001 · En cours" }),
  ).toBeVisible();
});

test("the menu of the account leads to the pages of the account", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Compte de Camille Martin" }).click();
  await expect(page.getByRole("menuitem", { name: "Se déconnecter" })).not.toHaveAttribute(
    "aria-disabled",
  );
  await page.getByRole("menuitem", { name: "Changer le mot de passe" }).click();

  await expect(page).toHaveURL("/account/password");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Changer le mot de passe");
  await expect(page.getByLabel("Nouveau mot de passe")).toBeVisible();
  await expect(page).toHaveTitle("Changer le mot de passe — Waterfall");
});
