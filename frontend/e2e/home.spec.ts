// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The home of a signed-in session (`/`), against the fake back and, tagged `@shared`, against the
 * service: it reads the projects (`listProjects`) and the readiness of the reference data
 * (`getReferenceReadiness`) the service serves since EP-04, and no longer renders « Introuvable »
 * for want of them (#1004). Its list in a card, « Créer un projet » filled at the right of the title
 * of the card, measured at 1366 points and at 911 — what a zoom of 150 % leaves of them (US-2130).
 */
import { expect, type Locator } from "@playwright/test";

import { inService, test } from "./mode";
import { scroller, withinBox } from "./scroll";

test("the home of a signed-in session renders against the service: its title, the filter of its list, no note of the mock-up and neither « not found » nor a request for a session; it only renders, the filter being carried by the back and projects.spec.ts (US-0920/L2, #1004) @shared [WF-IHM-0120-A]", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projets");
  await expect(page.getByRole("list", { name: "Filtres actifs" })).toContainText(
    "Projets : Mes projets (par défaut)",
  );
  await expect(page.getByRole("heading", { name: "Introuvable" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Session requise" })).toHaveCount(0);
  await expect(page.getByRole("note")).toHaveCount(0);
});

/** The box of an element in the page, measured. */
async function box(element: Locator) {
  const measured = await element.boundingBox();
  if (measured === null) {
    throw new Error("the element is not laid out");
  }
  return {
    ...measured,
    right: measured.x + measured.width,
    bottom: measured.y + measured.height,
    middle: measured.y + measured.height / 2,
  };
}

for (const { width, height } of [
  { width: 1366, height: 768 },
  { width: 911, height: 512 },
] as const) {
  test(`sets the list of the projects in its card, « Créer un projet » filled at the right of its title, above the bar of its table, the table at the width of the card, at ${String(width)} points (US-2130, #3264) [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    // À 150 % d'agrandissement, aucune commande ne devient inatteignable.
    await page.setViewportSize({ width, height });
    await page.goto("/");
    const card = page.getByRole("region", { name: "Liste des projets", exact: true });
    const grid = card.getByRole("grid", { name: "Liste des projets" });
    await expect(grid.getByRole("row")).toHaveCount(4);
    const main = await box(page.getByRole("main"));
    const frame = await box(card);
    const heading = await box(card.getByRole("heading", { level: 2 }));
    const create = card.getByRole("button", { name: "Créer un projet" });
    await expect(create).toBeInViewport({ ratio: 1 });
    // The totals row, in the window: the home is no longer a screen that fills it, and nothing may
    // leave it below its bottom (typescript.md, defect 13). The fake back lists three projects, one
    // page: the pages are not offered, and so not measured here.
    await expect.poll(() => withinBox(grid, grid.getByRole("row").last())).toBe(true);
    const button = await box(create);
    const bar = await box(card.locator("[data-grid-toolbar]"));
    // The table is what its scroller frames: the grid itself is as wide as its columns.
    const table = await box(scroller(grid));
    // The card within the column of the screen; the creation at its right edge, inside its
    // padding, on the line of its title, above the bar of its table.
    expect(frame.x).toBeGreaterThanOrEqual(main.x - 1);
    expect(frame.right).toBeLessThanOrEqual(main.right + 1);
    expect(frame.right - button.right).toBeGreaterThan(0);
    expect(frame.right - button.right).toBeLessThanOrEqual(32);
    expect(button.x).toBeGreaterThan(heading.right);
    expect(Math.abs(button.middle - heading.middle)).toBeLessThanOrEqual(8);
    expect(button.bottom).toBeLessThanOrEqual(bar.y);
    // The table and its bar at the width of the card, inside its padding.
    expect(table.x).toBeGreaterThan(frame.x);
    expect(table.right).toBeLessThan(frame.right);
    expect(frame.width - table.width).toBeLessThanOrEqual(48);
    expect(Math.abs(bar.width - table.width)).toBeLessThanOrEqual(4);
    // Filled: the background of the primary, never the background of the card.
    const background = (element: Locator) =>
      element.evaluate((node) => getComputedStyle(node).backgroundColor);
    expect(await background(create)).not.toBe(await background(card.locator('[data-slot="card"]')));
  });
}

// Against the service alone: the fake back grants one session, which reads the projects. The reader
// of the administration holds no permission of a project; that the list is not read is the unit
// test's, the request being the server's, which the browser does not see (#2915).
test("an account that reads no project lands on a home that says so and leads to the administration, without « Introuvable » [WF-IHM-0120-A] @shared @administration", async ({
  page,
}) => {
  test.skip(!inService, "the fake back grants a session that reads the projects");
  await page.goto("/");
  await expect(
    page.getByRole("heading", { level: 1, name: "Aucun projet à ouvrir" }),
  ).toBeVisible();
  await expect(
    page.getByRole("main").getByRole("link", { name: "Gestion des utilisateurs" }),
  ).toHaveAttribute("href", "/admin/users");
  // No redirection: the home is where the account stays.
  await expect(page).toHaveURL("/");
  await expect(page.getByRole("heading", { name: "Introuvable" })).toHaveCount(0);
});
