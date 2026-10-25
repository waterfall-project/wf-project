// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The end-to-end harness (US-0080): Playwright starts the fake back and the front, then
 * plays the paths of `e2e/` in a browser. Each path cites the requirement it covers in its
 * title (WF-QUA-0010). From EP-03, the same paths run against the real service by pointing
 * `WATERFALL_API_ADDRESS` at it.
 *
 * Every path plays against the front built for production, the one users open (US-0590): one
 * `next start` serves the paths, the measure of the second of §4.6.2 (`opening.spec.ts`,
 * US-0110/L2) and the paths against the service. The development server rendered the pages of
 * four workers in series, past the five seconds of an assertion (#1262). The front is built first
 * as `make build-front` builds it, with no API to reach (#131), unless `E2E_BUILT=1` says it is
 * built already — the chain builds it once for all its parts (`ci.yml`). `E2E_DEV_SERVER=1`, on a
 * workstation only, plays the paths against `next dev` instead, which spares a build at each run
 * again: never the measure, which says how fast the users' front is, and never in the chain (`CI`),
 * where it fails the run, saying so.
 *
 * The harness always starts its own servers, on ports of its own — never those of `make dev`,
 * 3000 and 4010 —, and its fake back serves a variant of the contract written where `make dev`
 * does not read it: a path played against servers it did not start would judge another version
 * of the code, or another contract (#150). A port already taken fails the run, saying so. The
 * environment moves the ports, for two checkouts on one workstation. With `WATERFALL_API_ADDRESS`
 * set, the paths run against the API it names, and no fake back is started.
 *
 * The front opens a connection of its own for each request to the API, Prism here whatever the
 * API, which closes an idle one (#1145).
 *
 * The measure never fails the run on the second itself: it writes what it measured, and warns
 * when an opening overran it (`opening.spec.ts`).
 *
 * `E2E_PART` plays half of the harness, as the chain does on separate runners (#492): `paths`,
 * every path but the measure, which Playwright can then spread over runners (`--shard`) — the
 * measure, depending on all of them, would otherwise drag every one into each part —; `measure`,
 * the measure alone, a runner to itself. Unset, the whole harness: the paths, then the measure.
 *
 * `service` plays the paths of `e2e/service/` alone (US-0340), which the others leave out:
 * against the real service, through the proxy of the contract that `WATERFALL_API_ADDRESS` names
 * (`make e2e-service`), with the real authentication — no fixed token —, and the front listening
 * on every interface, so that Keycloak reaches its back channel from its container (#681). They
 * play in five projects: the installation first, whose administrator the bootstrap made, and whose
 * link serves once (US-0420); the paths, on several workers; those that change a setting of the
 * realm, which every account reads, one at a time once the others are done; the restoration of the
 * platform, which closes every session, after them, alone (US-0440); and last the guard of the run,
 * which reads the log of the proxy of the contract from the start of the run.
 */
import { randomBytes } from "node:crypto";

import { defineConfig, devices, type PlaywrightTestConfig } from "@playwright/test";

import { lastLogged } from "./e2e/service/proxy-log";

type Project = NonNullable<PlaywrightTestConfig["projects"]>[number];
type WebServer = Extract<
  NonNullable<PlaywrightTestConfig["webServer"]>,
  readonly unknown[]
>[number];

/** A port of the harness: the one the environment names, or its own; anything else refused. */
function port(variable: string, own: number): number {
  const named = process.env[variable];
  const chosen = named === undefined ? own : Number(named);
  if (!Number.isInteger(chosen) || chosen < 1 || chosen > 65_535) {
    throw new Error(`${variable} must be a port, a whole number from 1 to 65535: ${String(named)}`);
  }
  return chosen;
}

/** A switch of the harness: `1` sets it, unset or empty leaves it; anything else refused. */
function switchedOn(variable: string): boolean {
  const named = process.env[variable];
  if (named === undefined || named === "") {
    return false;
  }
  if (named !== "1") {
    throw new Error(`${variable} must be 1, or unset: ${named}`);
  }
  return true;
}

const API_PORT = port("E2E_API_PORT", 4110);
// The port Keycloak knows the back channel of the front at, against the service (`make e2e-service`).
const FRONT_PORT = port("E2E_FRONT_PORT", 3100);
// An API named by the environment is played against as it is: no fake back is started for it.
const NAMED_API = process.env.WATERFALL_API_ADDRESS;
const API = NAMED_API ?? `http://127.0.0.1:${String(API_PORT)}`;
const FRONT = `http://127.0.0.1:${String(FRONT_PORT)}`;
// An address where no API answers, which `make build-front` builds the front with (#131).
const NOWHERE = "http://127.0.0.1:9";
const onWorkstation = process.env.CI === undefined;
// Whether the front is built already, and whether the paths play against the development server.
const BUILT = switchedOn("E2E_BUILT");
const DEVELOPMENT_ASKED = switchedOn("E2E_DEV_SERVER");
if (DEVELOPMENT_ASKED && !onWorkstation) {
  throw new Error(
    "E2E_DEV_SERVER=1 plays the paths against next dev, on a workstation only: the chain (CI) plays them against the built front",
  );
}
// The front built for production refuses the fixed token of the fake back unless the harness says
// it is the harness (`WATERFALL_E2E`), which it says against the service too: the front then writes
// no warning of `closed` connections (#1265). Against an API the environment names, the real
// authentication stands; the front built for production does not start without the key of its
// server actions, which the run gives it unless the environment does.
const AUTHENTICATION =
  NAMED_API === undefined
    ? { WATERFALL_AUTH: "mock" }
    : {
        NEXT_SERVER_ACTIONS_ENCRYPTION_KEY:
          process.env.NEXT_SERVER_ACTIONS_ENCRYPTION_KEY ?? randomBytes(32).toString("base64"),
      };
// What the front of the harness is told: where the API is, and to open a connection of its own for
// each request — the API is Prism, the fake back or the proxy of the contract, which closes a
// connection idle for five seconds, which the front would otherwise send a request on
// (`Connections`, `src/api/client.ts`, #1145).
const FRONT_ENV = {
  WATERFALL_API_ADDRESS: API,
  WATERFALL_API_CONNECTIONS: "closed",
  WATERFALL_E2E: "1",
  ...AUTHENTICATION,
};
const PARTS = ["paths", "measure", "service"] as const;
type Part = (typeof PARTS)[number];

/** The part of the harness the environment names, or the whole of it; anything else refused. */
function part(): Part | undefined {
  const named = process.env.E2E_PART;
  if (named === undefined || named === "") {
    return undefined;
  }
  const chosen = PARTS.find((candidate) => candidate === named);
  if (chosen === undefined) {
    throw new Error(`E2E_PART must be one of ${PARTS.join(", ")}, or unset: ${named}`);
  }
  return chosen;
}

const PART = part();
const PLAYS_SERVICE = PART === "service";
const PLAYS_PATHS = PART === undefined || PART === "paths";
// The measure never plays against the development server: the whole harness asked of it leaves the
// measure out, and the measure asked alone plays against the built front.
const DEVELOPMENT = DEVELOPMENT_ASKED && PART !== "measure";
const PLAYS_MEASURE = (PART === undefined && !DEVELOPMENT) || PART === "measure";
if (PLAYS_SERVICE && NAMED_API === undefined) {
  throw new Error("E2E_PART=service plays against the service WATERFALL_API_ADDRESS names");
}
// From the root of the repository, where `make -C ..` runs; ignored by git.
const MOCK_SPEC = "frontend/.e2e/waterfall.mock.json";
const MEASURES = /opening\.spec\.ts$/;
// The paths against the real service, which need its platform: `make e2e-service` alone plays them.
const SERVICE_PATHS = /e2e\/service\/.+\.spec\.ts$/;
// The paths that change a setting of the realm for the time they run — a lifetime —, which every
// account of the realm reads: tagged, played alone.
const REALM_WIDE = /@realm-wide/;
// The paths that replace the whole platform — a restoration —, which closes every session: tagged,
// played alone, after all the others.
const PLATFORM_WIDE = /@platform-wide/;
// The moment the run started, which the workers inherit: the guard of the run reads the log of the
// proxy from it (`e2e/service/contract.ts`). The last line the proxy wrote before the run, on the
// clock of Docker that stamps its log, never the workstation's (`e2e/service/proxy-log.ts`). Kept
// by a worker, which loads this file again.
if (PLAYS_SERVICE) {
  process.env.E2E_SERVICE_STARTED ??= lastLogged();
}

/** The fake back, started on the port of the harness — unless the environment names an API. */
function fakeBack(): WebServer[] {
  if (NAMED_API !== undefined) {
    return [];
  }
  return [
    {
      command: `make -C .. mock MOCK_PORT=${String(API_PORT)} MOCK_SPEC=${MOCK_SPEC}`,
      url: `http://127.0.0.1:${String(API_PORT)}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      // Signal the whole process group: make and pnpm start the servers as children.
      gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
    },
  ];
}

/** The paths, in a French browser — unless the measure is played alone. */
function pathProjects(): Project[] {
  if (!PLAYS_PATHS) {
    return [];
  }
  return [
    {
      name: "chromium",
      testIgnore: [MEASURES, SERVICE_PATHS],
      use: { ...devices["Desktop Chrome"], locale: "fr-FR" },
    },
  ];
}

/** The paths against the real service, in a French browser — when they are the part played. */
function serviceProjects(): Project[] {
  if (!PLAYS_SERVICE) {
    return [];
  }
  // Keycloak's front end answers with a certificate of its own local authority (#680), which the
  // server of Next trusts by NODE_EXTRA_CA_CERTS, and the browser by this.
  const use = { ...devices["Desktop Chrome"], locale: "fr-FR", ignoreHTTPSErrors: true };
  return [
    {
      // The link of the bootstrap serves once: its path sets the password of the administrator,
      // through whom the others act.
      name: "installation",
      testMatch: /e2e\/service\/installation\.setup\.ts$/,
      teardown: "contract",
      use,
    },
    {
      // Each path signs in as an account of its own, or as one no other path closes the sessions
      // of: they share no session, and play on several workers (#730).
      name: "service",
      testMatch: SERVICE_PATHS,
      grepInvert: [REALM_WIDE, PLATFORM_WIDE],
      dependencies: ["installation"],
      use,
    },
    {
      // A setting of the realm changed would reach the paths beside: these play once the others are
      // done, one at a time.
      name: "realm",
      testMatch: SERVICE_PATHS,
      grep: REALM_WIDE,
      dependencies: ["installation", "service"],
      workers: 1,
      use,
    },
    {
      // A restoration replaces the whole platform and closes every session: it plays last, alone.
      name: "restoration",
      testMatch: SERVICE_PATHS,
      grep: PLATFORM_WIDE,
      dependencies: ["installation", "service", "realm"],
      workers: 1,
      use,
    },
    {
      name: "contract",
      testMatch: /e2e\/service\/contract\.teardown\.ts$/,
      use,
    },
  ];
}

/** The measure, against the front built for production — unless the paths are played alone. */
function measureProjects(): Project[] {
  if (!PLAYS_MEASURE) {
    return [];
  }
  return [
    {
      name: "measure",
      testMatch: MEASURES,
      // After all the other paths, so that the measure has the machine to itself; played
      // alone, it has a runner to itself.
      dependencies: PLAYS_PATHS ? ["chromium"] : [],
      // No trace: recording one would weigh on what is measured.
      use: { ...devices["Desktop Chrome"], locale: "fr-FR", trace: "off" },
    },
  ];
}

/**
 * The front every part plays against: built for production and started, or the development
 * server when `E2E_DEV_SERVER=1` asks for it.
 */
function front(): WebServer {
  // Against the service, on every interface: Keycloak posts to the back channel of the front from
  // its container, through the address of the workstation (`host.docker.internal`).
  const listening = `--hostname ${PLAYS_SERVICE ? "0.0.0.0" : "127.0.0.1"} --port ${String(FRONT_PORT)}`;
  // Built as `make build-front` builds it: with no API to reach, which the address of the API given
  // to the server is not while it builds (#131). The build writes `.next`, the development server
  // `.next/dev`: the two live side by side.
  const build = BUILT ? "" : `WATERFALL_API_ADDRESS=${NOWHERE} pnpm build && `;
  return {
    command: DEVELOPMENT ? `pnpm dev ${listening}` : `${build}pnpm start ${listening}`,
    url: FRONT,
    env: FRONT_ENV,
    reuseExistingServer: false,
    timeout: DEVELOPMENT || BUILT ? 120_000 : 300_000,
    // Signal the whole process group: make and pnpm start the servers as children.
    gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
  };
}

export default defineConfig({
  testDir: "e2e",
  forbidOnly: !onWorkstation,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: FRONT, trace: "retain-on-failure" },
  // A French browser by default, the language of the reference catalogue: a path that needs
  // another language sets its own (`test.use({ locale })`).
  projects: [...pathProjects(), ...serviceProjects(), ...measureProjects()],
  webServer: [...fakeBack(), front()],
});
