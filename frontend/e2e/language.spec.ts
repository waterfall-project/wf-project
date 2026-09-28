// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

// The account of the fake back follows the browser (`language: default`), and the
// installation defaults to French: the browser alone decides the language of these paths.

test.describe("a browser asking for English", () => {
  test.use({ locale: "en-US" });

  test("gets the interface in English at its first connection [WF-INTF-0160-A]", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("combobox", { name: "Language" })).toHaveValue("default");
    await expect(page.getByRole("option", { name: "Browser language" })).toBeAttached();
  });
});

test.describe("a browser asking for French", () => {
  test.use({ locale: "fr-FR" });

  test("gets the interface in French [WF-INTF-0160-A]", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "fr");
    await expect(page.getByRole("combobox", { name: "Langue" })).toHaveValue("default");
  });
});

test.describe("a browser asking for a language not offered", () => {
  test.use({ locale: "de-DE" });

  test("gets the default language of the installation [WF-INTF-0160-A]", async ({ page }) => {
    await page.goto("/projects");
    await expect(page.locator("html")).toHaveAttribute("lang", "fr");
    await expect(page.getByRole("combobox", { name: "Langue" })).toBeVisible();
  });
});
