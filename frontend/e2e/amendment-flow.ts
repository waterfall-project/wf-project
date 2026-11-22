// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The two gestures of an amendment against the service that the paths of `amendment-service.spec.ts`
 * and of the course of the project manager (`service/project-manager-risks.spec.ts`) both play: prepared
 * from the screen of the revisions, then merged from its banner, as a user does (US-2640, US-2650).
 */
import { expect, type Page } from "@playwright/test";

import { WORKING } from "./bounds";
import { openHydrated } from "./hydration";

/**
 * Prepare an amendment from the screen of a revision of a project, as a user does, and return the
 * address it opens.
 */
export async function prepare(
  page: Page,
  project: string,
  revision: string,
  label: string,
): Promise<string> {
  await openHydrated(page, `${project}/revisions?revision_id=${revision}`);
  const commands = page.getByRole("main").getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Préparer un avenant" }).click();
  const form = commands.getByRole("form", { name: "Préparer un avenant" });
  await form.getByRole("textbox", { name: "Libellé de l’avenant" }).fill(label);
  await form.getByRole("button", { name: "Créer l’avenant" }).click();
  await expect(page).toHaveURL(/\/planning\?structure=[0-9a-f-]{36}$/, { timeout: WORKING });
  return page.url();
}

/**
 * Merge the amendment the page shows: the report read, the version name asked, the merge handed to
 * the worker and followed to its end, which marks the revision that carries it and makes it the
 * reference.
 */
export async function contractualise(page: Page, version: string): Promise<void> {
  await page.getByRole("button", { name: "Contractualiser l’avenant" }).click();
  const merge = page.getByRole("form", { name: "Contractualiser l’avenant" });
  await expect(merge.getByRole("list", { name: "Écarts par objet" })).toBeVisible({
    timeout: WORKING,
  });
  await merge.getByRole("textbox", { name: "Nom de version" }).fill(version);
  await merge.getByRole("button", { name: "Confirmer la fusion" }).click();
  await expect(merge).toHaveCount(0, { timeout: WORKING });
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: `« ${version} » est la nouvelle révision de référence` }),
  ).toBeVisible({ timeout: WORKING });
  await expect(page.getByRole("button", { name: "Contractualiser l’avenant" })).toHaveCount(0);
}
