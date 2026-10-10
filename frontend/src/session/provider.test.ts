// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it, vi } from "vitest";

import { TEST_SETTINGS } from "@/test/identity-provider";

import { createIdentityProvider, identityProvider, type Send } from "./provider";

afterEach(() => {
  vi.unstubAllEnvs();
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

  it("fails a refresh the realm answers without a refresh token", async () => {
    const withoutRefresh: Record<string, unknown> = { ...TOKENS };
    delete withoutRefresh.refresh_token;
    const provider = createIdentityProvider(TEST_SETTINGS, answering(withoutRefresh));
    await expect(provider.refresh("r0")).rejects.toThrow("no refresh token");
  });

  it("fails a refresh the realm cannot answer, rather than close the session", async () => {
    const failing = answering({ error: "temporarily_unavailable" }, 503);
    await expect(createIdentityProvider(TEST_SETTINGS, failing).refresh("r0")).rejects.toThrow();
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
