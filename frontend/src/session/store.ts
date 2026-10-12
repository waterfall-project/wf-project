// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sessions of the front, in Redis (US-0350, WF-ARC-0090): the one place where the tokens of a
 * person live, under the opaque identifier the browser holds in its cookie, and nothing a sign-in
 * cannot rebuild.
 *
 * - a sign-in under way, by the `state` of its request: the PKCE verifier, the nonce and the
 *   screen aimed at, fifteen minutes at most, taken once;
 * - the sign-out of a session the front lost, armed by the server action of the sign-out under a
 *   ticket drawn at random and bound to the cookie of the browser that asked for it, which
 *   `/login` takes once, for that cookie only, a minute at most (#689): a link of another site,
 *   or a ticket another armed, cannot sign anyone out;
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

import { randomBytes } from "node:crypto";

import {
  ClientClosedError,
  ClientOfflineError,
  ConnectionTimeoutError,
  createClient,
  ReconnectStrategyError,
  SocketClosedUnexpectedlyError,
  SocketTimeoutError,
} from "@redis/client";

import { LOST_CONNECTION, UNMADE_CONNECTION } from "./network";
import { redisAddress } from "./settings";

/** How long a sign-in may take, from the request to the return: fifteen minutes, in seconds. */
export const SIGN_IN_LIFETIME = 15 * 60;

/** How long an armed sign-out waits for the browser to load the sign-in: a minute, in seconds. */
export const SIGN_OUT_LIFETIME = 60;

/** A sign-in under way: what the return checks, and where it leads. */
export interface SignIn {
  /** The PKCE verifier of the request (S256). */
  readonly verifier: string;
  /** The nonce the ID token must carry back. */
  readonly nonce: string;
  /** The screen aimed at, a path of this front with its query (`returnTarget`). */
  readonly target: string;
  /**
   * Whether the sign-in is the sign-out of a session the front lost (#689): silent, it obtains a
   * token only to close the sessions of the account, on all its workstations.
   */
  readonly signOut: boolean;
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
const SIGN_OUT = "wf:sign-out:";
const SESSION = "wf:session:";
const ACCOUNT = "wf:account:";
const REFRESH = "wf:refresh:";

// Deletes a key only if it still holds the value given: an expired lock taken by another is theirs,
// and a ticket of the sign-out is taken by the browser it is bound to only.
const DELETE_HELD =
  'if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) end return 0';

// Deletes the sessions of an account and its index at once: a session filed meanwhile is either
// closed with the others, or filed after them, never left out of an index already deleted.
const FORGET_ACCOUNT = `
local ids = redis.call("smembers", KEYS[1])
for _, id in ipairs(ids) do redis.call("del", ARGV[1] .. id) end
return redis.call("del", KEYS[1])`;

/** How many times a lost connection is tried again, a tenth of a second apart, before it fails. */
const RECONNECTIONS = 5;

/** Connect to the Redis of the platform, at its address. */
function connect(address: string) {
  const client = createClient({
    url: address,
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
function reconnect(address: string): Promise<Redis> {
  const attempt: Promise<Redis> = connect(address).catch((error: unknown) => {
    if (connection === attempt) {
      connection = undefined;
    }
    throw error;
  });
  connection = attempt;
  return attempt;
}

/**
 * The client of the Redis of the platform at its address, connected at its first use, and again
 * once lost.
 */
async function redis(address: string): Promise<Redis> {
  const current = connection ?? reconnect(address);
  const client = await current;
  if (client.isOpen) {
    return client;
  }
  return connection === current ? reconnect(address) : (connection ?? reconnect(address));
}

/** The failures of the client that say Redis out of reach, rather than a defect. */
const CONNECTION_FAILURES = [
  ConnectionTimeoutError,
  ClientClosedError,
  ClientOfflineError,
  SocketClosedUnexpectedlyError,
  SocketTimeoutError,
  ReconnectStrategyError,
];

/**
 * The errors of the system that say the network failed: a connection not made, or lost once made —
 * a command in flight fails with the error of its socket, as it is.
 */
const NETWORK_FAILURES: ReadonlySet<unknown> = new Set([...UNMADE_CONNECTION, ...LOST_CONNECTION]);

/** How deep the causes of an error are looked into: a chain that loops ends there. */
const CAUSES = 8;

/**
 * Whether an error says Redis out of reach: a failure of the connection of the client, or an error
 * of the network — the error itself, one of its causes, or one of the errors it gathers (Node tries
 * each address of a host, and gathers their refusals). Anything else — a variable missing, an
 * address badly written, a defect — is not, and is thrown as it is.
 */
export function unreached(error: unknown, depth = 0): boolean {
  if (!(error instanceof Error) || depth > CAUSES) {
    return false;
  }
  if (CONNECTION_FAILURES.some((failure) => error instanceof failure)) {
    return true;
  }
  if ("code" in error && NETWORK_FAILURES.has(error.code)) {
    return true;
  }
  const gathered = error instanceof AggregateError ? (error.errors as unknown[]) : [];
  return [error.cause, ...gathered].some((inner) => unreached(inner, depth + 1));
}

/**
 * Redis could not be reached — a connection refused, lost, or not made in time —: nothing was read,
 * and nothing written but, perhaps, a write in flight when the connection was lost. A refusal of
 * Redis itself, an answer, is not this, but a defect; nor is an address missing or badly written.
 */
export class StoreUnreachable extends Error {
  /** The failure of the client, kept as the cause. */
  constructor(cause: unknown) {
    super("the sessions of the front cannot reach Redis", { cause });
    this.name = "StoreUnreachable";
  }
}

/**
 * Run commands on Redis, the failure to reach it marked as such (`StoreUnreachable`), and only it:
 * its address read first, a variable missing fails naming it.
 */
async function reaching<T>(commands: (client: Redis) => Promise<T>): Promise<T> {
  const address = redisAddress();
  try {
    return await commands(await redis(address));
  } catch (error) {
    throw unreached(error) ? new StoreUnreachable(error) : error;
  }
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
  await reaching((client) =>
    client.set(`${SIGN_IN}${state}`, JSON.stringify(signIn), {
      expiration: { type: "EX", value: SIGN_IN_LIFETIME },
    }),
  );
}

/** Take a sign-in under way by its state: once, and never after fifteen minutes. */
export async function takeSignIn(state: string): Promise<SignIn | undefined> {
  const text = await reaching((client) => client.getDel(`${SIGN_IN}${state}`));
  return text === null ? undefined : (JSON.parse(text) as SignIn);
}

/**
 * Arm the sign-out of a session the front lost: the ticket, drawn at random, that `/login` takes
 * once to sign in silently and close the sessions of the account (#689), for a minute at most —
 * bound to the identifier the cookie of the browser holds, so that only this browser may take it.
 */
export async function armSignOut(session: string): Promise<string> {
  const ticket = randomBytes(32).toString("base64url");
  await reaching((client) =>
    client.set(`${SIGN_OUT}${ticket}`, session, {
      expiration: { type: "EX", value: SIGN_OUT_LIFETIME },
    }),
  );
  return ticket;
}

/**
 * Take an armed sign-out by its ticket, for the identifier the cookie of the browser holds: once,
 * never after its minute, and only by the browser it is bound to — another leaves it in place.
 */
export async function takeSignOut(ticket: string, session: string): Promise<boolean> {
  const taken = await reaching((client) =>
    client.eval(DELETE_HELD, { keys: [`${SIGN_OUT}${ticket}`], arguments: [session] }),
  );
  return taken === 1;
}

/** Open a session for as long as Keycloak keeps it, in seconds, filed under its account. */
export async function openSession(id: string, session: FrontSession, lifetime: number) {
  const account = `${ACCOUNT}${session.subject}`;
  await reaching((client) =>
    client
      .multi()
      .set(`${SESSION}${id}`, JSON.stringify(session), {
        expiration: { type: "EX", value: lifetime },
      })
      .sAdd(account, id)
      // The index lives as long as the longest of its sessions.
      .expire(account, lifetime, "NX")
      .expire(account, lifetime, "GT")
      .exec(),
  );
}

/** The session of an identifier, if it lives. */
export async function readSession(id: string): Promise<FrontSession | undefined> {
  const text = await reaching((client) => client.get(`${SESSION}${id}`));
  return text === null ? undefined : (JSON.parse(text) as FrontSession);
}

/**
 * Keep the tokens a refresh gave, for as long as Keycloak keeps the session — only if the session
 * still lives: one the back channel closed during the refresh stays closed.
 */
export async function renewSession(id: string, session: FrontSession, lifetime: number) {
  await reaching(async (client) => {
    await client.set(`${SESSION}${id}`, JSON.stringify(session), {
      expiration: { type: "EX", value: lifetime },
      condition: "XX",
    });
    await client.expire(`${ACCOUNT}${session.subject}`, lifetime, "GT");
  });
}

/** Close a session. */
export async function forgetSession(id: string): Promise<void> {
  await reaching((client) => client.del(`${SESSION}${id}`));
}

/** Close every session of an account: on all its workstations (WF-SEC-0020). */
export async function forgetAccount(subject: string): Promise<void> {
  await reaching((client) =>
    client.eval(FORGET_ACCOUNT, { keys: [`${ACCOUNT}${subject}`], arguments: [SESSION] }),
  );
}

/** Take the lock of the refresh of a session for a while, in milliseconds, unless another holds it. */
export async function holdRefresh(id: string, holder: string, lifetime: number): Promise<boolean> {
  const taken = await reaching((client) =>
    client.set(`${REFRESH}${id}`, holder, {
      expiration: { type: "PX", value: lifetime },
      condition: "NX",
    }),
  );
  return taken !== null;
}

/** Give the lock of the refresh of a session back, if its holder still holds it. */
export async function releaseRefresh(id: string, holder: string): Promise<void> {
  await reaching((client) =>
    client.eval(DELETE_HELD, { keys: [`${REFRESH}${id}`], arguments: [holder] }),
  );
}
