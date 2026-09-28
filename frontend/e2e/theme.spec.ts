// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

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
