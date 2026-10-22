// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screens of the application, as the paths read them: those of the table of the functions
 * (`functions.json`) — the screen of a block, of a function, of a leaf with a screen of its own —,
 * and those no table names — the project itself, the pages of the account, the way in, an address
 * not found —, each at its address in the project and the revision of the examples of the
 * contract, and named as its heading names it. The links that reach the first (`screens.spec.ts`)
 * and the accessibility of all of them (`accessibility.spec.ts`) are drawn from here, and a test
 * of the front holds every page of `src/app` to these screens and to the pages that only redirect
 * (`src/app/screens.test.ts`): a page added has its paths, or the test says it has none.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import catalogue from "../messages/fr.json" with { type: "json" };
import type { FunctionGroup } from "../src/navigation/functions";
import table from "../src/navigation/functions.json" with { type: "json" };

/**
 * The table as the front reads it (`FUNCTION_GROUPS`): its module imports the JSON without the
 * attribute Node asks for, and cannot be loaded here.
 */
export const FUNCTION_GROUPS = table.groups as readonly FunctionGroup[];

/**
 * The project of the examples, read when the paths run: the fixtures lie outside the front, which
 * the image builds alone, and a static import would fail its type check.
 */
const project = JSON.parse(
  readFileSync(join(import.meta.dirname, "../../fixtures/api/project.json"), "utf-8"),
) as { value: { label: string } };

// The project of the examples of the contract, in progress, and its current revision.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

/** The text of a key of the reference catalogue, the French one, which names the controls. */
export function text(key: string): string {
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
export function path(route: string): string {
  return route.replace("[projectId]", PROJECT).replace("[revisionId]", REVISION);
}

/** A screen: a code that names it, its route, the address it opens at, and its heading. */
export interface AppScreen {
  readonly code: string;
  readonly route: string;
  readonly address: string;
  readonly name: string;
}

/** A screen of the table, at its route in the project and the revision of the examples. */
function tableScreen(code: string, route: string, label: string): AppScreen {
  return { code, route, address: path(route), name: text(label) };
}

/** Every screen of the table, in its order: a block that has one, then its functions and leaves. */
export function tableScreens(): AppScreen[] {
  return FUNCTION_GROUPS.flatMap((group) => [
    ...(group.route === undefined ? [] : [tableScreen(group.code, group.route, group.label)]),
    ...group.functions.flatMap((fn) => [
      tableScreen(fn.code, fn.route, fn.label),
      ...(fn.leaves ?? []).map((leaf) => tableScreen(leaf.code, leaf.route, leaf.label)),
    ]),
  ]);
}

/**
 * The screens no table names: the project itself, under its label; the account and its pages; the
 * sign-in that could not be made — the way in is the identity provider's, `/login` a route that
 * sends the browser there (EP-03) —; and the screen of an address no page answers.
 */
export const OTHER_SCREENS: readonly AppScreen[] = [
  {
    code: "project",
    route: "/projects/[projectId]",
    address: path("/projects/[projectId]"),
    name: project.value.label,
  },
  { code: "account", route: "/account", address: "/account", name: text("accountMenu.account") },
  {
    code: "account-avatar",
    route: "/account/avatar",
    address: "/account/avatar",
    name: text("accountMenu.avatar"),
  },
  {
    code: "login-unavailable",
    route: "/login/unavailable",
    address: "/login/unavailable",
    name: text("failure.unreachable.title"),
  },
  {
    code: "not-found",
    route: "/[...path]",
    address: "/no-such-screen",
    name: text("notFound.title"),
  },
];

/**
 * The grids of the planning and of the estimate opened on the amendment 2 of the current revision, a
 * differential (`structures`): the marks of a difference, `+`, `-` and `M`, tint their rows in a
 * green, a red and a yellow, and the contrast of those colours is held in both modes (US-0500).
 * The comparison of two revisions marks its nodes alike, in the same grid: the screen of the
 * revisions opened on the offer compared to the reference. Three more addresses of pages the table
 * already names, not three more pages: they are checked with the screens, and not counted in them
 * (`src/app/screens.test.ts`).
 */
export const DIFFERENTIAL_SCREENS: readonly AppScreen[] = [
  ...[
    ["planning", "/projects/[projectId]/revisions/[revisionId]/planning", "functions.planning"],
    ["estimate", "/projects/[projectId]/revisions/[revisionId]/estimate", "functions.estimate"],
  ].map(([code = "", route = "", label = ""]) => ({
    code: `${code}-differential`,
    route,
    address: `${path(route)}?structure=01926f3a-7c00-7000-8000-000000000203`,
    name: text(label),
  })),
  {
    code: "revisions-comparison",
    route: "/projects/[projectId]/revisions",
    address:
      path("/projects/[projectId]/revisions") +
      "?from_revision_id=01926f3a-7c00-7000-8000-000000000100" +
      "&to_revision_id=01926f3a-7c00-7000-8000-000000000101",
    name: text("functions.revisions"),
  },
];

/** The pages that only redirect, and have no screen of their own to check. */
export const REDIRECTS: readonly string[] = [
  // The former address of the list of projects, to the home.
  "/projects",
  // A revision itself, to the first function of a revision the session may read.
  "/projects/[projectId]/revisions/[revisionId]",
];
