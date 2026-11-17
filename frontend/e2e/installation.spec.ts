// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen « Installation » of the administration (FBS-1.6, EP-25 US-2120/L2): reached from the
 * navigation by its link, it shows a card « Installation » with the name of the company, its
 * command outlined at the right of the title of the card, and the currency, the default language
 * and the time zone read only; the form of the name opens, and the focus comes back to its command.
 * The name and its command are no longer on the screen of the cost settings. That the screen is
 * walked entirely by the keyboard and its contrast measured in both modes is proven by
 * `accessibility.spec.ts`, which draws it from the table of the functions.
 */
import { expect, test } from "@playwright/test";

import { WORKING } from "./bounds";
import { compile } from "./compile";
import { untilHydrated } from "./hydration";

test.slow();

test("shows the card of the installation, the name modifiable, the three facts read only", async ({
  page,
}) => {
  await compile(page.request, "/admin/installation");
  await page.goto("/admin/installation");
  await expect(page.getByRole("heading", { level: 1, name: "Installation" })).toBeVisible({
    timeout: WORKING,
  });
  await untilHydrated(page);
  const card = page.getByRole("region", { name: "Installation", exact: true });
  await expect(card).toBeVisible();
  for (const term of ["Nom de l’entreprise", "Devise", "Langue par défaut", "Fuseau horaire"]) {
    await expect(card.getByRole("term").filter({ hasText: term })).toBeVisible();
  }
  const command = card.getByRole("button", { name: "Modifier le nom de l’entreprise" });
  await expect(command).toBeVisible();
  await expect(card.getByRole("button")).toHaveCount(1);
  await command.click();
  const form = page.getByRole("dialog", { name: "Modifier le nom de l’entreprise" });
  await expect(form).toBeVisible();
  await form.getByRole("button", { name: "Annuler" }).click();
  await expect(form).toBeHidden();
  await expect(command).toBeFocused();
});

test("no longer offers the name of the company on the screen of the cost settings", async ({
  page,
}) => {
  await compile(page.request, "/reference/costs");
  await page.goto("/reference/costs");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: WORKING });
  await untilHydrated(page);
  await expect(page.getByRole("button", { name: "Modifier le nom de l’entreprise" })).toHaveCount(
    0,
  );
  await expect(page.getByRole("term").filter({ hasText: "Nom de l’entreprise" })).toHaveCount(0);
});
