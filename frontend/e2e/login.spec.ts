// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { compile } from "./compile";

// The fake back grants the session of Camille Martin, whose role grants the whole catalogue of
// permissions, and the front sends it a fixed token (`WATERFALL_AUTH=mock`): `/login` has nothing
// to sign in to, and leads to the screen aimed at. Waterfall shows no sign-in screen and asks for
// no password: the identity provider does (WF-ADM-0140).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const LIFECYCLE = `/projects/${PROJECT}/lifecycle`;

test("`/login` leads to the screen aimed at, then signing out closes the sessions, forgetting what they left", async ({
  page,
  context,
}) => {
  await page.goto(`/login?next=${encodeURIComponent(LIFECYCLE)}`);

  // The screen aimed at, in the shell, which keeps the project it reads in; no sign-in page.
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
          key: "01926f3a-7c00-7000-8000-000000000931",
          task_id: "01926f3a-7c00-7000-8000-000000000931",
          kind: "revision_mark",
          status: "running",
        },
      ]),
    );
  });

  // The home page, where `/login` leads without a screen aimed at, compiled first
  // (`e2e/compile.ts`).
  await compile(page.request, "/");
  await page.getByRole("button", { name: "Compte de Camille Martin" }).click();
  await page.getByRole("menuitem", { name: "Se déconnecter" }).click();

  await expect(page).toHaveURL("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projets");
  expect((await context.cookies()).map(({ name }) => name)).not.toContain("wf_last_project");
  expect(
    await page.evaluate(() => window.sessionStorage.getItem("wf_background_tasks")),
  ).toBeNull();
});

test("`/login` follows a path of the front only: no screen aimed at, or another site, leads home", async ({
  page,
}) => {
  await compile(page.request, "/");
  await page.goto("/login");
  await expect(page).toHaveURL("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projets");

  await page.goto(`/login?next=${encodeURIComponent("https://elsewhere.example/")}`);
  await expect(page).toHaveURL("/");
  await page.goto(`/login?next=${encodeURIComponent("//elsewhere.example/")}`);
  await expect(page).toHaveURL("/");
});

test("no screen asks for a password or offers to change one", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByLabel("Mot de passe", { exact: false })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Mot de passe oublié ?" })).toHaveCount(0);

  await page.goto("/account");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mon compte");
  await expect(page.getByRole("main")).toContainText("camille.martin@example.com");
  await expect(page.getByRole("radiogroup", { name: "Langue" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Changer le mot de passe" })).toHaveCount(0);
  await expect(page.getByLabel("Mot de passe", { exact: false })).toHaveCount(0);

  await page.goto("/account/password");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Introuvable");

  await page.goto("/login/reset");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Introuvable");
});

test("the screens of the account show it, and offer its avatar", async ({ page }) => {
  await page.goto("/account");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mon compte");

  await page.goto("/account/avatar");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Changer l’avatar");
  await expect(page.getByLabel("Image PNG ou JPEG")).toBeVisible();
});
