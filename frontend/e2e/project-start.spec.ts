// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";

// The start of the planning of a project (US-0490/L3, #1058), as far as a fake back that keeps no state
// lets a journey go. It serves the project of the witness whatever the project of the address, its
// revision in progress with its thousand tasks: the encart « Démarrer le projet », which the server shows
// only while the main structure has no task, cannot be reached from the page, and the two journeys —
// create, work breakdown, generate, planning; create, drop a file, report, planning — need a service
// that remembers (#1350). Each step is proved on the examples of the contract by the tests of the
// components (`project-start.dom.test.tsx`) and of the pages (`page.test.tsx`, `screens.test.tsx`); here
// the journey is played as far as the witness allows.
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
