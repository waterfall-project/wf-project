// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ACCOUNT_DEACTIVATED_DIGEST,
  ACCOUNT_NOT_ADMITTED_DIGEST,
  componentDigest,
  correlationDigest,
  SESSION_LOST_DIGEST,
  SESSION_REQUIRED_DIGEST,
  SESSION_REVOKED_DIGEST,
  UNREACHABLE_DIGEST,
} from "@/components/system/failure";

import { rejectedAfter, rejectedRead, rejectedWrite } from "./rejection";

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
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("is a write that may have been done when the link of the browser to the server was lost: fetch rejected, read anew before it is offered again [WF-REV-0010-A]", () => {
    vi.stubGlobal("navigator", { onLine: true });
    expect(rejectedWrite()(new TypeError("Failed to fetch"))).toEqual({
      kind: "unreachable",
      sent: true,
    });
  });

  it("is still a write that may have been done when the browser turns offline AFTER the sending [WF-REV-0010-A]", () => {
    const navigator = { onLine: true };
    vi.stubGlobal("navigator", navigator);
    const reject = rejectedWrite();
    navigator.onLine = false;
    expect(reject(new TypeError("Failed to fetch"))).toEqual({ kind: "unreachable", sent: true });
  });

  it("is the API out of reach, to try again in a moment, when the browser knew itself offline before the sending [WF-REV-0010-A]", () => {
    vi.stubGlobal("navigator", { onLine: false });
    const reject = rejectedWrite();
    vi.stubGlobal("navigator", { onLine: true });
    expect(reject(new TypeError("Failed to fetch"))).toEqual({ kind: "unreachable" });
    expect(rejectedAfter(false)(new TypeError("Failed to fetch"))).toEqual({ kind: "unreachable" });
  });

  it("does not take a browser that does not say whether it is online for an offline one [WF-REV-0010-A]", () => {
    vi.stubGlobal("navigator", {});
    expect(rejectedWrite()(new TypeError("Failed to fetch"))).toEqual({
      kind: "unreachable",
      sent: true,
    });
  });

  it("is the API out of reach for a read, online or offline: nothing was written, so nothing may have been done [WF-REV-0010-A]", () => {
    for (const onLine of [true, false]) {
      vi.stubGlobal("navigator", { onLine });
      expect(rejectedRead(new TypeError("Failed to fetch"))).toEqual({ kind: "unreachable" });
    }
  });

  it("is classed by its digest as the screen of failure classes it: out of reach, signed out", () => {
    expect(rejectedRead(thrown(UNREACHABLE_DIGEST))).toEqual({ kind: "unreachable" });
    // A session the front held no more is told as signed out too: the notice leads away on a click.
    for (const digest of [SESSION_REQUIRED_DIGEST, SESSION_LOST_DIGEST]) {
      expect(rejectedRead(thrown(digest))).toEqual({
        kind: "signed_out",
        problem: { code: "SESSION_REQUIRED", status: 401 },
        conflictingObjectId: null,
      });
    }
  });

  it("is signed out as of a session closed by its digest, which the notice says, its sign-in asking for the identifiers again (#855)", () => {
    expect(rejectedRead(thrown(SESSION_REVOKED_DIGEST))).toEqual({
      kind: "signed_out",
      problem: { code: "SESSION_REVOKED", status: 401 },
      conflictingObjectId: null,
    });
  });

  it.each([
    ["ACCOUNT_DEACTIVATED", ACCOUNT_DEACTIVATED_DIGEST],
    ["ACCOUNT_NOT_ADMITTED", ACCOUNT_NOT_ADMITTED_DIGEST],
  ] as const)(
    "is a refusal that says the account refused (%s), not a session lost, by its digest",
    (code, digest) => {
      expect(rejectedRead(thrown(digest))).toEqual({
        kind: "refused",
        problem: { code, status: 401 },
        conflictingObjectId: null,
      });
    },
  );

  it("is the refusal that names the component unavailable, by its digest, as the API names it [WF-EXP-0040-A]", () => {
    expect(rejectedRead(thrown(componentDigest("object_storage")))).toEqual({
      kind: "refused",
      problem: {
        code: "COMPONENT_UNAVAILABLE",
        status: 503,
        params: { component: "object_storage" },
      },
      conflictingObjectId: null,
    });
  });

  it("is the unexpected error with the correlation identifier of the API, its prefix left out", () => {
    expect(rejectedRead(thrown(correlationDigest("req-01926f3a.7c00")))).toEqual(
      unexpected("req-01926f3a.7c00"),
    );
  });

  it("is the unexpected error with the reference Next gives it, when the action threw", () => {
    expect(rejectedRead(thrown("1234567890"))).toEqual(unexpected("1234567890"));
  });

  it("keeps no reference that is not of the form of a correlation identifier, nor an empty one", () => {
    expect(rejectedRead(thrown(correlationDigest("not a reference!")))).toEqual(unexpected());
    expect(rejectedRead(thrown("x".repeat(65)))).toEqual(unexpected());
    expect(rejectedRead(thrown(""))).toEqual(unexpected());
    expect(rejectedRead(new Error("a defect of the front"))).toEqual(unexpected());
    expect(rejectedRead("not even an error")).toEqual(unexpected());
  });
});
