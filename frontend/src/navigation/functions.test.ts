// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { readContext } from "./context";
import {
  diagnosticGroups,
  findScreen,
  FUNCTION_GROUPS,
  functionHref,
  functionOf,
  PLATFORM_FUNCTIONS,
  readableGroups,
} from "./functions";

type Session = components["schemas"]["Session"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
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

  it("lists as functions outside any project exactly those of the table", () => {
    expect(PLATFORM_FUNCTIONS).toEqual(
      FUNCTIONS.filter((fn) => fn.scope === "platform").map((fn) => fn.permission),
    );
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

  it("routes the functions of the project itself under the project, the others under a revision", () => {
    const routes = FUNCTIONS.map((fn) => fn.route);
    expect(new Set(routes).size).toBe(routes.length);
    const ofProject = new Set(["FBS-4.1", "FBS-4.2", "FBS-4.9"]);
    for (const fn of FUNCTIONS) {
      if (ofProject.has(fn.code)) {
        expect([fn.code, fn.scope]).toEqual([fn.code, "project"]);
        expect(fn.route, fn.code).toMatch(/^\/projects\/\[projectId\]\/[a-z-]+$/);
      } else if (fn.code.startsWith("FBS-4.")) {
        expect([fn.code, fn.scope]).toEqual([fn.code, "revision"]);
        expect(fn.route, fn.code).toMatch(
          /^\/projects\/\[projectId\]\/revisions\/\[revisionId\]\/[a-z-]+$/,
        );
      } else {
        expect([fn.code, fn.scope]).toEqual([fn.code, "platform"]);
        expect(fn.route, fn.code).toMatch(/^\/(admin|portfolio|reference)\/[a-z-]+$|^\/system$/);
      }
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
    const codes = offered("session_without_administration");
    expect(codes).not.toContain("FBS-1");
    expect(codes.filter((code) => code.startsWith("FBS-1"))).toEqual([]);
    expect(codes).toContain("FBS-2.1");
    expect(codes).toContain("FBS-4.5");
  });

  it("keep the list of projects when no function of a project may be read", () => {
    expect(readableGroups(["users.read"]).map((group) => group.code)).toEqual(["FBS-1", "FBS-4"]);
    expect(readableGroups(["users.write"]).map((group) => group.code)).toEqual(["FBS-4"]);
  });

  it("keep the status screen alone when the session cannot be read", () => {
    expect(
      diagnosticGroups().map((group) => [group.code, ...group.functions.map((fn) => fn.route)]),
    ).toEqual([["FBS-1", "/system"]]);
  });
});

describe("the function of a permission", () => {
  it("is the function of the table that reads with it", () => {
    expect(functionOf("revisions").route).toBe("/projects/[projectId]/revisions");
    expect(functionOf("cost_settings").code).toBe("FBS-3.1");
  });

  it("is a defect of the table when no function reads with it", () => {
    expect(() => functionOf("platform_restore" as "users")).toThrow(
      "no function of the table reads with platform_restore.read",
    );
  });
});

describe("the address of a function", () => {
  const find = (code: string) => {
    const found = FUNCTIONS.find((fn) => fn.code === code);
    if (found === undefined) {
      throw new Error(code);
    }
    return found;
  };
  const planning = find("FBS-4.3");
  const lifecycle = find("FBS-4.9");
  const revisions = find("FBS-4.1");
  const portfolio = find("FBS-2.1");
  const FILTERS = `subproject_id=${SUBPROJECT}&as_of=2026-05-31`;

  it("is its route outside a project, whatever the context", () => {
    const context = readContext(`${IN_PROJECT}/risks`, new URLSearchParams());
    expect(functionHref(portfolio, context)).toBe("/portfolio/projects");
    expect(functionHref(portfolio, undefined)).toBe("/portfolio/projects");
  });

  it("carries the revision, the sub-project and the calculation date in a project", () => {
    const context = readContext(`${IN_PROJECT}/remaining`, new URLSearchParams(FILTERS));
    expect(functionHref(planning, context)).toBe(`${IN_PROJECT}/planning?${FILTERS}`);
  });

  it("carries the revision as a parameter to a function of the project itself, and back", () => {
    const context = readContext(`${IN_PROJECT}/remaining`, new URLSearchParams(FILTERS));
    const lifecycleHref = functionHref(lifecycle, context) ?? "";
    expect(lifecycleHref).toBe(`/projects/${PROJECT}/lifecycle?revision_id=${REVISION}&${FILTERS}`);

    const [pathname = "", query = ""] = lifecycleHref.split("?");
    const there = readContext(pathname, new URLSearchParams(query));
    expect(functionHref(planning, there)).toBe(`${IN_PROJECT}/planning?${FILTERS}`);
  });

  it("offers the functions of the project itself in a project without a revision", () => {
    const context = readContext(`/projects/${PROJECT}`, new URLSearchParams());
    expect(functionHref(revisions, context)).toBe(`/projects/${PROJECT}/revisions`);
    expect(functionHref(lifecycle, context)).toBe(`/projects/${PROJECT}/lifecycle`);
    expect(functionHref(planning, context)).toBeUndefined();
  });

  it("does not exist for a function of a project outside any project", () => {
    expect(functionHref(planning, undefined)).toBeUndefined();
    expect(functionHref(lifecycle, undefined)).toBeUndefined();
  });

  it("inserts an identifier as it is, whatever it holds", () => {
    const context = {
      projectId: "p$&q",
      revisionId: "r$'s",
      revisionInPath: true,
      parameters: new URLSearchParams(),
    };
    expect(functionHref(planning, context)).toBe("/projects/p$&q/revisions/r$'s/planning");
    expect(functionHref(lifecycle, context)).toBe("/projects/p$&q/lifecycle?revision_id=r%24%27s");
  });
});

describe("the function an address leads to", () => {
  it.each([
    [["system"], "FBS-1.3", undefined],
    [["admin", "users"], "FBS-1.1", undefined],
    [["reference", "costs"], "FBS-3.1", undefined],
    [["projects", PROJECT, "revisions", REVISION, "actual-costs"], "FBS-4.7", PROJECT, REVISION],
    [["projects", PROJECT, "lifecycle"], "FBS-4.9", PROJECT, undefined],
    [["projects", PROJECT, "revisions"], "FBS-4.1", PROJECT, undefined],
  ])("is found from %j", (segments, code, projectId, revisionId?: string) => {
    const screen = findScreen(segments);
    expect(screen?.fn.code).toBe(code);
    expect(screen?.projectId).toBe(projectId);
    expect(screen?.revisionId).toBe(revisionId);
  });

  it.each([[["admin"]], [["admin", "nobody"]], [["projects", PROJECT, "revisions", REVISION]]])(
    "is none from %j",
    (segments) => {
      expect(findScreen(segments)).toBeUndefined();
    },
  );
});
