// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { PHASE_PRODUCTION_BUILD } from "next/constants";
import { type MockInstance, afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

/** `process.exit`, which stops nothing here: the process of the tests goes on. */
let exit: MockInstance<typeof process.exit>;
/** `console.error`, where the server writes why it stops. */
let written: MockInstance<typeof console.error>;

beforeEach(() => {
  exit = vi.spyOn(process, "exit").mockImplementation(() => undefined as never);
  written = vi.spyOn(console, "error").mockImplementation(() => undefined);
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
  vi.restoreAllMocks();
});

/** What the server wrote before it stopped, once. */
function writtenMessage(): string {
  const [error] = written.mock.calls.map(([first]: unknown[]) => first);
  return error instanceof Error ? error.message : String(error);
}

/** Expect the server to have written why, naming what it says, then stopped with the code 1. */
function expectStopped(said: string): void {
  expect(written).toHaveBeenCalledOnce();
  expect(writtenMessage()).toContain(said);
  expect(exit).toHaveBeenCalledOnce();
  expect(exit).toHaveBeenCalledWith(1);
  const [writing] = written.mock.invocationCallOrder;
  const [stopping] = exit.mock.invocationCallOrder;
  expect(writing).toBeLessThan(stopping ?? 0);
}

/** Expect the server to go on, having written nothing and stopped nothing. */
function expectGoesOn(): void {
  expect(written).not.toHaveBeenCalled();
  expect(exit).not.toHaveBeenCalled();
}

describe("the start of the server of the front", () => {
  it("goes on with the environment of the production Compose [WF-SEC-0010-A]", async () => {
    await register();
    expectGoesOn();
  });

  it("goes on without the back channel to Keycloak, which defaults to its address", async () => {
    vi.stubEnv("WATERFALL_KEYCLOAK_BACKCHANNEL", undefined);
    await register();
    expectGoesOn();
  });

  it("exits with the code 1 once it has written the variable missing [WF-SEC-0010-A]", async () => {
    vi.stubEnv("WATERFALL_REDIS_URL", undefined);
    await register();
    expect(exit.mock.calls).toEqual([[1]]);
    expect(written.mock.calls).toHaveLength(1);
    expect(writtenMessage()).toBe(
      "WATERFALL_REDIS_URL must be set: the front does not start without them",
    );
    expect(written.mock.invocationCallOrder[0]).toBeLessThan(exit.mock.invocationCallOrder[0] ?? 0);
  });

  it.each([
    "WATERFALL_KEYCLOAK_ADDRESS",
    "WATERFALL_FRONT_ADDRESS",
    "WATERFALL_FRONT_CLIENT_SECRET",
    "WATERFALL_REDIS_URL",
    "NEXT_SERVER_ACTIONS_ENCRYPTION_KEY",
  ])("stops without %s, naming it [WF-SEC-0010-A]", async (name) => {
    vi.stubEnv(name, undefined);
    await register();
    expectStopped(`${name} must be set: the front does not start without them`);
  });

  it("stops on an empty value as on an absent one, naming every variable missing [WF-SEC-0010-A]", async () => {
    vi.stubEnv("WATERFALL_FRONT_CLIENT_SECRET", "");
    vi.stubEnv("WATERFALL_REDIS_URL", undefined);
    await register();
    expectStopped("WATERFALL_FRONT_CLIENT_SECRET, WATERFALL_REDIS_URL must be set");
  });

  it("asks the development server for the session alone, not for the key of the server actions", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("NEXT_SERVER_ACTIONS_ENCRYPTION_KEY", undefined);
    await register();
    expectGoesOn();
    vi.stubEnv("WATERFALL_FRONT_CLIENT_SECRET", undefined);
    await register();
    expectStopped("WATERFALL_FRONT_CLIENT_SECRET must be set");
  });

  it.each([
    ["while next build builds and prerenders the pages", "NEXT_PHASE", PHASE_PRODUCTION_BUILD],
    ["on the edge runtime, which serves no page", "NEXT_RUNTIME", "edge"],
  ])("checks nothing %s, which the image is built without", async (_case, name, value) => {
    for (const variable of Object.keys(PRODUCTION)) {
      vi.stubEnv(variable, undefined);
    }
    vi.stubEnv(name, value);
    await register();
    expectGoesOn();
  });

  it("asks nothing of the fake back, which grants the session, in the harness that measures it", async () => {
    for (const variable of Object.keys(PRODUCTION)) {
      vi.stubEnv(variable, undefined);
    }
    vi.stubEnv("WATERFALL_AUTH", "mock");
    vi.stubEnv("WATERFALL_E2E", "1");
    await register();
    expectGoesOn();
  });

  it("stops on the fake back in production out of the harness, saying so", async () => {
    vi.stubEnv("WATERFALL_AUTH", "mock");
    await register();
    expectStopped("WATERFALL_AUTH=mock is refused in production");
  });
});
