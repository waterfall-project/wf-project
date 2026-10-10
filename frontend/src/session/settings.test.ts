// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { redisAddress, sessionSettings } from "./settings";

beforeEach(() => {
  vi.stubEnv("WATERFALL_KEYCLOAK_ADDRESS", "http://localhost:8080/auth/");
  vi.stubEnv("WATERFALL_KEYCLOAK_BACKCHANNEL", undefined);
  vi.stubEnv("WATERFALL_FRONT_ADDRESS", "https://waterfall.example/");
  vi.stubEnv("WATERFALL_FRONT_CLIENT_SECRET", "secret");
  vi.stubEnv("WATERFALL_REDIS_URL", "redis://redis:6379/0");
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the settings of the session", () => {
  it("place the realm under the address of Keycloak, reached the same way by the server unless told otherwise, and the return under the front", () => {
    expect(sessionSettings()).toEqual({
      realmAddress: "http://localhost:8080/auth/realms/waterfall",
      realmBackchannel: "http://localhost:8080/auth/realms/waterfall",
      callback: "https://waterfall.example/auth/callback",
      clientSecret: "secret",
    });
    vi.stubEnv("WATERFALL_KEYCLOAK_BACKCHANNEL", "https://keycloak:8443/auth");
    expect(sessionSettings().realmBackchannel).toBe("https://keycloak:8443/auth/realms/waterfall");
    expect(redisAddress()).toBe("redis://redis:6379/0");
  });

  it.each([
    "WATERFALL_KEYCLOAK_ADDRESS",
    "WATERFALL_FRONT_ADDRESS",
    "WATERFALL_FRONT_CLIENT_SECRET",
    "WATERFALL_REDIS_URL",
  ])("name %s when it is missing", (name) => {
    vi.stubEnv(name, "");
    const read = name === "WATERFALL_REDIS_URL" ? redisAddress : sessionSettings;
    expect(read).toThrow(`${name} must be set`);
  });
});
