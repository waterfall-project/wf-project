// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { askPasswordReset, resetPassword, signIn, signOut } from "./session";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The API out of reach: `fetch` itself rejects. */
function unreachable() {
  server.client = createApiClient({
    address: "http://unreachable.invalid",
    fetch: () => Promise.reject(new TypeError("fetch failed")),
  });
}

const CREDENTIALS = { email: "camille.martin@example.com", password: "court" };

beforeEach(() => {
  server.client = undefined;
});

describe("the server actions of the session", () => {
  it("open a session with the credentials as they were typed, and give back nothing of it", async () => {
    // No rule of the password in the front: a short one goes to the API, which judges it.
    const client = serve({ "POST /session": { example: "session", status: 201 } });
    expect(await signIn(CREDENTIALS)).toEqual({ kind: "done", data: null });
    expect(client.calls.map(({ route, body }) => [route, body])).toEqual([
      ["POST /session", CREDENTIALS],
    ]);
  });

  it("tell the credentials refused as a refusal, not as a session to open", async () => {
    const invalid = { code: "INVALID_CREDENTIALS", status: 401 } as const;
    serve({ "POST /session": { problem: invalid } });
    expect(await signIn(CREDENTIALS)).toEqual({
      kind: "refused",
      problem: invalid,
      conflictingObjectId: null,
    });
    const locked = { code: "ACCOUNT_LOCKED", status: 429 } as const;
    serve({ "POST /session": { problem: locked } });
    expect(await signIn(CREDENTIALS)).toMatchObject({ kind: "refused", problem: locked });
  });

  it("close the session, and hold the user signed out when there was none left", async () => {
    const client = serve({ "DELETE /session": { status: 204 } });
    expect(await signOut()).toEqual({ kind: "done", data: null });
    expect(client.calls.map((call) => call.route)).toEqual(["DELETE /session"]);

    serve({ "DELETE /session": { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    expect(await signOut()).toEqual({ kind: "done", data: null });
  });

  it("say the API out of reach rather than a session closed", async () => {
    unreachable();
    expect(await signOut()).toEqual({ kind: "unreachable" });
    expect(await signIn(CREDENTIALS)).toEqual({ kind: "unreachable" });
  });

  it("ask for the link of a new password, then set it with the token of the link", async () => {
    const client = serve({
      "POST /session/password-reset": { status: 202 },
      "POST /session/password-reset/confirm": { status: 204 },
    });
    expect(await askPasswordReset("camille.martin@example.com")).toEqual({
      kind: "done",
      data: null,
    });
    expect(await resetPassword("a-token-of-twenty-characters", "court")).toEqual({
      kind: "done",
      data: null,
    });
    expect(client.calls.map(({ route, body }) => [route, body])).toEqual([
      ["POST /session/password-reset", { email: "camille.martin@example.com" }],
      [
        "POST /session/password-reset/confirm",
        { token: "a-token-of-twenty-characters", password: "court" },
      ],
    ]);
  });

  it("tell a link expired or used, and a password the API refuses, by their codes", async () => {
    const expired = { code: "PASSWORD_RESET_TOKEN_INVALID", status: 409 } as const;
    serve({ "POST /session/password-reset/confirm": { problem: expired } });
    expect(await resetPassword("a-token-of-twenty-characters", "long enough")).toMatchObject({
      kind: "conflict",
      problem: expired,
    });
    const refused = { code: "VALIDATION_FAILED", status: 422 } as const;
    serve({ "POST /session/password-reset/confirm": { problem: refused } });
    expect(await resetPassword("a-token-of-twenty-characters", "court")).toMatchObject({
      kind: "refused",
      problem: refused,
    });
  });
});
