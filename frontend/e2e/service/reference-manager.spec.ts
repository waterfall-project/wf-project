// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The uses of the manager against the service (US-0900, #2044): the settings of the reference data
 * carried to their end from their five screens by an account that holds the predefined role
 * « Manager », and the roles composed to measure that cumulate or withhold permissions.
 *
 * - Of WF-INTF-0020-A, its sentence on the settings of FBS-3.1 to FBS-3.4: the manager creates or
 *   sets each of the nine objects from its screen — nodes of the organisation, roles of resources,
 *   calendars, natures and categories of cost, hourly rates, the correspondence of the extraction of
 *   the actual costs, the bounds of the risk matrix, the thresholds of the indices and the delay
 *   between two reviews — and reads what it wrote after the page is read anew. The views of the
 *   portfolio and the project the manager is no contributor of are EP-11's.
 * - Of WF-ADM-0020-A, its two sentences: a role composed of `cost_settings.write` and `users.write`
 *   lets one account create a nature of cost and a local account; a role that holds all of the
 *   manager but `resource_settings.write` reads the roles of resources and is refused their creation
 *   (403 `PERMISSION_MISSING`, the permission named).
 *
 * The predefined role holds `risk_settings.write` and `indicator_settings.write` (the back seeds
 * them, #2187): the account of the path holds « Manager » alone, which suffices for the nine objects
 * (WF-INTF-0020-A). The accounts are the paths' own; what a path writes is deactivated at its end
 * (the correspondence and the rate are written the same on each run), for the lists to stay short on
 * an installation that is played again. The role made to measure, which holds the reads too, is the
 * matter of #2188. The first path reads and rewrites singletons the `@shared` paths write
 * too: it is tagged `@realm-wide`, to play alone once they are done.
 */
import { randomBytes } from "node:crypto";

import { expect, type Locator, type Page, test } from "@playwright/test";

import { openFilters } from "../check-menu";
import { compileAnswered } from "../compile";
import { openMenu, WORKING } from "../hydration";
import { isServerAction } from "../server-action";
import type { components } from "../../src/api/generated/schema";
import { heldToTheContract } from "./contract";
import {
  accountAdministrator,
  ADMINISTRATOR,
  API,
  frontToken,
  localAccount,
  signIn,
  withdrawRoles,
} from "./realm";

type Schemas = components["schemas"];

heldToTheContract();

const ACCOUNT = "/account";
const COSTS = "/reference/costs?sort_by=code&sort_order=asc";
const MAPPING = "/reference/costs/actual-cost-mapping";
const RESOURCES = "/reference/resources";
const RISKS = "/reference/risks";
const INDICATORS = "/reference/indicators";
const USERS = "/admin/users";
/** The role of the cumulation: costs and accounts, read to be shown and written to be changed. */
const CUMULATION = "Paramètres de coûts et comptes (parcours)";
/** The role of the reciprocal: all of « Manager » but `resource_settings.write`. */
const DEPRIVED = "Manager sans paramètres de ressources (parcours)";

/** The objects of the witness the path of the refusal asks for by their identifiers. */
const WITNESS = {
  node: "01926f3a-7c00-7000-8000-000000000471",
  category: "01926f3a-7c00-7000-8000-000000000402",
  calendar: "01926f3a-7c00-7000-8000-000000000481",
} as const;

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT, COSTS, MAPPING, RESOURCES, RISKS);
  await compileAnswered(request, INDICATORS, USERS);
});

/** A label between the quotes of the screens. */
function quoted(label: string): string {
  return `«\u00a0${label}\u00a0»`;
}

/**
 * Open the form of a command on a page that may not be hydrated yet, nothing witnessing it (défaut
 * n° 19): the command is pressed again until React opens the form, and never once it is open.
 */
async function openForm(command: Locator, form: Locator): Promise<void> {
  await expect(async () => {
    if (!(await form.isVisible())) {
      await command.click({ timeout: 1_000 });
    }
    await expect(form).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
}

/** Choose the option of a list that holds a text, by its value: the indentation of a tree is not ours. */
async function choose(list: Locator, text: string): Promise<void> {
  const value = await list.locator("option", { hasText: text }).first().getAttribute("value");
  if (value === null) {
    throw new Error(`no option of the list holds ${text}`);
  }
  await list.selectOption({ value });
}

/**
 * Deactivate an object from its row, on a page read at an address, pressed again until React
 * answers and never once the row offers nothing to deactivate; the answer of the service awaited.
 * A cleanup: told if it fails, never thrown — it would hide the error of the path that brought us
 * here (#963).
 */
async function deactivate(page: Page, address: string, label: string): Promise<void> {
  try {
    await page.goto(address);
    const command = page.getByRole("button", { name: `Désactiver ${quoted(label)}` });
    // The row first: a page read has not always drawn its commands, and a command not seen yet is
    // not a command done — the deactivation would be skipped, and the object left active.
    await expect(command).toBeVisible({ timeout: WORKING });
    // Pressed again only until the page answers (React may not be hydrated yet), and never once an
    // answer came: a deactivation is not asked twice. Both promises are awaited together, so that a
    // click that fails never leaves the wait of the answer to reject unheard.
    await expect(async () => {
      const [answer] = await Promise.all([
        page.waitForResponse((response) => isServerAction(response.request()), { timeout: 3_000 }),
        command.click({ timeout: 1_000 }),
      ]);
      expect(answer.status()).toBe(200);
    }).toPass({ timeout: WORKING });
    // The answer of the action awaited: the row hides at once, and the next page read would abandon
    // the request. A 200 of a server action says the request ended, not that the service kept it.
    await expect(command).toBeHidden({ timeout: WORKING });
  } catch (failure) {
    console.warn(`The deactivation of ${label} failed:`, failure);
  }
}

/** Create a nature of cost of the type of non-labour from its form, and say what the list says. */
async function createNature(
  page: Page,
  code: string,
  label: string,
  willBeMade: () => void,
): Promise<void> {
  const form = page.getByRole("dialog", { name: "Nouvelle nature de coût" });
  const section = page.getByRole("region", { name: "Natures de coût" });
  await openForm(section.getByRole("button", { name: "Nouvelle nature" }), form);
  await form.getByRole("textbox", { name: "Code", exact: true }).fill(code);
  await form.getByRole("textbox", { name: "Libellé" }).fill(label);
  await form.getByRole("combobox", { name: "Type" }).selectOption({ label: "Hors main-d’œuvre" });
  // Said before the click: a failure past it still finds the nature to deactivate.
  willBeMade();
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(form).toBeHidden({ timeout: WORKING });
  await expect(section.getByRole("status").filter({ hasText: "créée" })).toHaveText(
    `${quoted(label)} créée.`,
  );
}

test(
  "a holder of the role « Manager » alone carries the settings of the reference data to their end from their screens — an organisation node, a resource role, a calendar, a nature and a category of cost, an hourly rate, the correspondence of the actual costs, the bounds of the risk matrix, the thresholds and the delay between two reviews — and reads what it wrote [WF-INTF-0020-A]",
  {
    // It reads and rewrites singletons the `@shared` paths write too: played alone, after them.
    tag: "@realm-wide",
  },
  async ({ browser, page, playwright }) => {
    // Nine objects written and read anew, the account made first: a path of one piece.
    test.setTimeout(420_000);
    const stamp = String(Date.now() % 1_000_000);
    const suffix = randomBytes(2).toString("hex");
    const nature = { code: `NE-${stamp}`, label: `Nature ${stamp}` };
    const category = { code: `ESS-${stamp}`, label: `Essais ${stamp}`, accounting: `607${stamp}` };
    const node = { code: `ND-${stamp}`, label: `Pôle ${stamp}` };
    const calendar = `Semaine ${stamp}`;
    const role = { code: `RL-${stamp}`, label: `Rôle ${stamp}` };
    const mapped = `Pos. pièce ${stamp}${suffix}`;
    const COLUMN = "Poste de la pièce";

    const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
    const administrator = await accountAdministrator(browser, calls);
    const manager = await localAccount(browser, administrator);
    const made: string[] = [];
    try {
      await administrator.give(manager.id, "Manager", []);
      await signIn(page, manager, ACCOUNT);

      // The costs: a nature, a category of that nature, and a rate on the grid.
      await page.goto(COSTS);
      await createNature(page, nature.code, nature.label, () => made.push("nature"));
      const categories = page.getByRole("region", { name: "Catégories de coût" });
      const categoryForm = page.getByRole("dialog", { name: "Nouvelle catégorie de coût" });
      await openForm(categories.getByRole("button", { name: "Nouvelle catégorie" }), categoryForm);
      await categoryForm.getByRole("textbox", { name: "Code", exact: true }).fill(category.code);
      await categoryForm.getByRole("textbox", { name: "Libellé" }).fill(category.label);
      await choose(categoryForm.getByRole("combobox", { name: "Nature" }), nature.code);
      await categoryForm.getByRole("textbox", { name: "Code comptable" }).fill(category.accounting);
      await categoryForm.getByRole("button", { name: "Créer" }).click();
      await expect(categoryForm).toBeHidden({ timeout: WORKING });
      await expect(categories.getByRole("status").filter({ hasText: "créée" })).toHaveText(
        `${quoted(category.label)} créée.`,
      );

      // Read anew: the nature in its list, the category under the filter of its nature.
      await page.goto(COSTS);
      const natures = page.getByRole("grid", { name: "Natures de coût" });
      await expect(natures.getByRole("row", { name: new RegExp(nature.code) })).toHaveCount(1, {
        timeout: WORKING,
      });
      await openFilters(page, page.getByRole("region", { name: "Catégories de coût" }));
      const filter = page.getByRole("combobox", { name: "Nature", exact: true });
      await expect(async () => {
        await choose(filter, nature.code);
        await expect(page).toHaveURL(/category_cost_type_id=/, { timeout: 2_000 });
      }).toPass({ timeout: WORKING });
      await expect(
        page
          .getByRole("grid", { name: "Catégories de coût" })
          .getByRole("row", { name: new RegExp(category.code) }),
      ).toHaveCount(1, { timeout: WORKING });

      // A rate on the grid, in a cell the witness leaves empty, the same on each run.
      await page.goto(COSTS);
      const rates = page.getByRole("grid", { name: "Grille des taux horaires" });
      const row = rates
        .getByRole("row")
        .filter({ has: page.getByRole("gridcell", { name: "MO-003" }) });
      // The code, the label, the state, then 2012 to 2015; the cell of 2013
      // is this path's own (the others write 2014 and 2015, which no project orders with this one).
      const rate = row.getByRole("gridcell").nth(4);
      await expect(async () => {
        await row.getByRole("gridcell", { name: "MO-003" }).click();
        for (let step = 0; step < 4; step += 1) {
          await page.keyboard.press("ArrowRight");
        }
        await expect(rate).toBeFocused({ timeout: 1_000 });
      }).toPass({ timeout: WORKING });
      await page.keyboard.type("85");
      await page.keyboard.press("Enter");
      await expect(rate).toHaveText("85,00 €", { timeout: WORKING });
      await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
      await page.reload();
      await expect(
        page
          .getByRole("grid", { name: "Grille des taux horaires" })
          .getByRole("row")
          .filter({ has: page.getByRole("gridcell", { name: "MO-003" }) })
          .getByRole("gridcell")
          .nth(4),
      ).toHaveText("85,00 €", { timeout: WORKING });

      // The correspondence of the extraction: a label entered for an optional column, saved whole.
      await page.goto(MAPPING);
      const labels = page
        .getByRole("group", { name: new RegExp(`^${COLUMN}`) })
        .getByRole("textbox");
      const before = await labels.count();
      await expect(async () => {
        if ((await labels.count()) === before) {
          await page.getByRole("button", { name: `Ajouter un intitulé à « ${COLUMN} »` }).click();
        }
        await expect(labels).toHaveCount(before + 1, { timeout: 1_000 });
      }).toPass({ timeout: WORKING });
      await labels.last().fill(mapped);
      await page.getByRole("button", { name: "Enregistrer la correspondance" }).click();
      await expect(page.getByRole("status").filter({ hasText: "enregistrée" })).toHaveText(
        "Correspondance enregistrée.",
      );
      await page.goto(MAPPING);
      await expect
        .poll(
          () =>
            labels.evaluateAll((fields) =>
              fields.map((field) => (field instanceof HTMLInputElement ? field.value : "")),
            ),
          { timeout: WORKING },
        )
        .toContain(mapped);
      // Left as found: the label removed, the correspondence saved again.
      await page
        .getByRole("group", { name: new RegExp(`^${COLUMN}`) })
        .getByRole("button", { name: /^Retirer l’intitulé/ })
        .last()
        .click();
      await page.getByRole("button", { name: "Enregistrer la correspondance" }).click();
      await expect(page.getByRole("status").filter({ hasText: "enregistrée" })).toHaveText(
        "Correspondance enregistrée.",
      );

      // The resources: a node, a calendar of its own, and a role under the node, on that calendar.
      await page.goto(RESOURCES);
      const organisation = page.getByRole("region", { name: "Arbre d’organisation" });
      const nodeForm = page.getByRole("dialog", { name: "Nouveau nœud d’organisation" });
      await openForm(organisation.getByRole("button", { name: "Nouveau nœud" }), nodeForm);
      await nodeForm.getByRole("textbox", { name: "Code", exact: true }).fill(node.code);
      await nodeForm.getByRole("textbox", { name: "Libellé" }).fill(node.label);
      made.push("node");
      await nodeForm.getByRole("button", { name: "Créer" }).click();
      await expect(nodeForm).toBeHidden({ timeout: WORKING });
      await expect(organisation.getByRole("status").filter({ hasText: "créé" })).toHaveText(
        `${quoted(node.label)} créé.`,
      );

      const calendars = page.getByRole("region", { name: "Calendriers" });
      const calendarForm = page.getByRole("dialog", { name: "Nouveau calendrier" });
      await openForm(calendars.getByRole("button", { name: "Nouveau calendrier" }), calendarForm);
      await calendarForm.getByRole("textbox", { name: "Libellé" }).fill(calendar);
      const days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];
      for (const [index, day] of days.entries()) {
        await calendarForm
          .getByRole("textbox", { name: day, exact: true })
          .fill(index < 5 ? "8" : "0");
      }
      made.push("calendar");
      await calendarForm.getByRole("button", { name: "Créer" }).click();
      await expect(calendarForm).toBeHidden({ timeout: WORKING });
      await expect(calendars.getByRole("status").filter({ hasText: "créé" })).toHaveText(
        `${quoted(calendar)} créé.`,
      );

      const roles = page.getByRole("region", { name: "Rôles de ressources" });
      const roleForm = page.getByRole("dialog", { name: "Nouveau rôle de ressource" });
      await openForm(roles.getByRole("button", { name: "Nouveau rôle" }), roleForm);
      await roleForm.getByRole("textbox", { name: "Code", exact: true }).fill(role.code);
      await roleForm.getByRole("textbox", { name: "Libellé" }).fill(role.label);
      await choose(roleForm.getByRole("combobox", { name: "Nœud d’organisation" }), node.code);
      await choose(roleForm.getByRole("combobox", { name: "Catégorie de coût" }), "MO-001");
      await choose(roleForm.getByRole("combobox", { name: "Calendrier" }), calendar);
      await roleForm.getByRole("textbox", { name: "Heures par mois" }).fill("520");
      await roleForm.getByRole("textbox", { name: "Effectif" }).fill("3");
      made.push("role");
      await roleForm.getByRole("button", { name: "Créer" }).click();
      await expect(roleForm).toBeHidden({ timeout: WORKING });
      await expect(roles.getByRole("status").filter({ hasText: "créé" })).toHaveText(
        `${quoted(role.label)} créé.`,
      );

      // Read anew, each under the search of its code: the service kept the three objects.
      await page.goto(`${RESOURCES}?org_search=${node.code}&role_code=${role.code}`);
      await expect(
        page
          .getByRole("treegrid", { name: "Arbre d’organisation" })
          .getByRole("row", { name: new RegExp(node.code) }),
      ).toHaveCount(1, { timeout: WORKING });
      await expect(
        page
          .getByRole("grid", { name: "Rôles de ressources" })
          .getByRole("row", { name: new RegExp(role.code) }),
      ).toHaveCount(1, { timeout: WORKING });
      await expect(
        page
          .getByRole("grid", { name: "Calendriers" })
          .getByRole("row")
          .filter({ hasText: calendar }),
      ).toHaveCount(1, { timeout: WORKING });

      // The bounds of the risk matrix, the outer ones written too: the same on each run.
      await page.goto(RISKS);
      const matrix = page.getByRole("dialog", { name: "Modifier la matrice de risques" });
      await openForm(page.getByRole("button", { name: "Modifier la matrice de risques" }), matrix);
      const probability = matrix.getByRole("group", { name: "Bornes de probabilité (%)" });
      await probability.getByRole("textbox", { name: "Première borne" }).fill("25");
      await probability.getByRole("textbox", { name: "Deuxième borne" }).fill("55");
      await probability.getByRole("textbox", { name: "Troisième borne" }).fill("75");
      await matrix.getByRole("button", { name: "Enregistrer" }).click();
      await expect(matrix).toBeHidden({ timeout: WORKING });
      await expect(page.getByRole("status").filter({ hasText: "enregistrée" })).toHaveText(
        "Matrice de risques enregistrée.",
      );
      await page.goto(RISKS);
      await expect(
        page
          .getByRole("table", { name: "Bornes de la matrice de risques" })
          .getByRole("row", { name: "Probabilité 25 % 55 % 75 %" }),
      ).toHaveCount(1, { timeout: WORKING });

      // The thresholds of the indices and the delay between two reviews.
      await page.goto(INDICATORS);
      const thresholds = page.getByRole("dialog", { name: "Modifier les seuils et le délai" });
      await openForm(
        page.getByRole("button", { name: "Modifier les seuils et le délai" }),
        thresholds,
      );
      for (const index of ["Indice de coût", "Indice de délai"]) {
        const group = thresholds.getByRole("group", { name: index });
        await group.getByRole("textbox", { name: "Seuil de vigilance" }).fill("0,95");
        await group.getByRole("textbox", { name: "Seuil d’alerte" }).fill("0,85");
      }
      await thresholds
        .getByRole("textbox", { name: "Délai maximal entre deux révisions marquées (semaines)" })
        .fill("6");
      await thresholds.getByRole("button", { name: "Enregistrer" }).click();
      await expect(thresholds).toBeHidden({ timeout: WORKING });
      await expect(page.getByRole("status").filter({ hasText: "enregistrés" })).toHaveText(
        "Seuils et délai enregistrés.",
      );
      await page.goto(INDICATORS);
      await expect(
        page
          .getByRole("table", { name: "Seuils d’alerte des indices" })
          .getByRole("row", { name: "Indice de coût 0,95 0,85" }),
      ).toHaveCount(1, { timeout: WORKING });
      await expect(page.getByText("6 semaines")).toBeVisible();
      await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
    } finally {
      // What the path made is deactivated: the role, the calendar and the node, then the nature,
      // whose cascade takes the category with it (WF-REF-0010-A). The role first: an object that a
      // role holds is not deactivated, and the cascade of a node would take the role with it.
      if (made.includes("role")) {
        await deactivate(page, `${RESOURCES}?role_code=${role.code}`, role.label);
      }
      if (made.includes("calendar")) {
        await deactivate(page, RESOURCES, calendar);
      }
      if (made.includes("node")) {
        await deactivate(page, `${RESOURCES}?org_search=${node.code}`, node.label);
      }
      // The category is not deactivated by itself: the list of the categories is paged, and the
      // nature takes it with it. The natures are paged too: found under the search of its code.
      if (made.includes("nature")) {
        await deactivate(page, `${COSTS}?type_search=${nature.code}`, nature.label);
      }
      try {
        withdrawRoles(manager.email);
      } catch (failure) {
        console.error("The cleanup of the manager path failed:", failure);
      }
      await calls.dispose();
    }
  },
);

test("a role composed of the modification of the costs and of the users, and of their reading, lets one account create a nature of cost and a local account [WF-ADM-0020-A]", async ({
  browser,
  page,
  playwright,
}) => {
  // The account made, its role composed, a nature and an account created and read anew.
  test.setTimeout(240_000);
  const stamp = String(Date.now() % 1_000_000);
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const administrator = await accountAdministrator(browser, calls);
  const holder = await localAccount(browser, administrator);
  const nature = { code: `NC-${stamp}`, label: `Nature cumulée ${stamp}` };
  const lastName = `Cumul ${stamp}`;
  const email = `cumul.${stamp}.${randomBytes(2).toString("hex")}@waterfall.test`;
  const natureMade: string[] = [];
  let given = false;
  try {
    // Set before the call: a role made, then a failure, is still cleaned up. The reads are given
    // beside the writes: a modification does not read, and the screens read what they show.
    given = true;
    await administrator.give(holder.id, CUMULATION, [
      "cost_settings.read",
      "cost_settings.write",
      "users.read",
      "users.write",
    ]);
    await signIn(page, holder, ACCOUNT);

    // A nature of cost, from the screen of the costs, read anew.
    await page.goto(COSTS);
    await createNature(page, nature.code, nature.label, () => natureMade.push("nature"));
    await page.goto(COSTS);
    await expect(
      page
        .getByRole("grid", { name: "Natures de coût" })
        .getByRole("row", { name: new RegExp(nature.code) }),
    ).toHaveCount(1, { timeout: WORKING });

    // A local account, from the screen of the accounts, found by its name.
    await page.goto(`${USERS}?search=`);
    const told = page.getByRole("status", { name: "Commandes des comptes" });
    const accounts = page.getByRole("grid", { name: "Comptes utilisateurs" });
    await expect(accounts.getByRole("row").last()).toHaveText(/^[\d\s]+ comptes?$/, {
      timeout: WORKING,
    });
    const creation = page.getByRole("form", { name: "Créer un compte local" });
    await openMenu(page.getByRole("button", { name: "Créer un compte local" }), creation);
    await creation.getByLabel("Nom", { exact: true }).fill(lastName);
    await creation.getByLabel("Prénom", { exact: true }).fill("Léa");
    await creation.getByLabel("Adresse électronique").fill(email);
    await creation.getByRole("button", { name: "Créer", exact: true }).click();
    await expect(told).toHaveText(new RegExp(`^Compte ${quoted(`Léa ${lastName}`)} créé`), {
      timeout: WORKING,
    });
    await page.goto(`${USERS}?search=${encodeURIComponent(email)}`);
    await expect(accounts.getByRole("row").last()).toHaveText("1 compte", { timeout: WORKING });
  } finally {
    if (natureMade.length > 0) {
      await deactivate(page, COSTS, nature.label);
    }
    try {
      withdrawRoles(holder.email);
      if (given) {
        await administrator.remove(CUMULATION);
      }
    } catch (failure) {
      console.error("The cleanup of the cumulation path failed:", failure);
    }
    await calls.dispose();
  }
});

test("a role that holds all of « Manager » but the modification of the resource settings reads the roles of resources and is refused their creation by 403 PERMISSION_MISSING naming the permission, the screen offering no command to create one [WF-ADM-0020-A]", async ({
  browser,
  page,
  playwright,
}) => {
  // The account made, its role composed, the screen read and the API asked.
  test.setTimeout(240_000);
  const stamp = String(Date.now() % 1_000_000);
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const administrator = await accountAdministrator(browser, calls);
  const holder = await localAccount(browser, administrator);
  let given = false;
  try {
    // All of the permissions of the predefined role of the installation but one.
    const reading = await calls.get(`${API}/access-roles?search=Manager`, {
      headers: { Authorization: `Bearer ${await frontToken(browser, ADMINISTRATOR)}` },
    });
    expect(reading.status(), "GET /access-roles").toBe(200);
    const predefined = ((await reading.json()) as Schemas["AccessRole"][]).find(
      (one) => one.label === "Manager",
    );
    expect(predefined, "the predefined role « Manager »").toBeDefined();
    const kept = (predefined?.permissions ?? []).filter(
      (permission) => permission !== "resource_settings.write",
    );
    expect(kept, "the permissions of « Manager » but one").toContain("resource_settings.read");
    expect(kept).toHaveLength((predefined?.permissions ?? []).length - 1);
    given = true;
    await administrator.give(holder.id, DEPRIVED, kept);
    await signIn(page, holder, ACCOUNT);

    // The roles of resources are read, and the screen offers no command to create one.
    await page.goto(RESOURCES);
    const roles = page.getByRole("grid", { name: "Rôles de ressources" });
    await expect(roles.getByRole("row").nth(2)).toBeVisible({ timeout: WORKING });
    await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Nouveau rôle" })).toHaveCount(0);

    // Asked of the API all the same, the creation is refused, the permission named.
    const headers = { Authorization: `Bearer ${await frontToken(browser, holder)}` };
    const read = await calls.get(`${API}/reference/resource-roles`, { headers });
    expect(read.status(), "GET /reference/resource-roles").toBe(200);
    const created = await calls.post(`${API}/reference/resource-roles`, {
      headers,
      data: {
        code: `RL-${stamp}`,
        label: `Rôle refusé ${stamp}`,
        org_node_id: WITNESS.node,
        cost_category_id: WITNESS.category,
        calendar_id: WITNESS.calendar,
        capacity: { monthly_hours: "520.00", headcount: "3" },
      },
    });
    expect(created.status(), "POST /reference/resource-roles").toBe(403);
    const refusal = (await created.json()) as Schemas["Problem"];
    expect(refusal.code).toBe("PERMISSION_MISSING");
    expect(refusal.params).toEqual({ missing_permission: "resource_settings.write" });
  } finally {
    try {
      withdrawRoles(holder.email);
      if (given) {
        await administrator.remove(DEPRIVED);
      }
    } catch (failure) {
      console.error("The cleanup of the refusal path failed:", failure);
    }
    await calls.dispose();
  }
});
