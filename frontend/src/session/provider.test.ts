// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it, vi } from "vitest";

import { TEST_SETTINGS } from "@/test/identity-provider";

import { createIdentityProvider, identityProvider, RealmUnreachable, type Send } from "./provider";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

/** A token endpoint that answers every refresh with one body, at one status. */
function answering(body: Record<string, unknown>, status = 200): Send {
  return () => Promise.resolve(Response.json(body, { status }));
}

const TOKENS = { access_token: "a", refresh_token: "r", token_type: "Bearer", expires_in: 300 };

describe("the identity provider", () => {
  it("is the realm the environment names, which the browser signs in at, coming back to the front", () => {
    vi.stubEnv("WATERFALL_KEYCLOAK_ADDRESS", "https://sso.example/auth");
    vi.stubEnv("WATERFALL_KEYCLOAK_BACKCHANNEL", "https://keycloak:8443/auth");
    vi.stubEnv("WATERFALL_FRONT_ADDRESS", "https://waterfall.example");
    vi.stubEnv("WATERFALL_FRONT_CLIENT_SECRET", "secret");
    const address = identityProvider().signInAddress("s", "n", "c");
    expect(`${address.origin}${address.pathname}`).toBe(
      "https://sso.example/auth/realms/waterfall/protocol/openid-connect/auth",
    );
    expect(address.searchParams.get("redirect_uri")).toBe(
      "https://waterfall.example/auth/callback",
    );
    expect(identityProvider()).toBe(identityProvider());
  });

  it("keeps a session as long as the access token when the realm does not say how long it lives", async () => {
    const tokens = await createIdentityProvider(TEST_SETTINGS, answering(TOKENS)).refresh("r0");
    expect(tokens).toMatchObject({ accessToken: "a", refreshToken: "r", lifetime: 300 });
  });

  it.each([
    ["answers without a refresh token", answering({ ...TOKENS, refresh_token: undefined })],
    ["answers 503", answering({ error: "temporarily_unavailable" }, 503)],
  ])(
    "closes the session when the realm %s: the token sent may have been taken, and is never presented again (#687)",
    async (_, send) => {
      vi.spyOn(console, "error").mockReturnValue();
      await expect(createIdentityProvider(TEST_SETTINGS, send).refresh("r0")).resolves.toBe(
        undefined,
      );
    },
  );

  it.each([
    "ECONNREFUSED",
    "ENETDOWN",
    "EHOSTDOWN",
    "UND_ERR_CONNECT_TIMEOUT",
    "UNABLE_TO_VERIFY_LEAF_SIGNATURE",
    "CERT_HAS_EXPIRED",
    "DEPTH_ZERO_SELF_SIGNED_CERT",
    "SELF_SIGNED_CERT_IN_CHAIN",
  ])(
    "says the realm out of reach when a refresh could not leave, rather than close the session: %s",
    async (code) => {
      const failed = Object.assign(new Error(code), { code });
      const send: Send = () => Promise.reject(new TypeError("fetch failed", { cause: failed }));
      const provider = createIdentityProvider(TEST_SETTINGS, send);
      await expect(provider.refresh("r0")).rejects.toBeInstanceOf(RealmUnreachable);
    },
  );

  it("says the realm out of reach when the code of a sign-in cannot be exchanged", async () => {
    const send: Send = () => Promise.reject(new TypeError("fetch failed"));
    const provider = createIdentityProvider(TEST_SETTINGS, send);
    const exchange = provider.exchange("?code=c&state=s", "s", "n", "v");
    await expect(exchange).rejects.toBeInstanceOf(RealmUnreachable);
  });

  it("asks the realm for a silent sign-in, which shows no page (#689), or for one that asks for the identifiers again (#855)", () => {
    const provider = createIdentityProvider(TEST_SETTINGS);
    expect(provider.signInAddress("s", "n", "c", "none").searchParams.get("prompt")).toBe("none");
    expect(provider.signInAddress("s", "n", "c", "login").searchParams.get("prompt")).toBe("login");
    expect(provider.signInAddress("s", "n", "c").searchParams.has("prompt")).toBe(false);
  });

  it("fails a logout when the keys of the realm are out of reach, rather than refuse it", async () => {
    const send: Send = () => Promise.reject(new TypeError("fetch failed"));
    const provider = createIdentityProvider(TEST_SETTINGS, send);
    const token = "eyJhbGciOiJSUzI1NiIsImtpZCI6InJlYWxtIn0.eyJzdWIiOiJjIn0.c2ln";
    await expect(provider.loggedOut(token)).rejects.toThrow("fetch failed");
  });

  it("speaks to the realm over HTTPS only", () => {
    const clear = { ...TEST_SETTINGS, realmAddress: "http://localhost:8080/auth/realms/waterfall" };
    expect(() => createIdentityProvider(clear).signInAddress("s", "n", "c")).toThrow("HTTPS");
  });
});
