// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { ACCOUNT_PAGES, findAccountPage } from "./account";
import { crumbsOf } from "./breadcrumbs";
import { readContext } from "./context";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

/** The steps of an address, its context read as the shell reads it. */
function steps(address: string) {
  const [pathname = "", query = ""] = address.split("?");
  return crumbsOf(pathname, readContext(pathname, new URLSearchParams(query)));
}

describe("the breadcrumb", () => {
  it("sits the home, which is the list of projects, at the root", () => {
    expect(steps("/")).toEqual([{ kind: "label", label: "functionGroups.projects" }]);
    expect(steps("/?is_contributor=false")).toEqual([
      { kind: "label", label: "functionGroups.projects" },
    ]);
  });

  it("sits a function outside any project in its block of the FBS, which has no page", () => {
    expect(steps("/portfolio/projects?as_of=2026-05-31")).toEqual([
      { kind: "label", label: "functionGroups.portfolio" },
      { kind: "label", label: "functions.portfolioProjects" },
    ]);
  });

  it("sits a function of a project in the list of projects and in the project, whose page keeps the context", () => {
    const projects = { kind: "label", label: "functionGroups.projects", href: "/" };
    expect(steps(`/projects/${PROJECT}/revisions/${REVISION}/risks?as_of=2026-05-31`)).toEqual([
      projects,
      {
        kind: "project",
        projectId: PROJECT,
        href: `/projects/${PROJECT}?revision_id=${REVISION}&as_of=2026-05-31`,
      },
      { kind: "label", label: "functions.risks" },
    ]);
    expect(steps(`/projects/${PROJECT}/lifecycle`)).toEqual([
      projects,
      { kind: "project", projectId: PROJECT, href: `/projects/${PROJECT}` },
      { kind: "label", label: "functions.lifecycle" },
    ]);
  });

  it("sits the page of a project and of a revision, which are no function, in the list of projects", () => {
    const projects = { kind: "label", label: "functionGroups.projects", href: "/" };
    expect(steps(`/projects/${PROJECT}`)).toEqual([
      projects,
      { kind: "project", projectId: PROJECT },
    ]);
    expect(steps(`/projects/${PROJECT}/revisions/${REVISION}`)).toEqual([
      projects,
      {
        kind: "project",
        projectId: PROJECT,
        href: `/projects/${PROJECT}?revision_id=${REVISION}`,
      },
      { kind: "label", label: "breadcrumbs.revision" },
    ]);
  });

  it("sits the exchanges of a project, which are no function, in the project, whose page keeps the context", () => {
    expect(steps(`/projects/${PROJECT}/exchanges?revision_id=${REVISION}&import=i`)).toEqual([
      { kind: "label", label: "functionGroups.projects", href: "/" },
      {
        kind: "project",
        projectId: PROJECT,
        href: `/projects/${PROJECT}?revision_id=${REVISION}`,
      },
      { kind: "label", label: "exchanges.title" },
    ]);
  });

  it("sits a function of a project whose address names none in its block alone", () => {
    expect(steps("/projects/a.b/lifecycle")).toEqual([
      { kind: "label", label: "functionGroups.projects" },
      { kind: "label", label: "functions.lifecycle" },
    ]);
  });

  it("sits the pages of the account in the account", () => {
    expect(steps("/account")).toEqual([{ kind: "label", label: "accountMenu.account" }]);
    expect(steps("/account/password")).toEqual([
      { kind: "label", label: "accountMenu.account", href: "/account" },
      { kind: "label", label: "accountMenu.password" },
    ]);
  });

  it("has no step for an address that leads nowhere", () => {
    expect(steps("/admin/nobody")).toEqual([]);
    expect(steps("/account/nobody")).toEqual([]);
  });
});

describe("the pages of the account", () => {
  it("are found by their route, and by it alone", () => {
    for (const entry of ACCOUNT_PAGES) {
      expect(findAccountPage(entry.route)).toBe(entry);
    }
    expect(findAccountPage("/account/")).toBeUndefined();
  });
});
