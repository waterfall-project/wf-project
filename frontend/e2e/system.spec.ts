// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

/** Check the page shows the one screen not found, inside the shell, and its way back. */
async function expectNotFound(page: Page) {
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Introuvable");
  await expect(page.getByRole("main")).toContainText(
    "Cette adresse ne mène à rien que vous puissiez consulter.",
  );
  await expect(page.getByRole("navigation", { name: "Fonctions" })).toBeVisible();
}

test("an address that leads nowhere shows the screen not found, inside the shell, with its way home", async ({
  page,
}) => {
  await page.goto("/admin/nobody");
  await expectNotFound(page);
  await page.getByRole("link", { name: "Retour à l’accueil" }).click();
  await expect(page).toHaveURL("/");
});

test("an address that names no project shows the same screen not found", async ({ page }) => {
  await page.goto("/projects/a.b/lifecycle");
  await expectNotFound(page);
  await page.goto("/projects/a.b");
  await expectNotFound(page);
});

test("the list of projects says nothing of a complete reference, and lists the projects", async ({
  page,
}) => {
  await page.goto("/projects");
  await expect(
    page.getByRole("link", { name: "Modernisation du poste de commande" }),
  ).toBeVisible();
  await expect(page.getByRole("region", { name: "Référentiel incomplet" })).toHaveCount(0);
  await expect(page.getByRole("main", { name: "Chargement de l’écran" })).toHaveCount(0);
});

test("every address not found answers with the same status, whatever route it takes", async ({
  page,
}) => {
  // A soft 404: the response streams from the skeleton on, its status sent before the page
  // knows the object is not found (not-found.tsx). What matters is that it is the same.
  const nowhere = await page.goto("/admin/nobody");
  await expectNotFound(page);
  const refused = await page.goto("/projects/a.b");
  await expectNotFound(page);
  expect(refused?.status()).toBe(nowhere?.status());
  await expect(page.locator('meta[name="robots"][content*="noindex"]').first()).toBeAttached();
});
