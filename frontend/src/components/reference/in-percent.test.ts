// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { Outcome } from "@/api/problem";
import { example, type Problem } from "@/test/fixtures";

import { inPercent } from "./in-percent";

const PROBABILITY: ReadonlySet<string> = new Set(["/probability"]);

/** The refusal an example of the contract gives, as the form receives it. */
function refused(name: string): Outcome<never> {
  return { kind: "refused", problem: example(name) as Problem, conflictingObjectId: null };
}

describe("inPercent", () => {
  it("says the bound a refusal names in the ratio in the percentage the field enters", () => {
    const answer = inPercent(refused("risk_probability_out_of_range"), PROBABILITY);
    expect("problem" in answer ? answer.problem.fields : undefined).toEqual([
      { pointer: "/probability", code: "VALUE_OUT_OF_RANGE", params: { maximum: "100" } },
    ]);
  });

  it("leaves the fields that are no rate, and the answers that are no refusal, as they are", () => {
    const other = refused("risk_provision_refused");
    expect(inPercent(other, PROBABILITY)).toEqual(other);
    const rates = refused("project_rates_out_of_range");
    expect(inPercent(rates, PROBABILITY)).toEqual(rates);
    const out: Outcome<never> = { kind: "unreachable" };
    expect(inPercent(out, PROBABILITY)).toBe(out);
  });
});
