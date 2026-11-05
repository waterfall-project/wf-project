// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the terms of the English catalogue (#1822): each term is rendered one way, and the
 * variants set aside do not come back.
 */
import { describe, expect, it } from "vitest";

import en from "../../messages/en.json";

/** Every text of a catalogue, with the key that holds it. */
function texts(node: unknown, key = ""): [string, string][] {
  if (typeof node === "string") {
    return [[key, node]];
  }
  if (typeof node === "object" && node !== null) {
    return Object.entries(node).flatMap(([name, child]) => texts(child, `${key}.${name}`));
  }
  return [];
}

/** The texts that match a variant set aside, once what is allowed is taken out. */
function found(variant: RegExp, allowed?: RegExp, outside = ""): string[] {
  return texts(en)
    .filter(([key]) => outside === "" || !key.startsWith(outside))
    .filter(([, text]) => variant.test(allowed === undefined ? text : text.replace(allowed, "")))
    .map(([key]) => key);
}

describe("the terms of the English catalogue", () => {
  it("does not render the estimate at completion as « estimate to complete » [WF-QUA-0010]", () => {
    expect(found(/estimate to complete/i)).toEqual([]);
  });

  it("writes « cash-out » with its hyphen [WF-QUA-0010]", () => {
    expect(found(/cash out/i)).toEqual([]);
  });

  it("calls a cost type a cost type, never a « nature » [WF-QUA-0010]", () => {
    expect(found(/\bnatures?\b/i, /nature of the expense|\{nature,/g)).toEqual([]);
  });

  it("keeps « schedule » to the indices and to the schedule of the backups, the planning being the planning [WF-QUA-0010]", () => {
    expect(
      found(/\bschedule\b/i, /schedule (index|performance|variance)/gi, ".admin.schedule."),
    ).toEqual([]);
  });
});
