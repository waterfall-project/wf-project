// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the server of the front checks once, as it starts (#825, WF-SEC-0010): a front started
 * without one of its secrets would answer its probe, healthy to all appearances, and fail at the
 * first sign-in only. It stops instead, with the code 1, naming every variable that is missing.
 *
 * Out of the mode of the fake back (`WATERFALL_AUTH=mock`), which is refused here in production as
 * it is at a request (`src/api/server.ts`): the variables of the session (`SESSION_VARIABLES`),
 * and, in production, the address of the API, without which the front would call the fake back of
 * development (`src/api/server.ts`), and the key of the server actions, which Next reads before the
 * one `next build` wrote into the image (`frontend/Dockerfile`), the same for every start and every
 * instance.
 * `next build` checks nothing: the image is built without any of them (`src/instrumentation.ts`).
 *
 * It stops too on a way of holding the connections to the API it does not know
 * (`WATERFALL_API_CONNECTIONS`, `apiConnections`) — a typing error would otherwise answer every
 * request with an error —, and writes once, as a warning, that each request opens a connection of
 * its own when it is `closed` out of the harness of the fake back (`WATERFALL_E2E`): a setting of
 * the end-to-end harness, which its run against the service poses too, never of production (#1145).
 */
import "server-only";

import { API_CONNECTIONS, apiConnections, isMockAuthentication } from "@/api/server";
import { SESSION_VARIABLES, isSet } from "@/session/settings";

/** The key of the closures of the server actions, set at start in production. */
export const ACTIONS_KEY = "NEXT_SERVER_ACTIONS_ENCRYPTION_KEY";

/** The address of the API, which development may leave to its fake back, never production. */
export const API_ADDRESS = "WATERFALL_API_ADDRESS";

/** The variables the server of the front does not start without, here and now. */
export function startVariables(): readonly string[] {
  if (isMockAuthentication()) {
    return [];
  }
  const production = process.env.NODE_ENV === "production";
  return production ? [...SESSION_VARIABLES, API_ADDRESS, ACTIONS_KEY] : SESSION_VARIABLES;
}

/**
 * Refuse to start without a variable the front needs: write the error, naming each variable that is
 * missing, then stop the process. The standalone server of Next writes an error `register` throws
 * and goes on serving (#825): the front stops itself instead.
 */
export function checkStart(): void {
  try {
    const missing = startVariables().filter((name) => !isSet(name));
    if (missing.length > 0) {
      throw new Error(`${missing.join(", ")} must be set: the front does not start without them`);
    }
    if (apiConnections() === "closed" && process.env.WATERFALL_E2E !== "1") {
      console.warn(
        `${API_CONNECTIONS}=closed: each request to the API opens a connection of its own, as the end-to-end harness asks — never in production`,
      );
    }
  } catch (error) {
    console.error(error);
    process.exit(1);
  }
}
