// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the settings of the resources (`/reference/resources`): the roles, the tree of the
 * organisation, the calendars and the units of duration, against the fake back.
 */
import { expect, test } from "@playwright/test";

import { sortUntilAddress, WORKING } from "./hydration";
import { rowAt } from "./scroll";
import { isServerAction } from "./server-action";

/** The automation engineer, the deactivated role of the witness. */
const AUTOMATION = "01926f3a-7c00-7000-8000-000000000453";

// The fake back serves the first example of each read of the reference data — the grid of the
// volumes, a hundred and fifty categories of labour over fifteen years, the natures, the
// organisation, the roles and the calendars of the witness —, and the first example of
// `setHourlyRate` whatever was written: the first rate of 2015 of the mechanical engineering of
// level 1, the third row of the grid, which has none before 2016. What the screens ask of each is
// proven by the tests of the pages and of the grid.

test("sorts and searches each list of the settings of the resources by the server, folds the tree, and shows and reactivates the deactivated objects [WF-IHM-0060-A] [WF-REF-0150-A]", async ({
  page,
}) => {
  test.slow();
  await page.goto("/reference/resources");
  const roles = page.getByRole("grid", { name: "Rôles de ressources" });
  // A header of the roles asks the server for its sort, under the names of the grid: the code of
  // a role among them (EP-14/L42r).
  await sortUntilAddress(
    roles.getByRole("columnheader", { name: "Code", exact: true }),
    roles,
    "/reference/resources?role_sort_by=code&role_sort_order=asc",
  );
  // The tree sorts nothing, folds and unfolds, and its search keeps the sort of the roles.
  const tree = page.getByRole("treegrid", { name: "Arbre d’organisation" });
  await expect(tree.locator("thead button")).toHaveCount(0);
  const direction = tree.getByRole("row", { name: /Direction technique/ });
  await direction.getByRole("button", { name: "Plier" }).click();
  await expect(tree.getByRole("row")).toHaveCount(3);
  await direction.getByRole("button", { name: "Déplier" }).click();
  await expect(tree.getByRole("row")).toHaveCount(6);
  await page
    .getByRole("searchbox", { name: "Rechercher dans «\u00a0Arbre d’organisation\u00a0»" })
    .fill("BE");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/role_sort_by=code.*&org_search=BE$/, { timeout: WORKING });

  // The deactivated objects asked of the server, each offered to be reactivated.
  await page.getByRole("link", { name: "Afficher aussi les désactivés" }).click();
  await expect(page).toHaveURL(/include_inactive=true/, { timeout: WORKING });
  await expect(page.getByRole("link", { name: "Masquer les désactivés" })).toBeVisible();
  // The reactivation is a server action, which carries the role: its answer awaited, from before
  // the click.
  const reactivated = page.waitForResponse(
    (response) =>
      isServerAction(response.request()) &&
      (response.request().postData() ?? "").includes(AUTOMATION),
  );
  await roles.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" }).click();
  expect((await reactivated).status()).toBe(200);
  // The row shows what the server answers: active again, offering its deactivation (EP-02/L43b).
  await expect(
    roles.getByRole("button", { name: "Désactiver «\u00a0Automaticien\u00a0»" }),
  ).toBeVisible({ timeout: WORKING });
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);

  // The programmer of automata, under a node deactivated: its reactivation is unavailable, named
  // by its condition, and a press says it without asking anything (WF-REF-0080, WF-IHM-0090).
  const programmer = roles.getByRole("button", {
    name: "Réactiver «\u00a0Programmeur d'automates\u00a0»",
  });
  await expect(programmer).toHaveAttribute("aria-disabled", "true");
  await expect(programmer).toHaveAccessibleDescription(
    "Condition non remplie : nœud d’organisation actif.",
  );
  // Playwright clicks no button marked unavailable: the press is dispatched as a pointer would.
  await programmer.dispatchEvent("click");
  await expect(
    page
      .getByRole("region", { name: "Rôles de ressources" })
      .getByRole("status")
      .filter({ hasText: "indisponible" }),
  ).toHaveText(
    "La réactivation de «\u00a0Programmeur d'automates\u00a0» est indisponible. Condition non remplie\u00a0: nœud d’organisation actif.",
  );
});

test("creates a role in its form, moves a node under an active one, and designates the default calendar as its row lists it, the mock-up saying the fake back keeps nothing (EP-02/L43b, EP-14/L43g)", async ({
  page,
}) => {
  test.slow();
  await page.goto("/reference/resources");
  await expect(page.getByRole("note")).toContainText("le service simulé ne conserve");

  // A role created in its form. No project is opened here, nothing witnesses the hydration: the
  // creation is pressed again until React opens its form, and never once it is open.
  const roles = page.getByRole("region", { name: "Rôles de ressources" });
  const form = page.getByRole("dialog", { name: "Nouveau rôle de ressource" });
  await expect(async () => {
    if (!(await form.isVisible())) {
      await roles.getByRole("button", { name: "Nouveau rôle" }).click();
    }
    await expect(form).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  await form.getByRole("textbox", { name: "Code" }).fill("DESS-ELEC");
  await form.getByRole("textbox", { name: "Libellé" }).fill("Dessinateur électricien");
  // The active nodes alone, in the order of the tree; the categories of labour alone.
  await form
    .getByRole("combobox", { name: "Nœud d’organisation" })
    .selectOption({ label: "\u2003BE-ELEC · Bureau d'études électricité" });
  await form
    .getByRole("combobox", { name: "Catégorie de coût" })
    .selectOption({ label: "MO-001 · Ingénierie électrique" });
  await expect(
    form.getByRole("combobox", { name: "Catégorie de coût" }).getByRole("option", {
      name: "ACH-001 · Sous-traitance",
    }),
  ).toHaveCount(0);
  await form
    .getByRole("combobox", { name: "Calendrier" })
    .selectOption({ label: "Semaine standard" });
  await form.getByRole("textbox", { name: "Heures par mois" }).fill("520");
  await form.getByRole("textbox", { name: "Effectif" }).fill("3");
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(form).toBeHidden({ timeout: WORKING });
  // The list says what the server created — its example —, and adds no row of its own.
  await expect(roles.getByRole("status").filter({ hasText: "créé" })).toHaveText(
    "«\u00a0Dessinateur électricien\u00a0» créé.",
  );

  // The workshop moved under the direction in its form: the active nodes alone are offered as its
  // parent, never the workshop itself; the parent is sent, and the list says what the server wrote.
  const organisation = page.getByRole("region", { name: "Arbre d’organisation" });
  const nodeForm = page.getByRole("dialog", { name: "Modifier «\u00a0Atelier de câblage\u00a0»" });
  await page
    .getByRole("treegrid", { name: "Arbre d’organisation" })
    .getByRole("button", { name: "Modifier «\u00a0Atelier de câblage\u00a0»" })
    .click();
  const parent = nodeForm.getByRole("combobox", { name: "Parent" });
  await expect(parent.getByRole("option")).toHaveText([
    "Aucun — racine",
    "DT · Direction technique",
    "\u2003BE-ELEC · Bureau d'études électricité",
    "\u2003ACHATS · Service des achats",
  ]);
  await parent.selectOption({ label: "DT · Direction technique" });
  await nodeForm.getByRole("button", { name: "Enregistrer" }).click();
  await expect(nodeForm).toBeHidden({ timeout: WORKING });
  await expect(organisation.getByRole("status").filter({ hasText: "enregistré" })).toHaveText(
    "«\u00a0Atelier de câblage\u00a0» enregistré.",
  );

  // The four-day week designated by default from its row, as it lists the command: the row shows
  // what the server answers.
  const calendars = page.getByRole("grid", { name: "Calendriers" });
  await calendars
    .getByRole("button", { name: "Désigner «\u00a0Semaine de quatre jours\u00a0» par défaut" })
    .click();
  await expect(rowAt(calendars, 1)).toContainText("Calendrier par défaut", { timeout: WORKING });
  await expect(
    page
      .getByRole("region", { name: "Calendriers" })
      .getByRole("status")
      .filter({ hasText: "désigné" }),
  ).toHaveText("«\u00a0Semaine de quatre jours\u00a0» désigné calendrier par défaut.");
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("modifies the units of duration from the settings of the resources, and says what the change does to the schedules (US-0570)", async ({
  page,
}) => {
  test.slow();
  await page.goto("/reference/resources");
  const section = page.getByRole("region", { name: "Unités de durée" });
  const value = (name: string) =>
    section.getByText(name, { exact: true }).locator("xpath=following-sibling::dd");
  await expect(value("Heures par jour")).toHaveText("8");
  const form = page.getByRole("dialog", { name: "Modifier les unités de durée" });
  // No project is opened here, nothing witnesses the hydration: the command is pressed again until
  // React opens its form, and never once it is open.
  await expect(async () => {
    if (!(await form.isVisible())) {
      await section.getByRole("button", { name: "Modifier les unités de durée" }).click();
    }
    await expect(form).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  await expect(form).toContainText(
    "les plannings des révisions en cours sont recalculés ; une révision marquée garde les heures qu’elle a calculées.",
  );
  await form.getByRole("textbox", { name: "Heures par jour" }).fill("7");
  await form.getByRole("button", { name: "Enregistrer" }).click();
  await expect(form).toBeHidden({ timeout: WORKING });
  // The fake back answers the first example of the operation whatever was written: 7 and 35.
  await expect(value("Heures par semaine")).toHaveText("35");
  await expect(page.getByRole("status").filter({ hasText: "enregistrées" })).toHaveText(
    "Unités de durée enregistrées.",
  );
  await expect(section.getByRole("button", { name: "Modifier les unités de durée" })).toBeFocused();
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});
