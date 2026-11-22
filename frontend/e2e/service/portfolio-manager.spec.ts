// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The uses of the manager on the portfolio, against the service (EP-11, US-2770/L3, #3887): an
 * account that holds the predefined role « Manager » alone opens each of the seven views of the
 * portfolio on the witness loaded with its slice, then, from the list, a project of the slice it
 * is no contributor of. It carries on the path of the settings (`reference-manager.spec.ts`), whose
 * sentence of WF-INTF-0020-A it completes.
 *
 * - Of WF-INTF-0020-A, its sentence on the views of the portfolio (FBS-2) and the project the
 *   manager is no contributor of: the seven views are read at the date of calculation of the witness,
 *   3 June 2026, which the address names (`as_of`), each saying the date the server computed it at;
 *   the project of the slice opens from the list by its label, and the list of its contributors,
 *   read by the API under the token of the account, holds the project manager of the witness and
 *   not the manager (#4513): the loader of the slice gives each project that sole contributor, so
 *   that an account made for the path, which contributes to none of them, proves what the
 *   `can_open` of the list means only if it is checked not to be one.
 *
 * The account is made for the path, holds « Manager » alone, and writes nothing.
 */
import { readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

import { WORKING } from "../bounds";
import { compileAnswered } from "../compile";
import { scrollPageToGrid } from "../scroll";
import type { components } from "../../src/api/generated/schema";
import { heldToTheContract } from "./contract";
import { accountAdministrator, API, frontToken, localAccount, signIn } from "./realm";

type Schemas = components["schemas"];

heldToTheContract();

const ACCOUNT = "/account";
/** The date of calculation of the witness, which the service reads the portfolio at. */
const AS_OF = "as_of=2026-06-03";
/** The seven views of the portfolio, each by its address, the title of its screen and the reading the witness expects of it. */
const VIEWS = [
  ["/portfolio/projects", "Portefeuille de projets", "portfolio_projects"],
  ["/portfolio/workload", "Plan de charge agrégé", "portfolio_workload"],
  ["/portfolio/performance", "Performance du portefeuille", "portfolio_performance"],
  ["/portfolio/cost-structure", "Structure des coûts du portefeuille", "portfolio_cost_structure"],
  ["/portfolio/risks", "Risques du portefeuille", "portfolio_risks"],
  ["/portfolio/cost-curve", "Courbe en S du portefeuille", "portfolio_cost_curve"],
  ["/portfolio/pilot-health", "Santé du pilotage", "pilot_health"],
] as const;

/** What the witness expects of a view: the states of its reading and the count of projects of its perimeter. */
function expectedReading(name: string): { states: string; count: number } {
  const file = `${import.meta.dirname}/../../../fixtures/witness/portfolio/readings/${name}.json`;
  const reading = JSON.parse(readFileSync(file, "utf8")) as {
    query: { states: string };
    value: { scope: { project_count: number } };
  };
  return { states: reading.query.states, count: reading.value.scope.project_count };
}
/** A project of the slice of the portfolio the witness holds, in progress, with its only contributor. */
const OPENED = {
  id: "01926f3a-7c00-7000-8000-001100000001",
  code: "PRJ-301",
  label: "Modernisation de la chaufferie — Valence",
} as const;
/** The project manager of the witness, the sole contributor of each project of the slice. */
const WITNESS_MANAGER = "01926f3a-7c00-7000-8000-000000000301";

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT, ...VIEWS.map(([address]) => address));
});

test("a holder of the role « Manager » alone opens each of the seven views of the portfolio at the date of the witness, then, from the list, a project of its slice it is no contributor of [WF-INTF-0020-A]", async ({
  browser,
  page,
  playwright,
}) => {
  // Seven screens of the portfolio read by the service, the account made first: a path of one piece.
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1280, height: 800 });
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const administrator = await accountAdministrator(browser, calls);
    const manager = await localAccount(browser, administrator);
    // « Manager » alone: no « Chef de projet », which the shared paths hold beside it.
    await administrator.give(manager.id, "Manager", []);
    await signIn(page, manager, ACCOUNT);

    // The seven views, each read by the service at the date of the witness: its title, and the
    // perimeter the server retained under it, which a view the server did not read does not show.
    for (const [address, title, name] of VIEWS) {
      const { states, count } = expectedReading(name);
      await page.goto(`${address}?${AS_OF}&states=${encodeURIComponent(states)}`);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(title, {
        timeout: WORKING,
      });
      await expect(page).toHaveTitle(`${title} — Waterfall`);
      await expect(page.getByRole("main")).toContainText("calculé au 3 juin 2026", {
        timeout: WORKING,
      });
      // The perimeter holds the projects the witness reads in it: a view that read none says so.
      await expect(page.getByRole("main")).toContainText(
        new RegExp(`\\b${String(count)} projets · .*calculé au 3 juin 2026`),
        { timeout: WORKING },
      );
    }

    // From the list, the project of the slice: its row found by its code, opened from its label.
    await page.goto(
      `/portfolio/projects?${AS_OF}&states=in_progress%2Cpricing&code=${OPENED.code}`,
    );
    const grid = page.getByRole("grid", { name: "Projets du portefeuille" });
    const row = grid.getByRole("row", { name: new RegExp(OPENED.code) });
    await expect(row).toBeVisible({ timeout: WORKING });
    await scrollPageToGrid(grid);
    const link = row.getByRole("link", { name: OPENED.label });
    await expect(link).toHaveAttribute("href", `/projects/${OPENED.id}`);
    await link.click();
    await expect(page).toHaveURL((url) => url.pathname.startsWith(`/projects/${OPENED.id}`), {
      timeout: WORKING,
    });
    // The project leads to its planning, whose sidebar names the project open, with its code.
    await expect(
      page
        .getByRole("complementary", { name: "Barre latérale" })
        .getByRole("button", { name: new RegExp(`${OPENED.label} ${OPENED.code}`) }),
    ).toBeVisible({ timeout: WORKING });

    // The account is no contributor of that project: the service lists the project manager of the
    // witness alone, not it. Were it listed, opening the project would prove nothing (#4513).
    const reading = await calls.get(`${API}/projects/${OPENED.id}/contributors`, {
      headers: { Authorization: `Bearer ${await frontToken(browser, manager)}` },
    });
    expect(reading.status()).toBe(200);
    const contributors = ((await reading.json()) as Schemas["ContributorList"]).items;
    expect(contributors.map((contributor) => contributor.user_id)).toEqual([WITNESS_MANAGER]);
    expect(contributors.map((contributor) => contributor.user_id)).not.toContain(manager.id);
  } finally {
    await calls.dispose();
  }
});
