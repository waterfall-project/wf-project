// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A project the account of the run creates in the service, for the paths that write: the account is
 * its project manager as its creator (WF-PRJ-0060), and no other path reads it. The witness is never
 * written by a path (`mode.ts`: the account of the run is not a project manager of PRJ-001, #2193).
 */
import { randomBytes } from "node:crypto";

import { expect, type Page } from "@playwright/test";

import { WORKING } from "./hydration";

/** What a path keeps of the project it created: the address of its screen, and its label. */
export interface OwnProject {
  readonly path: string;
  readonly label: string;
}

/**
 * Create a project from the home, as a user does, and stay on its screen. No project is opened on
 * the home, nothing witnesses the hydration: the creation is pressed again until React opens its
 * form, and never once it is open.
 */
export async function createOwnProject(page: Page, prefix: string): Promise<OwnProject> {
  await page.goto("/");
  const main = page.getByRole("main");
  const creation = page.getByRole("dialog", { name: "Créer un projet" });
  await expect(async () => {
    if (!(await creation.isVisible())) {
      await main.getByRole("button", { name: "Créer un projet" }).click();
    }
    await expect(creation).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  const label = `${prefix} ${randomBytes(4).toString("hex")}`;
  await creation.getByRole("textbox", { name: "Libellé" }).fill(label);
  await creation.getByRole("button", { name: "Créer", exact: true }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/, { timeout: WORKING });
  return { path: new URL(page.url()).pathname, label };
}
