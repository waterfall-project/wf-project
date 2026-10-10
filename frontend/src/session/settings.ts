// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the session of the front needs to know of the platform (US-0350): where Keycloak is, as
 * the browser reaches it and as the server of Next does, where the front itself is, the secret
 * of its client, and the Redis that keeps the sessions.
 *
 * Read from the environment when a session is first needed, never at the import: the mode of the
 * fake back (`WATERFALL_AUTH=mock`) and `next build` need none of them. A variable that is missing
 * fails the first sign-in, naming it.
 */
import "server-only";

/** The realm of Waterfall (`deploy/keycloak/realm/waterfall.yaml`). */
export const REALM = "waterfall";

/** The client of the front in the realm: confidential, authorization code with PKCE. */
export const FRONT_CLIENT = "waterfall-front";

/** The return address of the authorization code flow, under the address of the front. */
export const CALLBACK_PATH = "/auth/callback";

/** What the session of the front needs to know of the platform. */
export interface SessionSettings {
  /** Where the browser reaches the realm: the issuer of its tokens. */
  readonly realmAddress: string;
  /** Where the server of Next reaches it, for its tokens and its keys: the same by default. */
  readonly realmBackchannel: string;
  /** The return address the realm sends the code to, under the address of the front. */
  readonly callback: string;
  /** The secret of the client of the front. */
  readonly clientSecret: string;
}

/** The value of a variable the session cannot do without. */
function required(name: string): string {
  const value = process.env[name];
  if (value === undefined || value === "") {
    throw new Error(`${name} must be set: the session of the front needs it`);
  }
  return value;
}

/** The realm under an address of Keycloak (`https://<host>/auth`). */
function realmUnder(address: string): string {
  return `${address.replace(/\/+$/, "")}/realms/${REALM}`;
}

/** Read from the environment how the session reaches the realm. */
export function sessionSettings(): SessionSettings {
  const address = required("WATERFALL_KEYCLOAK_ADDRESS");
  const backchannel = process.env.WATERFALL_KEYCLOAK_BACKCHANNEL;
  const front = required("WATERFALL_FRONT_ADDRESS").replace(/\/+$/, "");
  return {
    realmAddress: realmUnder(address),
    realmBackchannel: realmUnder(
      backchannel === undefined || backchannel === "" ? address : backchannel,
    ),
    callback: `${front}${CALLBACK_PATH}`,
    clientSecret: required("WATERFALL_FRONT_CLIENT_SECRET"),
  };
}

/** The address of the Redis of the platform, where the sessions are kept. */
export function redisAddress(): string {
  return required("WATERFALL_REDIS_URL");
}
