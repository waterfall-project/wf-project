// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";
import { withinBox } from "./scroll";

// The fake back serves the first example of each read: the actual costs of the project at 3 June
// 2026 — six lines, five charged to the project alone, one of them excluded, one to its
// sub-project — and the journal of its five imports, whatever the filters, the sort or the page
// asked: the component and page tests prove what the screen asks of each.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const COSTS = `/projects/${PROJECT}/revisions/${REVISION}/actual-costs`;

test("reads the actual costs of a project: the lines and their three totals, the last import, its journal, the sort and the filter asked of the server [WF-CRE-0040-A]", async ({
  page,
}) => {
  // The opening and the dense grid read anew by each click, each in the bound of a grid
  // (`WORKING`): more than the thirty seconds of a test.
  test.slow();
  await openHydrated(page, COSTS);
  await expect(page).toHaveTitle("Coûts réels · Modernisation du poste de commande — Waterfall");
  const grid = page.getByRole("grid", { name: "Coûts réels" });
  for (const name of [
    "N° de pièce",
    "Date de pièce",
    "Montant",
    "Sous-projet",
    "Périmètre suivi",
  ]) {
    await expect(grid.getByRole("columnheader", { name })).toBeVisible();
  }
  await expect(grid.getByRole("row", { name: /FA-2026-0295/ })).toContainText("Exclue");
  await expect(grid.getByRole("row", { name: /AV-2026-0388/ })).toContainText("-200,00");
  // The grid holds in the window: its totals, the general total the server gives, are in view.
  const total = grid.getByRole("row").last();
  await expect(total).toHaveText(/^Total général des lignes retenues\s*106\s050,00$/);
  expect(await withinBox(grid, total)).toBe(true);
  const totals = page.getByRole("region", { name: "Totaux des lignes retenues" });
  await expect(totals).toHaveText(
    /Périmètre suivi\s*105\s400,00\s*Exclu du périmètre suivi\s*650,00\s*Total général\s*106\s050,00\s*Dernier import\s*3 juin 2026/,
  );
  await expect(page.getByRole("region", { name: "Journal des imports" })).toHaveCount(1);
  await expect(
    page.getByRole("table", { name: "Journal des imports" }).getByRole("row"),
  ).toHaveCount(6);

  // The sort by amount, and the filter on the excluded lines, asked of the server by the address.
  await grid.getByRole("columnheader", { name: "Montant" }).getByRole("button").click();
  await expect(page).toHaveURL(`${COSTS}?sort_by=amount&sort_order=asc`, { timeout: WORKING });
  const scope = page.getByRole("group", { name: "Périmètre" });
  await scope.getByRole("button", { name: "Exclues" }).click();
  await expect(page).toHaveURL(`${COSTS}?sort_by=amount&sort_order=asc&in_tracked_scope=false`, {
    timeout: WORKING,
  });
  await expect(scope.getByRole("button", { name: "Exclues" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  // A period applied: the form stays once the address arrives, and the focus on its button (#537).
  const period = page.getByRole("form", { name: "Période des pièces" });
  await period.getByLabel("Pièces du").fill("2026-04-01");
  const apply = period.getByRole("button", { name: "Filtrer" });
  await apply.click();
  await expect(page).toHaveURL(
    `${COSTS}?sort_by=amount&sort_order=asc&in_tracked_scope=false&from=2026-04-01`,
    { timeout: WORKING },
  );
  await expect(apply).toBeFocused();
});

test("shows a line from the list to exclude it from the tracked scope with a reason, the page read anew once the server has written it (#291) [WF-CRE-0040-A]", async ({
  page,
}) => {
  test.slow();
  await openHydrated(page, COSTS);
  const grid = page.getByRole("grid", { name: "Coûts réels" });
  await grid.getByRole("link", { name: "FA-2026-0412" }).click();
  await expect(page).toHaveURL(`${COSTS}?line=01926f3a-7c00-7000-8000-000000000c01`, {
    timeout: WORKING,
  });
  const line = page.getByRole("region", { name: "Ligne FA-2026-0412" });
  await expect(line).toContainText("Suivie");
  await line.getByLabel("Motif de l’exclusion").fill("Câbles d'un autre projet, à réimputer");
  // The server action leaves before the click returns: its answer, and the page read anew, follow.
  const written = page.waitForResponse(
    (response) => response.request().method() === "POST" && response.url().includes(COSTS),
    { timeout: WORKING },
  );
  const command = line.getByRole("button", { name: "Exclure du périmètre suivi" });
  await command.click();
  expect((await written).ok()).toBe(true);
  await expect(command).toHaveAttribute("aria-busy", "false", { timeout: WORKING });
  await expect(line.getByRole("alert")).toHaveCount(0);
  // The excluded line offers its reinstatement, its reason said.
  await grid.getByRole("link", { name: "FA-2026-0295" }).click();
  const reception = page.getByRole("region", { name: "Ligne FA-2026-0295" });
  await expect(reception).toContainText(
    "Exclue du périmètre suivi : Réception du client, non budgétée",
    {
      timeout: WORKING,
    },
  );
  await expect(
    reception.getByRole("button", { name: "Réintégrer dans le périmètre suivi" }),
  ).toBeVisible();
});
