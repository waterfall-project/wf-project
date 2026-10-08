// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

import { axeViolations } from "./axe";

// The account of the fake back follows the workstation (`theme: default`): the mode the
// browser asks for alone decides the colours of the charter, and the variant of the logo.

/** The background the page is painted in, and the variant of the logo shown. */
async function shown(page: Page) {
  const background = await page
    .locator("body")
    .evaluate((body) => getComputedStyle(body).backgroundColor);
  const logo = await page
    .getByRole("img", { name: "Waterfall" })
    .evaluate((image: HTMLImageElement) => new URL(image.currentSrc).pathname);
  return { background, logo };
}

test.describe("a workstation in dark mode", () => {
  test.use({ colorScheme: "dark" });

  test("gets the dark tokens of the charter and the dark logo", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).not.toHaveAttribute("data-theme");
    expect(await shown(page)).toEqual({
      background: "rgb(10, 10, 10)",
      logo: "/waterfall_logo-dark.svg",
    });
  });

  test("is painted light when the account forces the light mode", async ({ page }) => {
    await page.goto("/");
    // The attribute the root layout sets for an account that chose `light`: the fake back
    // serves an account that follows the workstation, so it is set here as the layout would.
    await page.locator("html").evaluate((html) => {
      html.setAttribute("data-theme", "light");
    });
    await expect(page.locator("body")).toHaveCSS("background-color", "rgb(255, 255, 255)");
  });
});

test.describe("a workstation in light mode", () => {
  test.use({ colorScheme: "light" });

  test("gets the light tokens of the charter and the light logo", async ({ page }) => {
    await page.goto("/");
    expect(await shown(page)).toEqual({
      background: "rgb(255, 255, 255)",
      logo: "/waterfall_logo.svg",
    });
  });

  test("is painted dark when the account forces the dark mode", async ({ page }) => {
    await page.goto("/");
    await page.locator("html").evaluate((html) => {
      html.setAttribute("data-theme", "dark");
    });
    await expect(page.locator("body")).toHaveCSS("background-color", "rgb(10, 10, 10)");
  });
});

/** The background a cell is painted on. */
function backgroundOf(cell: Locator): Promise<string> {
  return cell.evaluate((element) => getComputedStyle(element).backgroundColor);
}

// The access roles set a dense grid and a list one above the other: the grid of the roles, and the
// matrix of the permissions (#508) — the settings of costs, which set them side by side before, hold
// dense grids alone since EP-02/L42a.
for (const mode of ["light", "dark"] as const) {
  test.describe(`the tables of a workstation in ${mode} mode`, () => {
    test.use({ colorScheme: mode });

    test("sets the header row of a list and of a dense grid on the same muted background, its text legible [WF-IHM-0100-A]", async ({
      page,
    }) => {
      await page.goto("/admin/access-roles");
      const list = page.getByRole("table", { name: "Permissions par fonction" });
      const grid = page.getByRole("grid", { name: "Rôles d’habilitation" });
      const listHeader = list.getByRole("columnheader").first();
      const gridHeader = grid.getByRole("columnheader", { name: "Comptes porteurs" });
      await expect(gridHeader).toBeVisible();
      const header = await backgroundOf(listHeader);
      expect(await backgroundOf(gridHeader)).toBe(header);
      // A colour of its own, neither transparent nor that of the page the rows of the list show.
      expect(header).not.toBe("rgba(0, 0, 0, 0)");
      expect(header).not.toBe(await backgroundOf(page.locator("body")));
      // Un contrôle automatisé de contraste ne relève aucun écart au niveau AA: in the head of
      // every table of the screen.
      expect(await axeViolations(page, "thead")).toEqual([]);
    });
  });
}
