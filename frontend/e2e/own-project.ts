// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A project the account of the run creates in the service, for the paths that write: the account is
 * its project manager as its creator (WF-PRJ-0060), and no other path reads it. The witness is never
 * written by a path (`mode.ts`: the account of the run is not a project manager of PRJ-001, #2193).
 */
import { randomBytes } from "node:crypto";

import { type APIRequestContext, type Browser, expect, type Page } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";
import { frontToken, type LocalPerson } from "./service/realm";

const API = `${process.env.WATERFALL_API_ADDRESS ?? ""}/api/v1`;

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

/**
 * Open a revision in progress on the project, as a user does from its revisions: the project goes to
 * pricing (WF-CYC-0090), and the address of the revision is reached.
 */
export async function openRevision(page: Page, own: OwnProject): Promise<void> {
  await openHydrated(page, `${own.path}/revisions`);
  await page
    .getByRole("main")
    .getByRole("region", { name: "Commandes" })
    .getByRole("button", { name: "Ouvrir une révision en cours" })
    .click();
  await expect(page).toHaveURL(/\?revision_id=[0-9a-f-]{36}$/, { timeout: WORKING });
}

/**
 * Write the contributors of a project by the API, under the token of its creator: she stays project
 * manager, and the other account is inscribed with the quality given. The screen of the contributors
 * proposes the accounts of the estimate alone (`listContributorSuggestions`), which a project just
 * created has none of.
 */
export async function inscribe(
  browser: Browser,
  calls: APIRequestContext,
  creator: LocalPerson,
  other: LocalPerson,
  own: OwnProject,
  kind: "contributor" | "project_manager" = "contributor",
): Promise<void> {
  const headers = { Authorization: `Bearer ${await frontToken(browser, creator)}` };
  const id = own.path.split("/").at(-1) ?? "";
  const read = await calls.get(`${API}/projects/${id}/contributors`, { headers });
  expect(read.status(), "GET contributors").toBe(200);
  const body = (await read.json()) as { lock_version: unknown };
  // A list read whole carries its counter; a null one is a filtered read, which the write refuses.
  if (typeof body.lock_version !== "number") {
    throw new Error("the contributors read whole carry no lock_version");
  }
  const written = await calls.put(`${API}/projects/${id}/contributors`, {
    headers,
    data: {
      contributors: [
        { user_id: creator.id, kind: "project_manager" },
        { user_id: other.id, kind },
      ],
      lock_version: body.lock_version,
    },
  });
  expect(written.status(), "PUT contributors").toBe(200);
}
