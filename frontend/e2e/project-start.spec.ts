// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";

// The start of the planning of a project (US-0490/L3, #1058, L4 #1358), as far as a fake back that keeps
// no state lets a journey go. It serves the project of the witness, its revision in progress with its
// thousand tasks, whatever the address but one: there the encart cannot be reached, and the journeys
// that need a service that remembers — create, work breakdown, generate, planning; create, drop a file,
// report, planning — wait for it (#1350). The project created today is served at its own address, with
// no revision: its encart is reached, and its generation played to the planning. The rest is proved on
// the examples of the contract by the tests of the components (`project-start.dom.test.tsx`) and of
// the pages (`page.test.tsx`, `screens.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";

test("shows no encart on a project whose main structure bears its tasks, the server saying so [WF-PRJ-0030-A]", async ({
  page,
}) => {
  await openHydrated(page, `/projects/${PROJECT}`);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: WORKING });
  await expect(page.getByRole("region", { name: "Démarrer le projet" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Démarrer le projet" })).toHaveCount(0);
});

test("offers « Engendrer le planning » on the work breakdown reached from the encart, unavailable once the structure bears a task, naming the condition [WF-PRJ-0030-A]", async ({
  page,
}) => {
  await openHydrated(page, `/projects/${PROJECT}/settings?start=skeleton`);
  const section = page.getByRole("region", { name: "Engendrer le planning" });
  await expect(section).toBeVisible({ timeout: WORKING });
  const generate = section.getByRole("button", { name: "Engendrer le planning" });
  await expect(generate).toHaveAttribute("aria-disabled", "true");
  await expect(generate).toHaveAccessibleDescription(/Condition non remplie\s: .*tâche/);

  // Pressed, from the keyboard as from the pointer, it asks nothing and leads nowhere.
  const sent: string[] = [];
  page.on("request", (request) => {
    if (request.method() !== "GET") {
      sent.push(`${request.method()} ${request.url()}`);
    }
  });
  await generate.focus();
  await page.keyboard.press("Enter");
  // `force`: the button is aria-disabled, not disabled, and Playwright waits for an enabled one.
  await generate.click({ force: true });
  await expect(page).toHaveURL(/\/settings\?start=skeleton$/);
  expect(sent).toEqual([]);
});

test("offers no « Engendrer le planning » on the work breakdown when it is not asked for and unavailable", async ({
  page,
}) => {
  await openHydrated(page, `/projects/${PROJECT}/settings`);
  await expect(page.getByRole("region", { name: "Lotissement" })).toBeVisible({ timeout: WORKING });
  await expect(page.getByRole("button", { name: "Engendrer le planning" })).toHaveCount(0);
});

// The project created today, which the fake back serves at its own address with no revision (US-0490/L4,
// #1358): `createRevision` answers the revision 103, `generatePlanningSkeleton` the skeleton generated.
const CREATED = "01926f3a-7c00-7000-8000-000000000003";
const OPENED = "01926f3a-7c00-7000-8000-000000000103";

test("starts the planning of the project created from its encart: the work breakdown, then « Engendrer le planning » opens the revision and generates [WF-PRJ-0030-A]", async ({
  page,
}) => {
  test.slow();
  await compile(
    page.request,
    `/projects/${CREATED}/settings?start=skeleton`,
    `/projects/${CREATED}/revisions/${OPENED}/planning`,
  );
  await openHydrated(page, `/projects/${CREATED}`);
  const encart = page.getByRole("region", { name: "Démarrer le projet" });
  await expect(encart).toBeVisible({ timeout: WORKING });
  await expect(
    encart.getByRole("button", { name: "Importer un fichier MS Project" }),
  ).toBeVisible();
  await encart.getByRole("link", { name: "Planning automatique depuis le lotissement" }).click();
  await expect(page).toHaveURL(/\/settings\?start=skeleton$/, { timeout: WORKING });
  const generate = page
    .getByRole("region", { name: "Engendrer le planning" })
    .getByRole("button", { name: "Engendrer le planning" });
  await expect(generate).not.toHaveAttribute("aria-disabled", "true", { timeout: WORKING });
  await generate.click();
  await expect(page).toHaveURL(new RegExp(`/revisions/${OPENED}/planning`), { timeout: WORKING });
});
