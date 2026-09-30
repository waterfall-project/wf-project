// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

// The fake back serves the first example of each operation: the two projects of the witness,
// which it lists whatever the filter asks — the filter is the server's to apply.

test("the home lists the projects the user contributes to, a filter shown and lifted, never a restriction of reading", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projets");
  const filter = page.getByRole("main").getByRole("region", { name: "Filtre de la liste" });
  await expect(filter).toContainText("Projets dont vous êtes contributeur");

  await filter.getByRole("link", { name: "Voir tous les projets" }).click();
  await expect(page).toHaveURL("/?is_contributor=false");
  await expect(filter.getByRole("link", { name: "N’afficher que mes projets" })).toBeVisible();
  const list = page.getByRole("table", { name: "Liste des projets" });
  await expect(list.getByRole("row")).toHaveCount(3);
  await expect(
    list.getByRole("link", { name: "Modernisation du poste de commande" }),
  ).toBeVisible();

  await filter.getByRole("link", { name: "N’afficher que mes projets" }).click();
  await expect(page).toHaveURL("/");
  await expect(filter).toContainText("Projets dont vous êtes contributeur");
});
