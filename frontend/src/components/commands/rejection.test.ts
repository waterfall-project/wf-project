// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  ACCOUNT_DEACTIVATED_DIGEST,
  correlationDigest,
  SESSION_REQUIRED_DIGEST,
  UNREACHABLE_DIGEST,
} from "@/components/system/failure";

import { rejected } from "./rejection";

/** An error thrown by a server action, as Next forwards it: its digest. */
function thrown(digest: string): Error {
  return Object.assign(new Error("An error occurred in the Server Components render."), {
    digest,
  });
}

/** The unexpected error, with the reference given if any. */
function unexpected(reference?: string) {
  return {
    kind: "refused",
    problem: {
      code: "INTERNAL_ERROR",
      status: 500,
      ...(reference === undefined ? {} : { correlation_id: reference }),
    },
    conflictingObjectId: null,
  };
}

describe("a server action whose promise rejected", () => {
  it("is the API out of reach when the browser could not reach the server: fetch rejected", () => {
    expect(rejected(new TypeError("Failed to fetch"))).toEqual({ kind: "unreachable" });
  });

  it("is classed by its digest as the screen of failure classes it: out of reach, signed out", () => {
    expect(rejected(thrown(UNREACHABLE_DIGEST))).toEqual({ kind: "unreachable" });
    expect(rejected(thrown(SESSION_REQUIRED_DIGEST))).toEqual({
      kind: "signed_out",
      problem: { code: "SESSION_REQUIRED", status: 401 },
      conflictingObjectId: null,
    });
  });

  it("is a refusal that says the account deactivated, not a session lost, by its digest", () => {
    expect(rejected(thrown(ACCOUNT_DEACTIVATED_DIGEST))).toEqual({
      kind: "refused",
      problem: { code: "ACCOUNT_DEACTIVATED", status: 401 },
      conflictingObjectId: null,
    });
  });

  it("is the unexpected error with the correlation identifier of the API, its prefix left out", () => {
    expect(rejected(thrown(correlationDigest("req-01926f3a.7c00")))).toEqual(
      unexpected("req-01926f3a.7c00"),
    );
  });

  it("is the unexpected error with the reference Next gives it, when the action threw", () => {
    expect(rejected(thrown("1234567890"))).toEqual(unexpected("1234567890"));
  });

  it("keeps no reference that is not of the form of a correlation identifier, nor an empty one", () => {
    expect(rejected(thrown(correlationDigest("not a reference!")))).toEqual(unexpected());
    expect(rejected(thrown("x".repeat(65)))).toEqual(unexpected());
    expect(rejected(thrown(""))).toEqual(unexpected());
    expect(rejected(new Error("a defect of the front"))).toEqual(unexpected());
    expect(rejected("not even an error")).toEqual(unexpected());
  });
});
