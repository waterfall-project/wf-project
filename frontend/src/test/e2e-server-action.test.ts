// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { failedPress, isDeactivation, isReactivation } from "../../e2e/server-action";

/** A request of the browser, as the predicates of `pressOnce` read it: its body alone. */
const posting = (body: string | null) => ({ postData: () => body });

/** The target of an activation, as `setActivation` of `src/api/actions/reference.ts` sends it. */
const TARGET = '{"kind":"cost_type","id":"x","lockVersion":1}';

// How the journeys tell the action a command of a row asks, without a browser (#3253): a change of
// the form of `ActivationTarget` would otherwise be said only by the wait of `WORKING`.
describe("the requests a journey takes for a command of a row", () => {
  it("take the deactivation of an object for one, and neither its reactivation nor another action", () => {
    expect(isDeactivation(posting(`[${TARGET},false]`))).toBe(true);
    expect(isDeactivation(posting(`[${TARGET},true]`))).toBe(false);
    expect(isDeactivation(posting('["estimate",{"hidden_columns":[]}]'))).toBe(false);
    expect(isDeactivation(posting(null))).toBe(false);
  });

  it("take the reactivation of an object for one, and neither its deactivation nor another action", () => {
    expect(isReactivation(posting(`[${TARGET},true]`))).toBe(true);
    expect(isReactivation(posting(`[${TARGET},false]`))).toBe(false);
    expect(isReactivation(posting('["estimate",{"hidden_columns":[]}]'))).toBe(false);
  });
});

describe("the failure of a command pressed that sent nothing", () => {
  it("says the last click refused, the cause of the failure (#3254)", () => {
    expect(failedPress(undefined)).toBe("no server action asked left from the command pressed");
    expect(failedPress(new Error("element is not visible"))).toBe(
      "no server action asked left from the command pressed; the last click refused: element is not visible",
    );
  });

  it("says the command was occupied and not pressed (#3448)", () => {
    expect(failedPress(undefined, true)).toBe(
      "no server action asked left from the command pressed; the command was occupied, and not pressed",
    );
  });
});
