// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sessions of the front, in Redis (US-0350, WF-ARC-0090): the one place where the tokens of a
 * person live, under the opaque identifier the browser holds in its cookie, and nothing a sign-in
 * cannot rebuild.
 *
 * - a sign-in under way, by the `state` of its request: the PKCE verifier, the nonce and the
 *   screen aimed at, fifteen minutes at most, taken once;
 * - a session, by its identifier: the tokens, living as long as the session of Keycloak does —
 *   the lifetime of the refresh token, which each refresh gives anew;
 * - the sessions of an account, by its subject, which the back channel of Keycloak closes
 *   together;
 * - the lock of the refresh of a session, so that two requests never present the same refresh
 *   token, which the realm refuses the second time (`refreshTokenMaxReuse` 0).
 *
 * The one module that reaches Redis: ESLint refuses its client anywhere else.
 */
import "server-only";

import { createClient } from "@redis/client";

import { redisAddress } from "./settings";

/** How long a sign-in may take, from the request to the return: fifteen minutes, in seconds. */
export const SIGN_IN_LIFETIME = 15 * 60;

/** A sign-in under way: what the return checks, and where it leads. */
export interface SignIn {
  /** The PKCE verifier of the request (S256). */
  readonly verifier: string;
  /** The nonce the ID token must carry back. */
  readonly nonce: string;
  /** The screen aimed at, a path of this front with its query (`returnTarget`). */
  readonly target: string;
}

/** The tokens of a session, and whose they are. */
export interface FrontSession {
  readonly accessToken: string;
  readonly refreshToken: string;
  /** When the access token expires, in milliseconds since the epoch. */
  readonly expiresAt: number;
  /** The subject of the account, `sub`, by which the back channel names it. */
  readonly subject: string;
}

const SIGN_IN = "wf:sign-in:";
const SESSION = "wf:session:";
const ACCOUNT = "wf:account:";
const REFRESH = "wf:refresh:";

// Deletes the lock only if its holder still holds it: an expired lock taken by another is theirs.
const RELEASE =
  'if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) end return 0';

// Deletes the sessions of an account and its index at once: a session filed meanwhile is either
// closed with the others, or filed after them, never left out of an index already deleted.
const FORGET_ACCOUNT = `
local ids = redis.call("smembers", KEYS[1])
for _, id in ipairs(ids) do redis.call("del", ARGV[1] .. id) end
return redis.call("del", KEYS[1])`;

/** How many times a lost connection is tried again, a tenth of a second apart, before it fails. */
const RECONNECTIONS = 5;

/** Connect to the Redis of the platform. */
function connect() {
  const client = createClient({
    url: redisAddress(),
    // A command fails at once while Redis is out of reach, rather than wait in a queue; and a
    // connection that cannot be made fails, rather than keep the request waiting for ever.
    disableOfflineQueue: true,
    socket: {
      reconnectStrategy: (retries: number, cause: Error) => (retries < RECONNECTIONS ? 100 : cause),
    },
  });
  client.on("error", (error: unknown) => {
    console.error("The sessions of the front cannot reach Redis", error);
  });
  return client.connect();
}

type Redis = Awaited<ReturnType<typeof connect>>;

let connection: Promise<Redis> | undefined;

/** Connect anew, the connection forgotten if it fails: the next command tries again. */
function reconnect(): Promise<Redis> {
  const attempt: Promise<Redis> = connect().catch((error: unknown) => {
    if (connection === attempt) {
      connection = undefined;
    }
    throw error;
  });
  connection = attempt;
  return attempt;
}

/** The client of the Redis of the platform, connected at its first use, and again once lost. */
async function redis(): Promise<Redis> {
  const current = connection ?? reconnect();
  const client = await current;
  if (client.isOpen) {
    return client;
  }
  return connection === current ? reconnect() : (connection ?? reconnect());
}

/** Close the connection, if any: the end of the process, or of a test. */
export async function closeStore(): Promise<void> {
  const open = connection;
  connection = undefined;
  if (open !== undefined) {
    await (await open).close();
  }
}

/** Keep a sign-in under way, until its return or for fifteen minutes. */
export async function rememberSignIn(state: string, signIn: SignIn): Promise<void> {
  const client = await redis();
  await client.set(`${SIGN_IN}${state}`, JSON.stringify(signIn), {
    expiration: { type: "EX", value: SIGN_IN_LIFETIME },
  });
}

/** Take a sign-in under way by its state: once, and never after fifteen minutes. */
export async function takeSignIn(state: string): Promise<SignIn | undefined> {
  const text = await (await redis()).getDel(`${SIGN_IN}${state}`);
  return text === null ? undefined : (JSON.parse(text) as SignIn);
}

/** Open a session for as long as Keycloak keeps it, in seconds, filed under its account. */
export async function openSession(id: string, session: FrontSession, lifetime: number) {
  const client = await redis();
  const account = `${ACCOUNT}${session.subject}`;
  await client
    .multi()
    .set(`${SESSION}${id}`, JSON.stringify(session), {
      expiration: { type: "EX", value: lifetime },
    })
    .sAdd(account, id)
    // The index lives as long as the longest of its sessions.
    .expire(account, lifetime, "NX")
    .expire(account, lifetime, "GT")
    .exec();
}

/** The session of an identifier, if it lives. */
export async function readSession(id: string): Promise<FrontSession | undefined> {
  const text = await (await redis()).get(`${SESSION}${id}`);
  return text === null ? undefined : (JSON.parse(text) as FrontSession);
}

/**
 * Keep the tokens a refresh gave, for as long as Keycloak keeps the session — only if the session
 * still lives: one the back channel closed during the refresh stays closed.
 */
export async function renewSession(id: string, session: FrontSession, lifetime: number) {
  const client = await redis();
  await client.set(`${SESSION}${id}`, JSON.stringify(session), {
    expiration: { type: "EX", value: lifetime },
    condition: "XX",
  });
  await client.expire(`${ACCOUNT}${session.subject}`, lifetime, "GT");
}

/** Close a session. */
export async function forgetSession(id: string): Promise<void> {
  await (await redis()).del(`${SESSION}${id}`);
}

/** Close every session of an account: on all its workstations (WF-SEC-0020). */
export async function forgetAccount(subject: string): Promise<void> {
  await (
    await redis()
  ).eval(FORGET_ACCOUNT, {
    keys: [`${ACCOUNT}${subject}`],
    arguments: [SESSION],
  });
}

/** Take the lock of the refresh of a session for a while, in milliseconds, unless another holds it. */
export async function holdRefresh(id: string, holder: string, lifetime: number): Promise<boolean> {
  const taken = await (
    await redis()
  ).set(`${REFRESH}${id}`, holder, {
    expiration: { type: "PX", value: lifetime },
    condition: "NX",
  });
  return taken !== null;
}

/** Give the lock of the refresh of a session back, if its holder still holds it. */
export async function releaseRefresh(id: string, holder: string): Promise<void> {
  await (await redis()).eval(RELEASE, { keys: [`${REFRESH}${id}`], arguments: [holder] });
}
