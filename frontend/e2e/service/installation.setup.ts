// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The bootstrap of a new installation, as its first administrator meets it (US-0420, WF-EXP-0020):
 * the link `make e2e-service` gives (`E2E_INSTALLATION_LINK`) sets its password — once: empty when
 * an earlier run on the platform set it, the administrator then signing in with the password the
 * paths gave it, which the result of the path says; never in the chain, whose platform is new —;
 * signed in, it holds the role « Administrateur », and finds the three predefined roles and the
 * catalogue of the permissions. The project `installation`, on which every other path depends: they
 * act through this administrator.
 */
import { expect, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { openMenu, WORKING } from "../hydration";
import { heldToTheContract } from "./contract";
import type { components } from "../../src/api/generated/schema";
import {
  accountAdministrator,
  ADMINISTRATION_READER,
  ADMINISTRATION_READS,
  ADMINISTRATOR,
  expectPasswordSet,
  frontToken,
  LOCAL_PASSWORD,
  openLink,
  setPassword,
  signIn,
} from "./realm";

heldToTheContract();

const ACCOUNT = "/account";
const USERS = "/admin/users";
const ROLES = "/admin/access-roles";
const PREDEFINED = ["Administrateur", "Chef de projet", "Manager"];

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT, USERS, ROLES);
});

test("the administrator of a new installation sets its password by the link of the bootstrap, signs in, holds the role « Administrateur », and finds the three predefined roles and the catalogue of the permissions [WF-EXP-0020-A]", async ({
  page,
  browser,
  playwright,
}) => {
  expect(ADMINISTRATOR.email, "E2E_ADMIN_EMAIL, as make e2e-service gives it").not.toBe("");
  const link = process.env.E2E_INSTALLATION_LINK ?? "";
  if (link === "") {
    // The chain starts from a new platform: a link already used there is a bootstrap gone wrong.
    expect(process.env.CI, "E2E_INSTALLATION_LINK, empty on a new platform").toBeUndefined();
    test.info().annotations.push({
      type: "installation",
      description:
        "the link of the bootstrap was used by an earlier run: the administrator signs in with the password of the paths",
    });
  } else {
    await openLink(page, link);
    await setPassword(page, LOCAL_PASSWORD);
    await expectPasswordSet(page);
  }
  await signIn(page, ADMINISTRATOR, ACCOUNT);

  // Its account, found by its address, holds the role « Administrateur ».
  await page.goto(`${USERS}?search=${encodeURIComponent(ADMINISTRATOR.email)}`);
  // The screen of the accounts first: a read the service does not serve yet, which the page cannot
  // do without, finds it « Introuvable » in its place, under the status 200 of a streamed page —
  // twice in the queue (US-1920), said then as a grid not found.
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Gestion des utilisateurs", {
    timeout: WORKING,
  });
  const accounts = page.getByRole("grid", { name: "Comptes utilisateurs" });
  await expect(accounts.getByRole("row").last()).toHaveText("1 compte", { timeout: WORKING });
  const name = `«\u00a0${ADMINISTRATOR.name}\u00a0»`;
  const held = page.getByRole("group", { name: `Rôles de ${name}` });
  await openMenu(accounts.getByRole("button", { name: `Rôles de ${name}` }), held);
  await expect(held.getByRole("checkbox", { name: "Administrateur", exact: true })).toBeChecked();
  await expect(held.getByRole("checkbox", { checked: true })).toHaveCount(1);
  await page.keyboard.press("Escape");

  // The three predefined roles, and no other, the table under no search nor filter.
  await page.goto(`${ROLES}?search=`);
  const roles = page.getByRole("grid", { name: "Rôles d’habilitation" });
  await expect(roles.getByRole("gridcell", { name: "Prédéfini", exact: true })).toHaveCount(3, {
    timeout: WORKING,
  });
  for (const label of PREDEFINED) {
    await expect(roles.getByRole("row", { name: new RegExp(`^${label} Prédéfini `) })).toHaveCount(
      1,
    );
  }

  // The catalogue of the permissions, whole: a cell of the matrix for each, under each role.
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const token = await frontToken(browser, ADMINISTRATOR);
  const answer = await calls.get(`${process.env.WATERFALL_API_ADDRESS ?? ""}/api/v1/permissions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(answer.status()).toBe(200);
  const catalogue = (await answer.json()) as components["schemas"]["Permission"][];
  await calls.dispose();
  expect(catalogue.length).toBeGreaterThan(0);
  const matrix = page.getByRole("table", { name: "Permissions par fonction" });
  for (const label of PREDEFINED) {
    await expect(
      // A pattern is matched against the name as Playwright reads it, its spaces made plain.
      matrix.getByRole("checkbox", { name: new RegExp(` pour «\\s${label}\\s»$`) }),
    ).toHaveCount(catalogue.length);
  }
});

test("the installation holds the role « Administrateur (parcours) », made by the administrator with the reads of the administration alone, found again on a replay with its permissions checked [WF-ADM-0020]", async ({
  browser,
  playwright,
}) => {
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const administrator = await accountAdministrator(browser, calls);
    // Made first, and alone, before any worker composes a role beside it (`giveRoles`): a role
    // found by its label has its permissions checked, as for any role of the paths.
    await administrator.compose([[ADMINISTRATION_READER, ADMINISTRATION_READS]]);
    // Read again by the API: the permissions of the role are exactly the reads, none of the writes.
    const token = await frontToken(browser, ADMINISTRATOR);
    const search = new URLSearchParams({ search: ADMINISTRATION_READER }).toString();
    const answer = await calls.get(
      `${process.env.WATERFALL_API_ADDRESS ?? ""}/api/v1/access-roles?${search}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(answer.status()).toBe(200);
    const roles = (await answer.json()) as components["schemas"]["AccessRole"][];
    const role = roles.find((one) => one.label === ADMINISTRATION_READER);
    expect([...(role?.permissions ?? [])].sort()).toEqual([...ADMINISTRATION_READS].sort());
  } finally {
    await calls.dispose();
  }
});
