// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A risk the account of the run identifies in the service, for the paths that read or write its own
 * estimate (US-2640): the account is no contributor of PRJ-001 (#2193), so each path takes a project
 * of its own to In progress — the reference is read-only, the risks are declared on the current
 * revision, opened as a copy — and identifies the risk from the register, as a user does.
 */
import {
  type APIRequestContext,
  type Browser,
  expect,
  type Locator,
  type Page,
} from "@playwright/test";

import { WORKING } from "./bounds";
import { openHydrated } from "./hydration";
import { bringInProgress } from "./in-progress";
import { openRevision } from "./own-project";
import { SEEDED, type Seeded, seedPlanning } from "./planning-seed";
import type { LocalPerson } from "./service/realm";

/** What a path keeps of the risk it identified. */
export interface IdentifiedRisk {
  readonly seeded: Seeded;
  /** The address of the register of the risks of the current revision. */
  readonly risks: string;
  /** The address of the own estimate of the risk, which the identification leads to. */
  readonly own: string;
}

/** Take a project of the run to In progress, open its current revision and identify a risk there. */
export async function identifyRisk(
  page: Page,
  browser: Browser,
  calls: APIRequestContext,
  manager: LocalPerson | undefined,
  prefix: string,
  label: string,
): Promise<IdentifiedRisk> {
  const seeded = await seedPlanning(page, browser, calls, manager, prefix);
  await bringInProgress(page, calls, seeded);
  await openRevision(page, seeded.own);
  const current = new URL(page.url()).searchParams.get("revision_id");
  const risks = `${seeded.own.path}/revisions/${current ?? ""}/risks`;
  await openHydrated(page, risks);
  await page.getByRole("button", { name: "Identifier un risque" }).click();
  const identify = page.getByRole("dialog", { name: "Identifier un risque" });
  await identify.getByRole("textbox", { name: "Libellé" }).fill(label);
  await identify.getByRole("textbox", { name: "Probabilité (%)" }).fill("20");
  await identify.getByRole("combobox", { name: "Catégorie" }).selectOption({ index: 1 });
  await identify.getByRole("button", { name: "Créer" }).click();
  await expect(page).toHaveURL(/\/estimate\?.*structure=/, { timeout: WORKING });
  return { seeded, risks, own: page.url() };
}

/**
 * Add a task to the own estimate of a risk open in its grid, and give its row. The own estimate is
 * born whole, the copy of the main structure (US-3070, WF-RIS-0030-A): the grid holds the planning
 * seeded, and offers no « Insérer une tâche » of an empty grid. The task goes below the last one
 * seeded, from the menu of its cell, at the first level, after the line that task bears.
 */
export async function addOwnTask(page: Page, grid: Locator, label: string): Promise<Locator> {
  // The cell of a task that bears a line offers its fold in its name.
  const last = grid.getByRole("gridcell", { name: new RegExp(`^(Plier )?Tâche ${SEEDED[6]}$`) });
  await last.click();
  await last.click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Insérer au-dessous" })
    .click();
  const creation = page.getByRole("dialog", { name: "Insérer au-dessous" });
  await creation.getByRole("textbox", { name: "Libellé" }).fill(label);
  await creation.getByRole("button", { name: "Créer" }).click();
  await expect(page.getByText(`« ${label} » créée.`)).toBeVisible({ timeout: WORKING });
  return grid.getByRole("row", { name: new RegExp(`^\\d+ .*${label}`) });
}
