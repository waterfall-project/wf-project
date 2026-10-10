// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { readRefusal, refusedHref, resultHref, withoutRefusal } from "./result-refusal";

const TASK = "01926f3a-7c00-7000-8000-000000000921";
const SCREEN = "/projects/p/revisions/r/exchanges?subproject_id=unassigned";

/** The refusal of a state that forbids the operation (409), naming the condition that lacks. */
const FORBIDDEN = {
  kind: "conflict",
  problem: {
    code: "STATE_FORBIDS_OPERATION",
    status: 409,
    params: { missing_condition: "backup_verified" },
  },
  conflictingObjectId: null,
} as const;

/** The search of the address the route sends the browser back to. */
function searchOf(href: string): URLSearchParams {
  return new URLSearchParams(href.split("?")[1]);
}

describe("the way back of a refused result", () => {
  it("leaves from the screen named, and comes back to it with the task and the refusal, read again as it was", () => {
    expect(resultHref(TASK, SCREEN)).toBe(
      `/tasks/${TASK}/result?from=${encodeURIComponent(SCREEN)}`,
    );
    const back = refusedHref(SCREEN, TASK, {
      kind: "refused",
      problem: { code: "PERMISSION_MISSING", status: 403 },
      conflictingObjectId: null,
    });
    expect(back).toBe(`${SCREEN}&refused_task=${TASK}&refusal=403%3APERMISSION_MISSING`);
    expect(readRefusal(searchOf(back))).toEqual({
      id: TASK,
      refusal: {
        kind: "refused",
        problem: { code: "PERMISSION_MISSING", status: 403 },
        conflictingObjectId: null,
      },
    });
    expect(
      withoutRefusal({
        pathname: "/projects/p/revisions/r/exchanges",
        search: back.split("?")[1] ?? "",
      }),
    ).toBe("/projects/p/revisions/r/exchanges?subproject_id=unassigned");
  });

  it("carries the condition a refusal names, which reads again as the parameter of the refusal [WF-IHM-0090-A]", () => {
    const back = refusedHref(SCREEN, TASK, FORBIDDEN);
    expect(searchOf(back).get("refusal")).toBe("409:STATE_FORBIDS_OPERATION:backup_verified");
    expect(readRefusal(searchOf(back))).toEqual({ id: TASK, refusal: FORBIDDEN });
  });

  it("reads a refusal written without a condition as before, and leaves unsaid a condition the catalogue does not know", () => {
    const bare = readRefusal(
      new URLSearchParams(`refused_task=${TASK}&refusal=409%3ASTATE_FORBIDS_OPERATION`),
    );
    expect(bare?.refusal).toEqual({
      kind: "conflict",
      problem: { code: "STATE_FORBIDS_OPERATION", status: 409 },
      conflictingObjectId: null,
    });
    expect(
      bare !== undefined && "problem" in bare.refusal && "params" in bare.refusal.problem,
    ).toBe(false);
    const unknown = readRefusal(
      new URLSearchParams(
        `refused_task=${TASK}&refusal=409%3ASTATE_FORBIDS_OPERATION%3Ano_such_condition`,
      ),
    );
    expect(
      unknown !== undefined && "problem" in unknown.refusal && "params" in unknown.refusal.problem,
    ).toBe(false);
    expect(unknown?.refusal).toMatchObject({
      problem: { code: "STATE_FORBIDS_OPERATION", status: 409 },
    });
  });

  it("reads none from an address that says a refusal it cannot stand for, and the API out of reach as such", () => {
    expect(
      readRefusal(new URLSearchParams(`refused_task=${TASK}&refusal=409%3Abackup_verified`)),
    ).toBeUndefined();
    expect(
      readRefusal(
        new URLSearchParams(`refused_task=${TASK}&refusal=409%3ASTATE_FORBIDS_OPERATION%3A`),
      ),
    ).toBeUndefined();
    expect(readRefusal(new URLSearchParams(`refused_task=${TASK}&refusal=unreachable`))).toEqual({
      id: TASK,
      refusal: { kind: "unreachable" },
    });
    expect(searchOf(refusedHref(SCREEN, TASK, { kind: "unreachable" })).get("refusal")).toBe(
      "unreachable",
    );
  });
});
