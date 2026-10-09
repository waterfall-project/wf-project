// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { axeViolations } from "./axe";
import { compile } from "./compile";
import { openMenu, setExpanded, sortUntilAddress, WORKING } from "./hydration";
import { withinBox } from "./scroll";

// The fake back serves the first example of each read: the session, whose role grants the whole
// catalogue — the consultation of the journal included —, the journal of the installation on
// 3 June 2026, thirty-six inscriptions, whatever the filters, the search, the sort or the page asked,
// the authors and the projects the journal names, and the projects of the witness: the page and
// component tests prove what the screen asks of each, and that a session without the consultation
// finds it not found.
const JOURNAL = "/admin/audit-log";
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
/** The risks of the revision in progress, where the risk 752 occurred, its detail open. */
const RISK = `/projects/${PROJECT}/revisions/01926f3a-7c00-7000-8000-000000000102/risks?risk=01926f3a-7c00-7000-8000-000000000752`;

test("reaches the journal of audit from the navigation of the administration, and reads it on a grid that holds in the window", async ({
  page,
}) => {
  await compile(page.request, JOURNAL, `/projects/${PROJECT}`, RISK);
  await page.goto("/admin/users");
  const nav = page.getByRole("navigation", { name: "Fonctions" });
  await setExpanded(nav.getByRole("button", { name: "Administration", exact: true }), true);
  await nav.getByRole("link", { name: "Journal d’audit" }).click();
  await expect(page).toHaveURL(JOURNAL, { timeout: WORKING });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Journal d’audit");
  await expect(page).toHaveTitle("Journal d’audit — Waterfall");

  const grid = page.getByRole("grid", { name: "Journal d’audit" });
  await expect(
    grid.getByRole("row", {
      name: /Camille Martin Survenance d’un risque Risque Retard de livraison des armoires/,
    }),
  ).toContainText("PRJ-001 · Modernisation du poste de commande");
  // Each date in the local time of the workstation, once the browser has written it.
  await expect(grid.getByRole("row").nth(1).locator("time")).not.toBeEmpty();
  // The totals, how many the server retained, in view: their cells stick to the foot of the grid.
  await expect(grid.getByRole("row").last()).toHaveText("36 inscriptions");
  const totals = grid.getByRole("gridcell", { name: "36 inscriptions" });
  await expect.poll(() => withinBox(grid, totals)).toBe(true);
  // Nothing modifies nor deletes an inscription: no command (WF-SEC-0030).
  await expect(
    page.getByRole("main").getByRole("button", { name: /Supprimer|Modifier/ }),
  ).toHaveCount(0);
  expect(await axeViolations(page, "main")).toEqual([]);

  // The project of an inscription, which the session may open, leads to it.
  await grid
    .getByRole("row", { name: /Retard de livraison des armoires/ })
    .getByRole("link", { name: "PRJ-001 · Modernisation du poste de commande" })
    .click();
  await expect(page).toHaveURL(`/projects/${PROJECT}`, { timeout: WORKING });

  // The risk, which lives in a revision, leads to the risks of the one the inscription names.
  await page.goBack();
  await grid.getByRole("link", { name: "Retard de livraison des armoires", exact: true }).click();
  await expect(page).toHaveURL(RISK, { timeout: WORKING });
});

test("sorts the journal on its columns both ways and filters it by the server, under the names of the contract, back to its first page [WF-IHM-0060-A]", async ({
  page,
}) => {
  test.slow();
  await page.goto(`${JOURNAL}?offset=10`);
  const grid = page.getByRole("grid", { name: "Journal d’audit" });
  const date = grid.getByRole("columnheader", { name: /^Date/ });
  await expect(date).toHaveAttribute("aria-sort", "descending");
  // The newest first unless asked: the header asks the oldest first, then the newest again.
  await sortUntilAddress(date, grid, `${JOURNAL}?sort_by=occurred_at&sort_order=asc`);
  await date.getByRole("button").click();
  await expect(page).toHaveURL(`${JOURNAL}?sort_by=occurred_at&sort_order=desc`, {
    timeout: WORKING,
  });
  await expect(date).toHaveAttribute("aria-sort", "descending");
  // The author, sorted by the server: the header asks it ascending, the date header then unsorted.
  await grid
    .getByRole("columnheader", { name: /^Auteur/ })
    .getByRole("button")
    .click();
  await expect(page).toHaveURL(`${JOURNAL}?sort_by=actor&sort_order=asc`, { timeout: WORKING });
  await expect(date).not.toHaveAttribute("aria-sort", "descending");
  // The date, from another sort, asks the most recent first, as the server gives them unasked.
  await date.getByRole("button").click();
  await expect(page).toHaveURL(`${JOURNAL}?sort_by=occurred_at&sort_order=desc`, {
    timeout: WORKING,
  });

  // The platform alone, then the backups, in a menu of the actions.
  await page
    .getByRole("group", { name: "Filtrer par nature d’auteur" })
    .getByRole("button", { name: "La plateforme" })
    .click();
  await expect(page).toHaveURL(
    `${JOURNAL}?sort_by=occurred_at&sort_order=desc&actor_kind=platform`,
    {
      timeout: WORKING,
    },
  );
  const menu = page.getByRole("menu");
  await openMenu(page.getByRole("button", { name: /^Filtrer par action/ }), menu);
  await menu.getByRole("menuitemcheckbox", { name: "Sauvegarde" }).click();
  await expect(page).toHaveURL(
    `${JOURNAL}?sort_by=occurred_at&sort_order=desc&actor_kind=platform&actions=backup`,
    { timeout: WORKING },
  );
  await page.keyboard.press("Escape");
  await page.getByRole("combobox", { name: "Projet" }).selectOption(PROJECT);
  await expect(page).toHaveURL(new RegExp(`actions=backup&project_id=${PROJECT}$`), {
    timeout: WORKING,
  });

  // The history of an object: its whole history, the other filters lifted, its sort kept; named,
  // and lifted in turn.
  await grid
    .getByRole("link", { name: "Histoire de «\u00a0Retard de livraison des armoires\u00a0»" })
    .click();
  await expect(page).toHaveURL(
    `${JOURNAL}?sort_by=occurred_at&sort_order=desc&object_kind=risk&object_id=01926f3a-7c00-7000-8000-000000000752`,
    { timeout: WORKING },
  );
  await expect(page.getByText("Objet\u00a0: Retard de livraison des armoires")).toBeVisible();
  await page
    .getByRole("link", {
      name: "Lever le filtre sur «\u00a0Retard de livraison des armoires\u00a0»",
    })
    .click();
  await expect(page).toHaveURL(`${JOURNAL}?sort_by=occurred_at&sort_order=desc&object_kind=risk`, {
    timeout: WORKING,
  });
  await expect(page.getByRole("combobox", { name: "Nature de l’objet" })).toBeFocused();

  // The inscriptions of one request: the merge of the amendment, every other filter lifted.
  const merge = "01926f3a-7c00-7000-8000-000800000018";
  await grid
    .getByRole("link", { name: `Les inscriptions de la corrélation ${merge}` })
    .first()
    .click();
  await expect(page).toHaveURL(
    `${JOURNAL}?sort_by=occurred_at&sort_order=desc&correlation_id=${merge}`,
    { timeout: WORKING },
  );
  await expect(page.getByRole("searchbox", { name: "Corrélation" })).toHaveValue(merge);
});
