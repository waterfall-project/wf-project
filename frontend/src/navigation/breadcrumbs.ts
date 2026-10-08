// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The steps of the breadcrumb of the shell, from the address shown: where the page sits, each
 * step before it a link when it has a page. A function outside any project sits in its block of
 * the FBS, which has no page of its own; a function of a project, in the list of projects and in
 * the project, whose page keeps the context of the address; a page of the account, in the
 * account. The last step is the page shown. The label of a project is not in the address: the
 * step names the project by its identifier, and the shell by the project the screen hands on. The
 * function a leaf sits under is a link only for a session that may read it: a costing engineer on
 * the imports and exports, a leaf of the planning they do not read, sees its name alone.
 */
import type { components } from "@/api/generated/schema";

import { findAccountPage } from "./account";
import { contextQuery, type ProjectContext } from "./context";
import {
  findScreen,
  FUNCTION_GROUPS,
  type FunctionGroup,
  functionHref,
  type NavigationFunction,
} from "./functions";
import { HOME } from "./home";

/** A permission of the catalogue, as a session carries it. */
type PermissionCode = components["schemas"]["PermissionCode"];

/** The key of the label of a step in the catalogues. */
export type CrumbLabel =
  | NavigationFunction["label"]
  | FunctionGroup["label"]
  | `accountMenu.${"account" | "password" | "avatar"}`
  | "breadcrumbs.revision";

/** A step of the breadcrumb: a label of the catalogue, or a project; a link when it has one. */
export type Crumb =
  | { readonly kind: "label"; readonly label: CrumbLabel; readonly href?: string }
  | { readonly kind: "project"; readonly projectId: string; readonly href?: string };

const PROJECTS = "/projects";
const ACCOUNT = "/account";

// The list of projects is the home.
const PROJECTS_STEP: Crumb = { kind: "label", label: "functionGroups.projects", href: HOME };

/** A step named by the catalogue, a link when it has an address. */
function label(key: CrumbLabel, href?: string): Crumb {
  return href === undefined ? { kind: "label", label: key } : { kind: "label", label: key, href };
}

/** The step of the project of a context: a link to its page, which keeps the context. */
function projectStep(context: ProjectContext): Crumb {
  return {
    kind: "project",
    projectId: context.projectId,
    href: `${PROJECTS}/${context.projectId}${contextQuery(context, true)}`,
  };
}

/** The block of the FBS a function belongs to. */
function blockOf(fn: NavigationFunction): FunctionGroup | undefined {
  return FUNCTION_GROUPS.find((group) => group.functions.includes(fn));
}

/**
 * The steps of the screen of a function, a leaf after the function it is a leaf of, a link to its
 * screen in the same context for a session that may read it, its name alone otherwise.
 */
function functionSteps(
  fn: NavigationFunction,
  parent: NavigationFunction | undefined,
  context: ProjectContext | undefined,
  permissions: readonly PermissionCode[],
): Crumb[] {
  if (fn.scope !== "platform" && context !== undefined) {
    const granted = new Set<string>(permissions);
    const readable = (above: NavigationFunction) => granted.has(`${above.permission}.read`);
    const above =
      parent === undefined
        ? []
        : [label(parent.label, readable(parent) ? functionHref(parent, context) : undefined)];
    return [PROJECTS_STEP, projectStep(context), ...above, label(fn.label)];
  }
  const block = blockOf(fn);
  return block === undefined ? [label(fn.label)] : [label(block.label), label(fn.label)];
}

/** The steps of the page of a project, or of a revision of it, which are no function. */
function projectSteps(context: ProjectContext): Crumb[] {
  if (context.revisionInPath) {
    return [PROJECTS_STEP, projectStep(context), label("breadcrumbs.revision")];
  }
  return [PROJECTS_STEP, { kind: "project", projectId: context.projectId }];
}

/**
 * The steps of the breadcrumb of an address, for a session of the permissions given; none for an
 * address that leads nowhere.
 */
export function crumbsOf(
  pathname: string,
  context: ProjectContext | undefined,
  permissions: readonly PermissionCode[],
): Crumb[] {
  if (pathname === HOME) {
    return [label("functionGroups.projects")];
  }
  const account = findAccountPage(pathname);
  if (account !== undefined) {
    return account.route === ACCOUNT
      ? [label(account.label)]
      : [label("accountMenu.account", ACCOUNT), label(account.label)];
  }
  const screen = findScreen(pathname.split("/").slice(1));
  if (screen !== undefined) {
    return functionSteps(screen.fn, screen.parent, context, permissions);
  }
  return context === undefined ? [] : projectSteps(context);
}
