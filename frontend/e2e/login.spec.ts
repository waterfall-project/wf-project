// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { compile } from "./compile";

// The fake back opens the session of Camille Martin, whose role grants the whole catalogue of
// permissions, and lists the three providers of its first example: the local accounts, the
// directory and the identity provider.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const LIFECYCLE = `/projects/${PROJECT}/lifecycle`;

test("signs in, comes to the screen aimed at, then signs out to the sign-in page, forgetting what the session left", async ({
  page,
  context,
}) => {
  await page.goto(`/login?next=${encodeURIComponent(LIFECYCLE)}`);

  // The way in stands outside the shell: neither bar nor side bar.
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Connexion");
  await expect(page.getByRole("banner")).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Fonctions" })).toHaveCount(0);
  await expect(page.getByRole("main")).toContainText("l’annuaire « Annuaire Exemple »");
  await expect(page.getByRole("link", { name: "Se connecter avec Exemple SSO" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Mot de passe oublié ?" })).toHaveAttribute(
    "href",
    "/login/reset",
  );
  await expect(page).toHaveTitle("Connexion — Waterfall");

  await page.getByLabel("Adresse électronique").fill("camille.martin@example.com");
  await page.getByLabel("Mot de passe", { exact: true }).fill("le mot de passe de Camille");
  await page.getByRole("button", { name: "Se connecter" }).click();

  // The screen aimed at, in the shell, which keeps the project it reads in.
  await expect(page).toHaveURL(LIFECYCLE);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Cycle de vie du projet");
  await expect(page.getByRole("navigation", { name: "Fonctions" })).toBeVisible();
  await expect
    .poll(async () => (await context.cookies()).some(({ name }) => name === "wf_last_project"))
    .toBe(true);
  // A background task the tab keeps for a reload, as the tracker keeps one that runs.
  await page.evaluate(() => {
    window.sessionStorage.setItem(
      "wf_background_tasks",
      JSON.stringify([
        {
          key: "01926f3a-7c00-7000-8000-000000000901",
          task_id: "01926f3a-7c00-7000-8000-000000000901",
          kind: "revision_mark",
          status: "running",
        },
      ]),
    );
  });

  await page.getByRole("button", { name: "Compte de Camille Martin" }).click();
  await page.getByRole("menuitem", { name: "Se déconnecter" }).click();

  await expect(page).toHaveURL("/login");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Connexion");
  expect((await context.cookies()).map(({ name }) => name)).not.toContain("wf_last_project");
  expect(
    await page.evaluate(() => window.sessionStorage.getItem("wf_background_tasks")),
  ).toBeNull();
});

test("signs in without a screen aimed at, and comes to the list of projects", async ({ page }) => {
  // The home, the list of projects, reached by the sign-in, compiled first (`e2e/compile.ts`).
  await compile(page.request, "/");
  await page.goto("/login");
  await page.getByLabel("Adresse électronique").fill("camille.martin@example.com");
  await page.getByLabel("Mot de passe", { exact: true }).fill("le mot de passe de Camille");
  await page.getByRole("button", { name: "Se connecter" }).click();

  await expect(page).toHaveURL("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projets");
});

test("asks for the link of a forgotten password, outside the shell", async ({ page }) => {
  await compile(page.request, "/login/reset");
  await page.goto("/login");
  await page.getByRole("link", { name: "Mot de passe oublié ?" }).click();

  await expect(page).toHaveURL("/login/reset");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mot de passe oublié");
  await expect(page.getByRole("banner")).toHaveCount(0);
  await page.getByLabel("Adresse électronique").fill("camille.martin@example.com");
  const send = page.getByRole("button", { name: "Envoyer le lien" });
  await send.click();
  await expect(page.getByRole("status")).toHaveText(
    "Si un compte correspond à cette adresse, un lien vient de lui être envoyé.",
  );
  // The focus stays on the button pressed: it was never disabled under it.
  await expect(send).toBeFocused();
});

test("the screens of the account show it, and offer its password and its avatar", async ({
  page,
}) => {
  await compile(page.request, "/account/password");
  await page.goto("/account");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mon compte");
  await expect(page.getByRole("main")).toContainText("camille.martin@example.com");
  await expect(page.getByRole("radiogroup", { name: "Langue" })).toBeVisible();

  await page.getByRole("link", { name: "Changer le mot de passe" }).click();
  await expect(page).toHaveURL("/account/password");
  await expect(page.getByLabel("Mot de passe actuel")).toBeVisible();
  await expect(page).toHaveTitle("Changer le mot de passe — Waterfall");

  await page.goto("/account/avatar");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Changer l’avatar");
  await expect(page.getByLabel("Image PNG ou JPEG")).toBeVisible();
});
