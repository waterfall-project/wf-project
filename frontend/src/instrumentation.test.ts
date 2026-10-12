// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { PHASE_PRODUCTION_BUILD } from "next/constants";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { register } from "./instrumentation";

/** The environment the service front of `deploy/compose/compose.prod.yaml` starts with. */
const PRODUCTION = {
  WATERFALL_API_ADDRESS: "http://api:8000",
  WATERFALL_FRONT_ADDRESS: "https://waterfall.example",
  WATERFALL_KEYCLOAK_ADDRESS: "https://waterfall.example/auth",
  WATERFALL_KEYCLOAK_BACKCHANNEL: "https://waterfall.example/auth",
  WATERFALL_FRONT_CLIENT_SECRET: "secret",
  WATERFALL_REDIS_URL: "redis://:password@redis:6379/0",
  NEXT_SERVER_ACTIONS_ENCRYPTION_KEY: "a-key-of-the-server-actions",
};

beforeEach(() => {
  vi.stubEnv("NODE_ENV", "production");
  vi.stubEnv("NEXT_RUNTIME", "nodejs");
  vi.stubEnv("NEXT_PHASE", "phase-production-server");
  vi.stubEnv("WATERFALL_AUTH", undefined);
  vi.stubEnv("WATERFALL_E2E", undefined);
  for (const [name, value] of Object.entries(PRODUCTION)) {
    vi.stubEnv(name, value);
  }
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the start of the server of the front", () => {
  it("goes on with the environment of the production Compose [WF-SEC-0010-A]", async () => {
    await expect(register()).resolves.toBeUndefined();
  });

  it("goes on without the back channel to Keycloak, which defaults to its address", async () => {
    vi.stubEnv("WATERFALL_KEYCLOAK_BACKCHANNEL", undefined);
    await expect(register()).resolves.toBeUndefined();
  });

  it.each([
    "WATERFALL_KEYCLOAK_ADDRESS",
    "WATERFALL_FRONT_ADDRESS",
    "WATERFALL_FRONT_CLIENT_SECRET",
    "WATERFALL_REDIS_URL",
    "NEXT_SERVER_ACTIONS_ENCRYPTION_KEY",
  ])("stops without %s, naming it [WF-SEC-0010-A]", async (name) => {
    vi.stubEnv(name, undefined);
    await expect(register()).rejects.toThrow(
      `${name} must be set: the front does not start without them`,
    );
  });

  it("stops on an empty value as on an absent one, naming every variable missing [WF-SEC-0010-A]", async () => {
    vi.stubEnv("WATERFALL_FRONT_CLIENT_SECRET", "");
    vi.stubEnv("WATERFALL_REDIS_URL", undefined);
    await expect(register()).rejects.toThrow(
      "WATERFALL_FRONT_CLIENT_SECRET, WATERFALL_REDIS_URL must be set",
    );
  });

  it("asks the development server for the session alone, not for the key of the server actions", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("NEXT_SERVER_ACTIONS_ENCRYPTION_KEY", undefined);
    await expect(register()).resolves.toBeUndefined();
    vi.stubEnv("WATERFALL_FRONT_CLIENT_SECRET", undefined);
    await expect(register()).rejects.toThrow("WATERFALL_FRONT_CLIENT_SECRET must be set");
  });

  it.each([
    ["while next build builds and prerenders the pages", "NEXT_PHASE", PHASE_PRODUCTION_BUILD],
    ["on the edge runtime, which serves no page", "NEXT_RUNTIME", "edge"],
  ])("checks nothing %s, which the image is built without", async (_case, name, value) => {
    for (const variable of Object.keys(PRODUCTION)) {
      vi.stubEnv(variable, undefined);
    }
    vi.stubEnv(name, value);
    await expect(register()).resolves.toBeUndefined();
  });

  it("asks nothing of the fake back, which grants the session, in the harness that measures it", async () => {
    for (const variable of Object.keys(PRODUCTION)) {
      vi.stubEnv(variable, undefined);
    }
    vi.stubEnv("WATERFALL_AUTH", "mock");
    vi.stubEnv("WATERFALL_E2E", "1");
    await expect(register()).resolves.toBeUndefined();
  });

  it("stops on the fake back in production out of the harness, saying so", async () => {
    vi.stubEnv("WATERFALL_AUTH", "mock");
    await expect(register()).rejects.toThrow("WATERFALL_AUTH=mock is refused in production");
  });
});
