// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The load of fifty users of the report of a version (US-2300, `make measure-version`): the
 * scenario k6 plays, in its service of the service platform (`load`, `compose.service.yaml`),
 * while a browser measures the operations of table 15 of §4.6.2 (`e2e/measure/version.measure.ts`).
 * TypeScript, which k6 strips of its types; typed and analysed with the front, whose lint and
 * types hold it, and whose tests try its draw and its requests (`draw.ts`, `screens.ts`).
 *
 * Each virtual user is an account of its own, which the preparation of the measure made by the
 * operations of the contract and signed in at the identity provider, outside the measure: the file
 * it writes (`WATERFALL_LOAD_FILE`) gives each its tokens, the task of the planning it writes, and
 * where it reads. A user then plays the journey of the grids on PRJ-001 for as long as the load
 * lasts: a gesture every ten seconds on average, nine readings for one entry, drawn reproducibly
 * from the seed of the file (`draw.ts`). It speaks to the API directly, inside the network of the
 * platform, as the server of Next does, with its own token; it renews the token by its refresh token
 * at the identity provider, on the back channel, a minute before it expires — five minutes is the
 * lifetime of a token, shorter than a measure —, as the session of a user of the front does.
 *
 * The load ends when the measure stops its container: k6 then writes its summary, beside the
 * file it read (`summary.json`): the gestures made, those refused — an entry on a revision the
 * measure has marked is refused, which is the marking's doing —, and those refused for want of a
 * valid token, which say that the load did not run as asked.
 */
import { sleep } from "k6";
import http from "k6/http";
import { Counter } from "k6/metrics";
import type { Options } from "k6/options";

import { type Gesture, gestures } from "./draw.ts";
import { ENTRIES, type Place, READINGS, taskPath, type Written } from "./screens.ts";

/** A user of the load, as the preparation hands it. */
interface Prepared {
  readonly access_token: string;
  readonly refresh_token: string;
  /** When the token expires, in milliseconds since the epoch. */
  readonly expires_at: number;
  readonly task: Written & { readonly lock_version: number };
}

/** What the preparation of the measure writes for the load. */
interface Preparation {
  readonly seed: number;
  readonly place: Place;
  readonly users: readonly Prepared[];
}

/** The answer of the identity provider to a refresh token. */
interface TokenAnswer {
  readonly access_token: string;
  readonly refresh_token: string;
  readonly expires_in: number;
}

/** The answer of `updateTaskFacet` to a stale counter, and the nodes it wrote otherwise. */
interface TaskAnswer {
  readonly nodes?: readonly { readonly node_id: string; readonly lock_version: number }[];
  readonly params?: { readonly expected_lock_version?: number };
}

const FILE = __ENV.WATERFALL_LOAD_FILE ?? "/load/load.json";
const API = __ENV.WATERFALL_LOAD_API ?? "http://api:8000/api/v1";
const TOKENS = `${__ENV.WATERFALL_LOAD_KEYCLOAK ?? "http://keycloak:8080/auth"}/realms/waterfall/protocol/openid-connect/token`;
const SECRET = __ENV.WATERFALL_FRONT_CLIENT_SECRET ?? "";
/** How long before it expires a token is renewed, in milliseconds. */
const RENEWED_BEFORE = 60_000;

const preparation = JSON.parse(open(FILE)) as Preparation;

export const options: Options = {
  scenarios: {
    users: {
      executor: "constant-vus",
      vus: preparation.users.length,
      // Past any measure: the measure stops the load itself.
      duration: "24h",
    },
  },
  // The load measures nothing: its summary counts, it does not time.
  summaryTrendStats: ["med", "max"],
};

const made = new Counter("gestures");
const refused = new Counter("gestures_refused");
const unauthorised = new Counter("gestures_unauthorised");

/** What a virtual user keeps from one gesture to the next. */
interface User {
  token: string;
  refresh: string;
  expiresAt: number;
  lockVersion: number;
  entries: number;
  readonly task: Written;
  readonly next: () => Gesture;
}

let own: User | undefined;

/** The user this virtual user plays, its gestures drawn from the seed and its number. */
function user(): User {
  if (own === undefined) {
    const prepared = preparation.users[__VU - 1];
    if (prepared === undefined) {
      throw new Error(`no account prepared for the virtual user ${String(__VU)}`);
    }
    own = {
      token: prepared.access_token,
      refresh: prepared.refresh_token,
      expiresAt: prepared.expires_at,
      lockVersion: prepared.task.lock_version,
      entries: 0,
      task: prepared.task,
      next: gestures(preparation.seed, __VU, {
        reads: READINGS.length,
        writes: ENTRIES.length,
      }),
    };
  }
  return own;
}

/** The headers of a request of the user: its token, renewed first if it is about to expire. */
function headers(playing: User): Record<string, string> {
  if (Date.now() >= playing.expiresAt - RENEWED_BEFORE) {
    const answer = http.post(
      TOKENS,
      {
        grant_type: "refresh_token",
        refresh_token: playing.refresh,
        client_id: "waterfall-front",
        client_secret: SECRET,
      },
      { tags: { name: "refreshToken" } },
    );
    if (answer.status === 200) {
      const renewed = answer.json() as unknown as TokenAnswer;
      playing.token = renewed.access_token;
      playing.refresh = renewed.refresh_token;
      playing.expiresAt = Date.now() + renewed.expires_in * 1000;
    }
  }
  return { Authorization: `Bearer ${playing.token}`, "Content-Type": "application/json" };
}

/** Count a gesture, and how it was answered. */
function counted(kind: string, name: string, status: number): void {
  const tags = { kind, name };
  made.add(1, tags);
  if (status === 401 || status === 403) {
    unauthorised.add(1, tags);
  }
  if (status < 200 || status >= 300) {
    refused.add(1, { ...tags, status: String(status) });
  }
}

/** A reading: the requests of its screen, one after the other, as the server of Next makes them. */
function read(playing: User, choice: number): void {
  const reading = READINGS[choice];
  if (reading === undefined) {
    return;
  }
  let status = 200;
  for (const asked of reading.asks(preparation.place)) {
    const answer = http.get(`${API}${asked.path}`, {
      headers: headers(playing),
      tags: { name: asked.name, gesture: reading.name },
    });
    if (answer.status !== 200) {
      status = answer.status;
      break;
    }
  }
  counted("read", reading.name, status);
}

/**
 * An entry on the task of the user, at the counter it last read; a counter another entry made
 * stale — a duration that redated the task — is taken from the refusal, and the entry sent again.
 */
function write(playing: User, choice: number): void {
  const entry = ENTRIES[choice];
  if (entry === undefined) {
    return;
  }
  playing.entries += 1;
  const send = () =>
    http.patch(
      `${API}${taskPath(preparation.place, playing.task)}`,
      JSON.stringify({
        ...entry.body(playing.task, playing.entries),
        lock_version: playing.lockVersion,
      }),
      { headers: headers(playing), tags: { name: "updateTaskFacet", gesture: entry.name } },
    );
  let answer = send();
  if (answer.status === 412) {
    const stale = answer.json() as unknown as TaskAnswer;
    playing.lockVersion = stale.params?.expected_lock_version ?? playing.lockVersion;
    answer = send();
  }
  if (answer.status === 200) {
    const written = answer.json() as unknown as TaskAnswer;
    const node = written.nodes?.find((one) => one.node_id === playing.task.node);
    playing.lockVersion = node?.lock_version ?? playing.lockVersion;
  }
  counted("write", entry.name, answer.status);
}

/** One gesture of a virtual user: its pause, then a reading or an entry. */
export default function gesture(): void {
  const playing = user();
  const next = playing.next();
  sleep(next.pause);
  if (next.kind === "read") {
    read(playing, next.choice);
  } else {
    write(playing, next.choice);
  }
}

/** The metrics of the summary of k6, as far as the load reads them. */
interface Summary {
  readonly metrics: Readonly<
    Record<string, { readonly values: Readonly<Record<string, number>> } | undefined>
  >;
}

/** The summary of the load, beside the file it read: what the measure writes in its report. */
export function handleSummary(data: Summary): Record<string, string> {
  const count = (name: string) => data.metrics[name]?.values.count ?? 0;
  const summary = {
    users: preparation.users.length,
    seed: preparation.seed,
    gestures: count("gestures"),
    refused: count("gestures_refused"),
    unauthorised: count("gestures_unauthorised"),
    requests: count("http_reqs"),
  };
  return { [FILE.replace(/[^/]*$/, "summary.json")]: `${JSON.stringify(summary, null, 2)}\n` };
}
