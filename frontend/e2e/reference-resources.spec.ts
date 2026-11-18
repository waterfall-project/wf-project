// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the settings of the resources (`/reference/resources`): the roles, the tree of the
 * organisation, the calendars and the units of duration, against the fake back and, for the paths
 * tagged `@shared`, against the service (US-0850). The service keeps what is written: the paths
 * that write leave a state equivalent to the one they found — the units of duration alternate
 * between 7 and 8 — and the screen shows no mock-up notice. Every path of this file writes what the
 * installation holds once — the units of duration, the default calendar, the position of a node, the
 * activity of a role, a calendar or a node — and is read by the paths beside it (the roles and the
 * calendars of the settings of the costs, the schedules of every project, which the default calendar
 * dates): each is tagged `@serial`, so that the project `shared-serial` plays them alone, after the
 * others, and no worker reads the installation as one of them restores it (US-1330, US-1890).
 */
import { expect, type Locator, type Request } from "@playwright/test";

import { WORKING } from "./bounds";
import { sortUntilAddress } from "./hydration";
import { inService, test } from "./mode";
import { answerOf, isDeactivation, isReactivation, pressOnce } from "./server-action";

/** A suffix no other run of the service has used, for the code and the label of a role created. */
const STAMP = Date.now().toString(36);

// The fake back serves the first example of each read of the reference data — the grid of the
// volumes, a hundred and fifty categories of labour over fifteen years, the natures, the
// organisation, the roles and the calendars of the witness —, and the first example of
// `setHourlyRate` whatever was written: the first rate of 2015 of the mechanical engineering of
// level 1, the third row of the grid, which has none before 2016. What the screens ask of each is
// proven by the tests of the pages and of the grid.

test("sorts and searches each list of the settings of the resources by the server, folds the tree, and shows and reactivates the deactivated objects @shared @serial [WF-IHM-0060-A] [WF-REF-0150-A]", async ({
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

  // Every role asked of the server, the chip of their state lifted — the active ones alone by
  // default (US-2090) —, each deactivated one offered to be reactivated.
  await page
    .getByRole("region", { name: "Rôles de ressources" })
    .getByRole("button", { name: "Retirer le filtre État : Actifs (par défaut)" })
    .click();
  await expect(page).toHaveURL(/role_is_active=all/, { timeout: WORKING });
  try {
    // The reactivation is a server action, told from the others — the settings of the grids kept
    // as the address changes — by its body (`isReactivation`), and pressed once (#3135).
    const reactivated = await pressOnce(
      page,
      roles.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" }),
      isReactivation,
    );
    expect((await answerOf(reactivated)).status()).toBe(200);
    // The row shows what the server answers: active again, offering its deactivation (EP-02/L43b).
    await expect(
      roles.getByRole("button", { name: "Désactiver «\u00a0Automaticien\u00a0»" }),
    ).toBeVisible({ timeout: WORKING });
    await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
  } finally {
    if (inService) {
      // The service kept it: the role is left deactivated, as the witness has it, even on a
      // failure.
      const deactivate = roles.getByRole("button", {
        name: "Désactiver «\u00a0Automaticien\u00a0»",
      });
      // Nothing to undo when the reactivation itself failed.
      if (await deactivate.isVisible()) {
        const deactivated = await pressOnce(page, deactivate, isDeactivation);
        expect((await answerOf(deactivated)).status()).toBe(200);
        await expect(
          roles.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" }),
        ).toBeVisible({ timeout: WORKING });
      }
    }
  }

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

test("creates a role in its form, moves a node under an active one, and designates the default calendar as its row lists it, with no mock-up notice @shared @serial [WF-REF-0090-A] [WF-REF-0080-A] [WF-REF-0120-A]", async ({
  page,
}) => {
  test.slow();
  await page.goto("/reference/resources");
  await expect(page.getByRole("note")).toHaveCount(0);
  // The fake back answers its example whatever is written; the service, what was written.
  const code = inService ? `DESS-${STAMP}` : "DESS-ELEC";
  const label = inService ? `Dessinateur ${STAMP}` : "Dessinateur électricien";

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
  await form.getByRole("textbox", { name: "Code" }).fill(code);
  await form.getByRole("textbox", { name: "Libellé" }).fill(label);
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
  // The hours per month are calculated: the form types the headcount alone (WF-IHM-0030-A).
  await expect(form.getByRole("textbox", { name: "Effectif" })).toBeVisible();
  await expect(form.getByRole("textbox", { name: "Heures par mois" })).toHaveCount(0);
  await form.getByRole("textbox", { name: "Effectif" }).fill("3");
  const nodeForm = page.getByRole("dialog", { name: "Modifier «\u00a0Atelier de câblage\u00a0»" });
  const calendars = page.getByRole("grid", { name: "Calendriers" });
  const calendarRow = (label: string) => calendars.getByRole("row").filter({ hasText: label });
  let moved = false;
  // The restorations that failed: told once the path is done, if the path itself did not fail.
  const notRestored: unknown[] = [];
  // The role is written by the click on « Créer »: whatever fails after it, it is deactivated.
  try {
    await form.getByRole("button", { name: "Créer" }).click();
    await expect(form).toBeHidden({ timeout: WORKING });
    // The list says what the server created — its example —, and adds no row of its own.
    await expect(roles.getByRole("status").filter({ hasText: "créé" })).toHaveText(
      `«\u00a0${label}\u00a0» créé.`,
    );
    if (inService) {
      // The service kept it: the list read anew shows the role.
      await page.goto("/reference/resources?role_is_active=all");
      await expect(
        page.getByRole("grid", { name: "Rôles de ressources" }).getByRole("row", {
          name: new RegExp(code),
        }),
      ).toBeVisible({ timeout: WORKING });
      await page.goto("/reference/resources");
    }

    // The workshop moved under the direction in its form: the active nodes alone are offered as
    // its parent, never the workshop itself; the parent is sent, and the list says what the server
    // wrote.
    const organisation = page.getByRole("region", { name: "Arbre d’organisation" });
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
    moved = true;
    await expect(nodeForm).toBeHidden({ timeout: WORKING });
    await expect(organisation.getByRole("status").filter({ hasText: "enregistré" })).toHaveText(
      "«\u00a0Atelier de câblage\u00a0» enregistré.",
    );

    // The four-day week designated by default from its row, as it lists the command: the row shows
    // what the server answers.
    await calendars
      .getByRole("button", { name: "Désigner «\u00a0Semaine de quatre jours\u00a0» par défaut" })
      .click();
    // Found by its label, not by its position: the bootstrap writes a calendar of its own, which
    // sorts before this one by label.
    await expect(calendarRow("Semaine de quatre jours")).toContainText("Calendrier par défaut", {
      timeout: WORKING,
    });
    await expect(
      page
        .getByRole("region", { name: "Calendriers" })
        .getByRole("status")
        .filter({ hasText: "désigné" }),
    ).toHaveText("«\u00a0Semaine de quatre jours\u00a0» désigné calendrier par défaut.");
    await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
  } finally {
    if (inService) {
      // Leave what was found, even on a failure: the role created deactivated, the workshop under
      // the electrical design office, the standard week by default, each by the command of its row.
      // Each restoration stands alone and never replaces the error that brought us here; its
      // gestures follow a navigation, so they are pressed again until React answers.
      const restore = async (step: () => Promise<void>) => {
        try {
          await page.goto("/reference/resources");
          await step();
        } catch (error) {
          notRestored.push(error);
        }
      };
      // A command pressed waits, `aria-disabled`, until its write answers (#2260), and Playwright
      // waits for an enabled target: pressed again meanwhile, a click without a bound would wait
      // until the command is gone, past the time of the retries. Each click is bounded, and the
      // retry goes on.
      const deactivate = page
        .getByRole("grid", { name: "Rôles de ressources" })
        .getByRole("button", { name: `Désactiver «\u00a0${label}\u00a0»` });
      await restore(async () => {
        await expect(async () => {
          if (await deactivate.isVisible()) {
            await deactivate.click({ timeout: 1_000 });
          }
          await expect(deactivate).toBeHidden({ timeout: 1_000 });
        }).toPass({ timeout: WORKING });
      });
      if (moved) {
        await restore(async () => {
          await expect(async () => {
            if (!(await nodeForm.isVisible())) {
              await page
                .getByRole("treegrid", { name: "Arbre d’organisation" })
                .getByRole("button", { name: "Modifier «\u00a0Atelier de câblage\u00a0»" })
                .click({ timeout: 1_000 });
            }
            await expect(nodeForm).toBeVisible({ timeout: 1_000 });
          }).toPass({ timeout: WORKING });
          await nodeForm
            .getByRole("combobox", { name: "Parent" })
            .selectOption({ label: "\u2003BE-ELEC · Bureau d'études électricité" });
          await nodeForm.getByRole("button", { name: "Enregistrer" }).click();
          await expect(nodeForm).toBeHidden({ timeout: WORKING });
        });
      }
      // The button exists only for a calendar that is not the default: seen, the command is
      // pressed; absent, there is nothing to restore.
      const standard = calendars.getByRole("button", {
        name: "Désigner «\u00a0Semaine standard\u00a0» par défaut",
      });
      await restore(async () => {
        await expect(async () => {
          if (await standard.isVisible()) {
            await standard.click({ timeout: 1_000 });
          }
          await expect(calendarRow("Semaine standard")).toContainText("Calendrier par défaut", {
            timeout: 1_000,
          });
        }).toPass({ timeout: WORKING });
      });
    }
  }
  // A restoration that failed leaves the service changed: the path, which passed, does not.
  expect(notRestored, "the restorations that failed").toEqual([]);
});

test("modifies the units of duration from the settings of the resources, and says what the change does to the schedules (US-0570) @shared @serial", async ({
  page,
}) => {
  test.slow();
  await page.goto("/reference/resources");
  const section = page.getByRole("region", { name: "Unités de durée" });
  const value = (name: string) =>
    section.getByText(name, { exact: true }).locator("xpath=following-sibling::dd");
  // The fake back starts from 8 hours; the service from what the installation keeps, which a
  // replay found changed: the path writes the other of 7 and 8, valid on every run.
  await expect(value("Heures par jour")).toHaveText(/^\d+$/, { timeout: WORKING });
  const before = (await value("Heures par jour").textContent()) ?? "";
  if (!inService) {
    expect(before).toBe("8");
  }
  const written = before === "7" ? "8" : "7";
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
  await form.getByRole("textbox", { name: "Heures par jour" }).fill(written);
  await form.getByRole("button", { name: "Enregistrer" }).click();
  await expect(form).toBeHidden({ timeout: WORKING });
  if (!inService) {
    // The fake back answers the first example of the operation whatever was written: 7 and 35.
    await expect(value("Heures par semaine")).toHaveText("35");
  }
  await expect(page.getByRole("status").filter({ hasText: "enregistrées" })).toHaveText(
    "Unités de durée enregistrées.",
  );
  await expect(section.getByRole("button", { name: "Modifier les unités de durée" })).toBeFocused();
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
  if (inService) {
    // What the service kept, read anew after a reload.
    await page.reload();
    await expect(value("Heures par jour")).toHaveText(written, { timeout: WORKING });
  }
});

/**
 * What a command to delete is called: the settings of the resources offer none (WF-REF-0010-A).
 * « Effacer les filtres », which the chips of the filters of a table bring, deletes nothing.
 */
const DELETION = /supprim|effac(?!er les filtres)|delete/i;

test("shows the deactivated roles, calendars and nodes by the filter of the state of each table, still named by the roles that employ them, offers no deletion, proposes only the active nodes and calendars to a role, and each again once reactivated (US-0880) @shared @serial [WF-REF-0010-A] [WF-REF-0150-A]", async ({
  page,
}) => {
  test.slow();
  // The witness holds, deactivated, a calendar, two nodes — the second under the first — and the
  // role of the automata programmer under it (the examples of the contract). The fake back ignores
  // the state asked and answers its examples whatever the address says: the roles alone hold a
  // deactivated one, so what a read leaves out or brings is asserted in service alone.
  const calendarLabel = "Semaine de trente-neuf heures";
  const nodeLabel = "Bureau d'études automatismes";
  const calendars = page.getByRole("grid", { name: "Calendriers" });
  const tree = page.getByRole("treegrid", { name: "Arbre d’organisation" });
  const roles = page.getByRole("grid", { name: "Rôles de ressources" });
  const calendar = calendars.getByRole("row", { name: new RegExp(calendarLabel) });
  const node = tree.getByRole("row", { name: new RegExp(nodeLabel) });
  const form = page.getByRole("dialog", { name: "Nouveau rôle de ressource" });
  const calendarChoice = form
    .getByRole("combobox", { name: "Calendrier" })
    .getByRole("option", { name: new RegExp(calendarLabel) });
  const nodeChoice = form
    .getByRole("combobox", { name: "Nœud d’organisation" })
    .getByRole("option", { name: new RegExp(nodeLabel) });
  const command = (verb: "Réactiver" | "Désactiver", grid: Locator, label: string) =>
    grid.getByRole("button", { name: `${verb} «\u00a0${label}\u00a0»` });
  /** The form of a role, opened pressed again until React opens it, and never once it is open. */
  const openForm = async () => {
    await expect(async () => {
      if (!(await form.isVisible())) {
        await page
          .getByRole("region", { name: "Rôles de ressources" })
          .getByRole("button", { name: "Nouveau rôle" })
          .click();
      }
      await expect(form).toBeVisible({ timeout: 1_000 });
    }).toPass({ timeout: WORKING });
  };
  /**
   * A command of a row, pressed until its action leaves and never after, a command occupied
   * (`aria-busy`, `aria-disabled`) not pressed at all (`pressOnce`, #3396): the row then offers the
   * opposite, awaited within `WORKING`.
   */
  const press = async (
    pressed: Locator,
    answered: Locator,
    asked: (request: Request) => boolean,
  ) => {
    await pressOnce(page, pressed, asked);
    await expect(answered).toBeVisible({ timeout: WORKING });
  };

  await page.goto("/reference/resources");
  if (inService) {
    // Each table opens on its active objects alone, the state by default (US-2090).
    await expect(roles.getByRole("row", { name: /Ingénieur électricien/ })).toHaveCount(1);
    await expect(calendars).toBeVisible();
    await expect(tree).toBeVisible();
    await expect(calendar).toHaveCount(0);
    await expect(node).toHaveCount(0);
    await expect(roles.getByRole("row", { name: /Programmeur d'automates/ })).toHaveCount(0);
  }

  // Every state of each table asked of the server, its chip lifted: the deactivated named
  // deactivated and offered to be reactivated by the command their row lists.
  await page.goto(
    "/reference/resources?org_is_active=all&role_is_active=all&calendar_is_active=all",
  );
  const programmer = roles.getByRole("row", { name: /Programmeur d'automates/ });
  await expect(programmer).toContainText("Désactivé", { timeout: WORKING });
  await expect(roles.getByRole("button", { name: /^Réactiver/ }).first()).toBeVisible();
  if (inService) {
    await expect(calendar).toContainText("Désactivé");
    await expect(node).toContainText("Désactivé");
    await expect(command("Réactiver", calendars, calendarLabel)).toBeVisible();
    await expect(command("Réactiver", tree, nodeLabel)).toBeVisible();
    // A deactivated object stays named where it is employed (WF-REF-0010-A): the programmer by its
    // node, the automation engineer by its calendar.
    await expect(programmer).toContainText(nodeLabel);
    await expect(roles.getByRole("row", { name: /Automaticien/ })).toContainText(calendarLabel);
  }
  // No screen offers to delete an object: neither a button nor a link of the page says it.
  await expect(page.getByRole("main").getByRole("button", { name: DELETION })).toHaveCount(0);
  await expect(page.getByRole("main").getByRole("link", { name: DELETION })).toHaveCount(0);
  await expect(page.getByRole("menuitem", { name: DELETION })).toHaveCount(0);

  // The choices of a role are the active objects alone, whatever the tables show.
  await openForm();
  await expect(form.getByRole("combobox", { name: "Nœud d’organisation" })).toBeVisible();
  await expect(nodeChoice).toHaveCount(0);
  await expect(calendarChoice).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(form).toBeHidden();

  if (inService) {
    try {
      // Reactivated, the calendar and the node are proposed again: the page is read anew by the
      // command, and the form shows them.
      await press(
        command("Réactiver", calendars, calendarLabel),
        command("Désactiver", calendars, calendarLabel),
        isReactivation,
      );
      await press(
        command("Réactiver", tree, nodeLabel),
        command("Désactiver", tree, nodeLabel),
        isReactivation,
      );
      await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
      await page.goto("/reference/resources");
      await openForm();
      await expect(nodeChoice).toHaveCount(1);
      await expect(calendarChoice).toHaveCount(1);
      await page.keyboard.press("Escape");
      await expect(form).toBeHidden();
    } finally {
      // Leave what was found, even on a failure: the node and the calendar deactivated again. Only
      // the gestures are here, so that no check hides the error that brought us here.
      // Every state asked for, so that a row stays on the page once deactivated.
      await page.goto("/reference/resources?org_is_active=all&calendar_is_active=all");
      await expect(calendars).toBeVisible({ timeout: WORKING });
      await expect(tree).toBeVisible();
      for (const [grid, label] of [
        [tree, nodeLabel],
        [calendars, calendarLabel],
      ] as const) {
        if (await command("Désactiver", grid, label).isVisible()) {
          await press(
            command("Désactiver", grid, label),
            command("Réactiver", grid, label),
            isDeactivation,
          );
        }
      }
    }
    // Left as found: neither the calendar nor the node is among the active objects again — asked
    // so, whatever state the account keeps for their tables.
    await page.goto("/reference/resources?org_is_active=true&calendar_is_active=true");
    await expect(calendars).toBeVisible({ timeout: WORKING });
    await expect(tree).toBeVisible();
    await expect(calendar).toHaveCount(0);
    await expect(node).toHaveCount(0);
  }
});
