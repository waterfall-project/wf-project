// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { randomUUID } from "node:crypto";
import { connect, createServer, type Server } from "node:net";
import { inspect } from "node:util";

import { createClient, ErrorReply, ReconnectStrategyError } from "@redis/client";
import { describe, expect, it, vi } from "vitest";

import { withTestRedis } from "@/test/session";

import {
  armSignOut,
  closeStore,
  type FrontSession,
  forgetAccount,
  holdRefresh,
  openSession,
  readSession,
  releaseRefresh,
  renewSession,
  rememberSignIn,
  SIGN_IN_LIFETIME,
  SIGN_OUT_LIFETIME,
  StoreUnreachable,
  takeSignIn,
  takeSignOut,
  unreached,
} from "./store";

withTestRedis();

/** The time to live Redis gives a key, in seconds. */
async function ttl(key: string): Promise<number> {
  const client = await createClient({ url: process.env.WATERFALL_TEST_REDIS_URL ?? "" }).connect();
  try {
    return await client.ttl(key);
  } finally {
    await client.close();
  }
}

/** The address of the Redis of the tests, its user and password, or its database, changed. */
function testAddress(change: (address: URL) => void): string {
  const address = new URL(process.env.WATERFALL_TEST_REDIS_URL ?? "");
  change(address);
  return address.href;
}

/**
 * A door to the Redis of the tests, on a port of its own, that the test can shut: while it is shut,
 * a client that reconnects is refused, whatever the time it takes — the order between the loss of a
 * connection and its reconnection is the test's, never the load of the machine's.
 */
async function doorToRedis() {
  const target = new URL(process.env.WATERFALL_TEST_REDIS_URL ?? "");
  const server: Server = createServer((inbound) => {
    const outbound = connect({ host: target.hostname, port: Number(target.port) || 6379 });
    inbound.pipe(outbound);
    outbound.pipe(inbound);
    // Redis closing the connection closes the other end too, as it would without the door.
    outbound.on("close", () => inbound.destroy());
    inbound.on("close", () => outbound.destroy());
    outbound.on("error", () => undefined);
    inbound.on("error", () => undefined);
  });
  const open = (port: number) =>
    new Promise<void>((resolve, reject) => {
      server.once("error", reject);
      server.listen(port, "127.0.0.1", () => {
        server.off("error", reject);
        resolve();
      });
    });
  await open(0);
  const address = server.address();
  const port = typeof address === "object" && address !== null ? address.port : 0;
  return {
    port,
    /** Refuse new connections from now on; those made go on. */
    shut: () =>
      new Promise<void>((resolve) => {
        server.close(() => {
          resolve();
        });
      }),
    /** Accept connections again, at the same port. */
    reopen: () => open(port),
    /** Stop listening, if it still does. */
    dispose: () => {
      if (server.listening) {
        server.close();
      }
    },
  };
}

/** A session of an account, its access token good for five minutes. */
function sessionOf(subject: string): FrontSession {
  const id = randomUUID();
  return {
    accessToken: `a-${id}`,
    refreshToken: `r-${id}`,
    expiresAt: Date.now() + 300_000,
    subject,
  };
}

describe("the store of the sessions of the front", () => {
  it("keeps a sign-in under way fifteen minutes at most, and gives it once", async () => {
    const state = randomUUID();
    const signIn = { verifier: "v", nonce: "n", target: "/projects?sort_by=code", signOut: false };
    await rememberSignIn(state, signIn);
    const left = await ttl(`wf:sign-in:${state}`);
    expect(left).toBeGreaterThan(SIGN_IN_LIFETIME - 5);
    expect(left).toBeLessThanOrEqual(15 * 60);
    expect(await takeSignIn(state)).toEqual(signIn);
    expect(await takeSignIn(state)).toBeUndefined();
  });

  it("keeps the sign-out of a lost session a minute at most, bound to the cookie that armed it: another cookie leaves it in place, and it is taken once (#689)", async () => {
    const [mine, theirs] = [randomUUID(), randomUUID()];
    const ticket = await armSignOut(mine);
    expect(await ttl(`wf:sign-out:${ticket}`)).toBeGreaterThan(SIGN_OUT_LIFETIME - 5);
    expect(await ttl(`wf:sign-out:${ticket}`)).toBeLessThanOrEqual(60);
    expect(await takeSignOut(ticket, theirs)).toBe(false);
    expect(await takeSignOut(ticket, mine)).toBe(true);
    expect(await takeSignOut(ticket, mine)).toBe(false);
  });

  it("keeps a session as long as Keycloak does, and closes every session of an account, not another's", async () => {
    const [first, second, other] = [randomUUID(), randomUUID(), randomUUID()];
    const subject = randomUUID();
    const session = sessionOf(subject);
    await openSession(first, session, 7200);
    await openSession(second, sessionOf(subject), 600);
    await openSession(other, sessionOf(randomUUID()), 600);
    expect(await readSession(first)).toEqual(session);
    expect(await ttl(`wf:session:${first}`)).toBeGreaterThan(7190);
    // The index of the account lives as long as the longest of its sessions.
    expect(await ttl(`wf:account:${subject}`)).toBeGreaterThan(7190);

    await forgetAccount(subject);
    expect(await readSession(first)).toBeUndefined();
    expect(await readSession(second)).toBeUndefined();
    expect(await readSession(other)).toBeDefined();
  });

  it("renews a session that lives, and never brings back one closed meanwhile", async () => {
    const [living, closed] = [randomUUID(), randomUUID()];
    const subject = randomUUID();
    await openSession(living, sessionOf(subject), 60);
    const renewed = sessionOf(subject);
    await renewSession(living, renewed, 7200);
    expect(await readSession(living)).toEqual(renewed);
    expect(await ttl(`wf:session:${living}`)).toBeGreaterThan(7190);
    expect(await ttl(`wf:account:${subject}`)).toBeGreaterThan(7190);

    await renewSession(closed, sessionOf(subject), 7200);
    expect(await readSession(closed)).toBeUndefined();
  });

  it("lends the lock of a refresh to one holder at a time, given back by that holder only", async () => {
    const id = randomUUID();
    expect(await holdRefresh(id, "first", 10_000)).toBe(true);
    expect(await holdRefresh(id, "second", 10_000)).toBe(false);
    await releaseRefresh(id, "second");
    expect(await holdRefresh(id, "second", 10_000)).toBe(false);
    await releaseRefresh(id, "first");
    expect(await holdRefresh(id, "second", 10_000)).toBe(true);
  });

  it("fails at once while Redis is out of reach, rather than keep the request waiting, and connects once it is back", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const address = process.env.WATERFALL_REDIS_URL;
    await closeStore();
    // A port nobody listens on.
    process.env.WATERFALL_REDIS_URL = "redis://127.0.0.1:1/0";
    const started = Date.now();
    await expect(readSession(randomUUID())).rejects.toThrow();
    expect(Date.now() - started).toBeLessThan(3000);
    expect(error).toHaveBeenCalledWith(
      "The sessions of the front cannot reach Redis",
      expect.anything(),
    );
    process.env.WATERFALL_REDIS_URL = address;
    expect(await readSession(randomUUID())).toBeUndefined();
    error.mockRestore();
  });

  it("fails as Redis out of reach when the connection is lost once made, Redis killing it, and connects again after", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    // The store connects as a user of its own, whose connection only is killed, never another test's.
    const [user, password] = [`store-${randomUUID()}`, randomUUID()];
    const admin = await createClient({ url: process.env.WATERFALL_TEST_REDIS_URL ?? "" }).connect();
    await admin.aclSetUser(user, ["on", `>${password}`, "~*", "+@all"]);
    const door = await doorToRedis();
    await closeStore();
    vi.stubEnv(
      "WATERFALL_REDIS_URL",
      testAddress((address) =>
        Object.assign(address, {
          username: user,
          password,
          hostname: "127.0.0.1",
          port: door.port,
        }),
      ),
    );
    try {
      expect(await readSession(randomUUID())).toBeUndefined();
      // The door is shut before Redis kills the connection: the client that finds it lost is refused
      // when it reconnects, however late it comes, so the read below can only fail.
      const shut = door.shut();
      expect(await admin.clientKill({ filter: "USER", username: user })).toBe(1);
      await shut;
      await expect(readSession(randomUUID())).rejects.toBeInstanceOf(StoreUnreachable);
      await door.reopen();
      await vi.waitFor(async () => {
        expect(await readSession(randomUUID())).toBeUndefined();
      });
    } finally {
      await closeStore();
      door.dispose();
      vi.unstubAllEnvs();
      await admin.aclDelUser(user);
      await admin.close();
      error.mockRestore();
    }
  });

  it.each([
    [
      "a user it does not know",
      (address: URL) => Object.assign(address, { username: "nobody", password: "wrong" }),
    ],
    ["a database it does not have", (address: URL) => Object.assign(address, { pathname: "/99" })],
  ])(
    "fails as a defect, never as Redis out of reach, when Redis refuses the connection: %s",
    async (_, change) => {
      const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
      await closeStore();
      vi.stubEnv("WATERFALL_REDIS_URL", testAddress(change));
      try {
        const failure: unknown = await readSession(randomUUID()).catch((thrown: unknown) => thrown);
        expect(failure).toBeInstanceOf(ReconnectStrategyError);
        expect(failure).not.toBeInstanceOf(StoreUnreachable);
      } finally {
        await closeStore();
        vi.unstubAllEnvs();
        error.mockRestore();
      }
    },
  );

  it("fails naming the variable, never quoting the address and its password, when the address of Redis is badly written [WF-SEC-0010-A] [WF-OBS-0020-A]", async () => {
    await closeStore();
    vi.stubEnv("WATERFALL_REDIS_URL", "redis://waterfall:s3cret-of-redis@[127.0.0.1:6379/0");
    try {
      const failure: unknown = await readSession(randomUUID()).catch((thrown: unknown) => thrown);
      expect(failure).toBeInstanceOf(Error);
      expect(inspect(failure)).toMatch(/WATERFALL_REDIS_URL/);
      expect(inspect(failure)).not.toMatch(/s3cret-of-redis/);
    } finally {
      await closeStore();
      vi.unstubAllEnvs();
    }
  });
});

describe("a failure to reach Redis", () => {
  /** An error of the system, as Node gives it for a socket. */
  function systemError(code: string): Error {
    return Object.assign(new Error(`write ${code}`), { code, syscall: "write" });
  }

  it.each(["EPIPE", "ENETUNREACH", "ENETDOWN", "EHOSTDOWN", "ECONNABORTED", "ENETRESET"])(
    "is told by the error of its socket, %s, alone, as a cause, or gathered with others",
    (code) => {
      const failure = systemError(code);
      expect(unreached(failure)).toBe(true);
      expect(unreached(new Error("the command failed", { cause: failure }))).toBe(true);
      expect(unreached(new AggregateError([new Error("another"), failure]))).toBe(true);
    },
  );

  it("is told by the last attempt of a connection given up, never by the giving up alone", () => {
    const refused = systemError("ECONNREFUSED");
    expect(unreached(new ReconnectStrategyError(refused, refused))).toBe(true);
    const wrong = new ErrorReply("WRONGPASS invalid username-password pair");
    expect(unreached(new ReconnectStrategyError(wrong, wrong))).toBe(false);
    expect(unreached(wrong)).toBe(false);
  });

  it("is not told by an error of another kind: a defect is thrown as it is", () => {
    expect(
      unreached(Object.assign(new TypeError("Invalid URL"), { code: "ERR_INVALID_URL" })),
    ).toBe(false);
    expect(unreached(new Error("a defect"))).toBe(false);
    const cert = Object.assign(new Error("Hostname/IP does not match certificate's altnames"), {
      code: "ERR_TLS_CERT_ALTNAME_INVALID",
    });
    expect(unreached(new ReconnectStrategyError(cert, cert))).toBe(false);
  });
});
