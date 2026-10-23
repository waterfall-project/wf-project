// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A rate the contract bounds as a ratio and a form enters as a percentage — the rates of a project
 * (EP-14/L42i), the probability of a risk (WF-RIS-0010) —: the refusal by field of the server names
 * its bound in the ratio (`1`), and the form says it in the percentage the field enters (`100`).
 * Pure, and neither server nor client.
 */
import type { Outcome } from "@/api/problem";
import { ratioPercent } from "@/i18n/format";

/** The bounds a refusal by field may name. */
const BOUNDS: ReadonlySet<string> = new Set(["minimum", "maximum"]);

/**
 * A refusal of the rates as the form says it: each bound the server names in a ratio, for a field
 * of `rates` (by pointer), said in the percentage the field enters; any other answer as it is.
 */
export function inPercent<T>(answer: Outcome<T>, rates: ReadonlySet<string>): Outcome<T> {
  if (!("problem" in answer) || answer.problem.fields === undefined) {
    return answer;
  }
  const fields = answer.problem.fields.map((field) =>
    rates.has(field.pointer) && field.params !== undefined
      ? {
          ...field,
          params: Object.fromEntries(
            Object.entries(field.params).map(([key, value]) => [
              key,
              BOUNDS.has(key) && typeof value === "string" ? (ratioPercent(value) ?? value) : value,
            ]),
          ),
        }
      : field,
  );
  return { ...answer, problem: { ...answer.problem, fields } };
}
