// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Each route of the table of the functions reached by a click on a link (EP-02/L3), one path a
 * route, drawn from `functions.json` itself, so that a route added to the table has its path: a
 * function by a link of the navigation, on the screen of another function of its block — the block
 * of the page shown is open —, or of a revision for a function of a project; a leaf with a screen
 * of its own by a link of the screen of its function; the list of projects by the navigation.
 * Each screen reached names its function, and shows the leaves the table says it shows itself
 * (`sections`), found by their role and their name, or a fact by its text in the list of facts
 * that names it. `make screens` holds the table against the FBS and the pages of the application;
 * this path proves the links in a browser: a link hidden, or that a click does not reach, fails it.
 *
 * The route reached is compiled before the path starts (`compile`, #142), and a screen of a project
 * the path starts from is opened hydrated (`openHydrated`, #471). The session of the fake back
 * grants the whole catalogue of permissions: every function is offered. A browser in French, the
 * reference catalogue, which names the controls.
 */
import { expect, type Locator, type Page, test } from "@playwright/test";

import catalogue from "../messages/fr.json" with { type: "json" };
import type { FunctionGroup, NavigationFunction, ScreenSection } from "../src/navigation/functions";
import table from "../src/navigation/functions.json" with { type: "json" };
import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";

// The table as the front reads it (`FUNCTION_GROUPS`): its module imports the JSON without the
// attribute Node asks for, and cannot be loaded here.
const FUNCTION_GROUPS = table.groups as readonly FunctionGroup[];

// The project of the examples of the contract, in progress, and its current revision.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

/** The text of a key of the reference catalogue. */
function text(key: string): string {
  const found = key.split(".").reduce<unknown>((node, part) => {
    return typeof node === "object" && node !== null
      ? (node as Record<string, unknown>)[part]
      : undefined;
  }, catalogue);
  if (typeof found !== "string") {
    throw new Error(`no text for ${key} in the reference catalogue`);
  }
  return found;
}

/** The path of a route in the project and the revision of the examples. */
function path(route: string): string {
  return route.replace("[projectId]", PROJECT).replace("[revisionId]", REVISION);
}

/** An address whose path is the one given, whatever its query: the context a link carries. */
function at(route: string): RegExp {
  return new RegExp(`^${path(route).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(\\?.*)?$`);
}

/** The screen a function is reached from: another of its block, or a revision for a project's. */
function origin(fn: NavigationFunction, block: readonly NavigationFunction[]): string {
  const others = block.filter((other) => other.code !== fn.code);
  const from =
    fn.scope === "platform" ? others[0] : others.find((other) => other.scope === "revision");
  if (from === undefined) {
    throw new Error(`no screen to reach ${fn.code} from`);
  }
  return path(from.route);
}

/**
 * Open the page a path starts from: a screen of a project hydrated, the shell witnessing it; any
 * other page by its address, the link it is left by working before hydration as after.
 */
async function start(page: Page, address: string): Promise<void> {
  await (address.startsWith("/projects/") ? openHydrated(page, address) : page.goto(address));
}

/**
 * Follow a link by a click, and check the screen it leads to names what the link does: within the
 * bound of a screen of grid, which several of them are (`WORKING`).
 */
async function follow(page: Page, link: Locator, route: string, name: string): Promise<void> {
  await expect(link).toHaveAttribute("href", at(route));
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL((url) => url.pathname === path(route), { timeout: WORKING });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(name, { timeout: WORKING });
}

/**
 * What shows a leaf on the screen of its function: by its role and its name; by a name that holds
 * its text, for the header of a column, which a computed column prefixes with « Calculé »; or, for
 * a fact, by its text in the list of facts that names it.
 */
function shown(page: Page, section: ScreenSection): Locator {
  const main = page.getByRole("main");
  const name = text(section.name);
  if (section.role === undefined) {
    return main.getByLabel(text(section.within ?? "")).getByText(name, { exact: true });
  }
  return section.role === "columnheader"
    ? main.getByRole(section.role, { name }).first()
    : main.getByRole(section.role, { name, exact: true });
}

for (const group of FUNCTION_GROUPS) {
  if (group.route !== undefined) {
    const route = group.route;
    test(`${group.code} ${route}: reached from the navigation`, async ({ page }) => {
      await compile(page.request, route);
      await page.goto("/system");
      const nav = page.getByRole("navigation", { name: text("navigation.label") });
      const name = text(group.label);
      await follow(page, nav.getByRole("link", { name, exact: true }), route, name);
    });
  }

  for (const fn of group.functions) {
    test(`${fn.code} ${fn.route}: reached from the navigation, its sections shown`, async ({
      page,
    }) => {
      await compile(page.request, path(fn.route));
      await start(page, origin(fn, group.functions));
      const nav = page.getByRole("navigation", { name: text("navigation.label") });
      const name = text(fn.label);
      await follow(page, nav.getByRole("link", { name, exact: true }), fn.route, name);
      for (const section of fn.sections ?? []) {
        await test.step(`${section.code} on the screen of ${fn.code}`, async () => {
          await expect(shown(page, section)).toBeVisible();
        });
      }
    });

    for (const leaf of fn.leaves ?? []) {
      test(`${leaf.code} ${leaf.route}: reached from the screen of ${fn.code}`, async ({
        page,
      }) => {
        await compile(page.request, path(leaf.route));
        await start(page, path(fn.route));
        const name = text(leaf.label);
        const link = page.getByRole("main").getByRole("link", { name, exact: true });
        await follow(page, link, leaf.route, name);
      });
    }
  }
}
