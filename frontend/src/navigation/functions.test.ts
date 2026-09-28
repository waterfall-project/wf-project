// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { readContext } from "./context";
import { findScreen, FUNCTION_GROUPS, functionHref, readableGroups } from "./functions";

type Session = components["schemas"]["Session"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000401";
const IN_PROJECT = `/projects/${PROJECT}/revisions/${REVISION}`;

const FUNCTIONS = FUNCTION_GROUPS.flatMap((group) => group.functions);

/** The value of a key of a catalogue, or `undefined` when it has none. */
function text(catalogue: object, key: string): unknown {
  return key.split(".").reduce<unknown>((node, part) => {
    return typeof node === "object" && node !== null && part in node
      ? (node as Record<string, unknown>)[part]
      : undefined;
  }, catalogue);
}

/** The codes of the functions of the groups offered to a session. */
function offered(name: string): string[] {
  const { permissions } = example(name) as Session;
  return readableGroups(permissions).flatMap((group) => [
    group.code,
    ...group.functions.map((fn) => fn.code),
  ]);
}

describe("the table of the functions", () => {
  it("holds the four blocks of the FBS and their functions of the second level, in order", () => {
    expect(FUNCTION_GROUPS.map((group) => group.code)).toEqual([
      "FBS-1",
      "FBS-2",
      "FBS-3",
      "FBS-4",
    ]);
    const sizes = { "FBS-1": 4, "FBS-2": 7, "FBS-3": 4, "FBS-4": 9 };
    for (const group of FUNCTION_GROUPS) {
      const expected = Array.from(
        { length: sizes[group.code as keyof typeof sizes] },
        (_, index) => `${group.code}.${String(index + 1)}`,
      );
      expect(group.functions.map((fn) => fn.code)).toEqual(expected);
    }
  });

  it("names each function and block by a key of both catalogues", () => {
    const keys = [
      ...FUNCTION_GROUPS.map((group) => group.label),
      ...FUNCTIONS.map((fn) => fn.label),
    ];
    for (const key of keys) {
      expect(text(CATALOGUES.fr, key), key).toEqual(expect.any(String));
      expect(text(CATALOGUES.en, key), key).toEqual(expect.any(String));
    }
  });

  it("guards each function by a read permission of the catalogue", () => {
    for (const fn of FUNCTIONS) {
      expect(text(CATALOGUES.fr, `permissions.${fn.permission}.read`), fn.code).toEqual(
        expect.any(String),
      );
    }
  });

  it("gives each function a route of its own, in a project for the functions of FBS-4", () => {
    const routes = FUNCTIONS.map((fn) => fn.route);
    expect(new Set(routes).size).toBe(routes.length);
    for (const fn of FUNCTIONS) {
      const inProject = fn.code.startsWith("FBS-4.");
      expect(fn.scope, fn.code).toBe(inProject ? "project" : "platform");
      expect(fn.route, fn.code).toMatch(
        inProject
          ? /^\/projects\/\[projectId\]\/revisions\/\[revisionId\]\/[a-z-]+$/
          : /^\/(admin|portfolio|reference)\/[a-z-]+$|^\/system$/,
      );
    }
  });
});

describe("the functions offered", () => {
  it("are all of them to a session granted the whole catalogue", () => {
    expect(offered("session")).toEqual([
      ...FUNCTION_GROUPS.flatMap((group) => [group.code, ...group.functions.map((fn) => fn.code)]),
    ]);
  });

  it("leave out the functions whose read permission the session lacks", () => {
    const codes = offered("session_project_manager");
    expect(codes).not.toContain("FBS-1");
    expect(codes.filter((code) => code.startsWith("FBS-1"))).toEqual([]);
    expect(codes).toContain("FBS-2.1");
    expect(codes).toContain("FBS-4.5");
  });

  it("keep the list of projects when no function of a project may be read", () => {
    expect(readableGroups(["users.read"]).map((group) => group.code)).toEqual(["FBS-1", "FBS-4"]);
    expect(readableGroups(["users.write"]).map((group) => group.code)).toEqual(["FBS-4"]);
  });
});

describe("the address of a function", () => {
  const planning = FUNCTIONS.find((fn) => fn.code === "FBS-4.3");
  const portfolio = FUNCTIONS.find((fn) => fn.code === "FBS-2.1");

  it("is its route outside a project, whatever the context", () => {
    const context = readContext(`${IN_PROJECT}/risks`, new URLSearchParams());
    expect(portfolio && functionHref(portfolio, context)).toBe("/portfolio/projects");
    expect(portfolio && functionHref(portfolio, undefined)).toBe("/portfolio/projects");
  });

  it("carries the revision, the sub-project and the calculation date in a project", () => {
    const search = new URLSearchParams({ subproject_id: SUBPROJECT, as_of: "2026-05-31" });
    const context = readContext(`${IN_PROJECT}/remaining`, search);
    expect(planning && functionHref(planning, context)).toBe(
      `${IN_PROJECT}/planning?subproject_id=${SUBPROJECT}&as_of=2026-05-31`,
    );
  });

  it("does not exist in a project without a revision to read in, nor outside", () => {
    const context = readContext(`/projects/${PROJECT}`, new URLSearchParams());
    expect(planning && functionHref(planning, context)).toBeUndefined();
    expect(planning && functionHref(planning, undefined)).toBeUndefined();
  });
});

describe("the function an address leads to", () => {
  it.each([
    [["system"], "FBS-1.3", undefined],
    [["admin", "users"], "FBS-1.1", undefined],
    [["reference", "costs"], "FBS-3.1", undefined],
    [["projects", PROJECT, "revisions", REVISION, "actual-costs"], "FBS-4.7", PROJECT],
  ])("is found from %j", (segments, code, projectId) => {
    const screen = findScreen(segments);
    expect(screen?.fn.code).toBe(code);
    expect(screen?.projectId).toBe(projectId);
  });

  it.each([[["admin"]], [["admin", "nobody"]], [["projects", PROJECT, "revisions", REVISION]]])(
    "is none from %j",
    (segments) => {
      expect(findScreen(segments)).toBeUndefined();
    },
  );
});
