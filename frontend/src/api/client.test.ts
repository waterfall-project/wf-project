// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it, vi } from "vitest";

import { UNREACHABLE_DIGEST } from "@/components/system/failure";

import { API_PREFIX, createApiClient, Unreachable } from "./client";

/** A fetch that records the requests it receives, and answers an empty object. */
function recorder(): {
  send: (request: Request) => Promise<Response>;
  urls: string[];
  requests: Request[];
} {
  const requests: Request[] = [];
  const urls: string[] = [];
  const record = (request: Request): Promise<Response> => {
    requests.push(request);
    urls.push(request.url);
    return Promise.resolve(Response.json({}));
  };
  return { send: record, urls, requests };
}

describe("createApiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("calls an operation of the contract under the prefix of the contract", async () => {
    const { send, urls } = recorder();
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    await client.GET("/health");
    expect(urls).toEqual([`http://localhost:4010${API_PREFIX}/health`]);
  });

  it("writes a list of the query as one parameter, its values apart by commas, as the contract declares it", async () => {
    const { send, urls } = recorder();
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    await client.GET("/tasks", { params: { query: { status: ["queued", "running"] } } });
    expect(new URL(urls[0] ?? "").search).toBe("?status=queued,running");
  });

  it("sends the bearer token it is given, asked for at each request, none otherwise", async () => {
    const { send, requests } = recorder();
    const tokens = ["t0k", undefined, "t1k"];
    const bearer = () => Promise.resolve(tokens.shift());
    const client = createApiClient({ address: "http://localhost:4010", fetch: send, bearer });
    await client.GET("/health");
    await client.GET("/health");
    await client.GET("/health");
    const bare = createApiClient({ address: "http://localhost:4010", fetch: send });
    await bare.GET("/health");
    expect(requests.map((request) => request.headers.get("Authorization"))).toEqual([
      "Bearer t0k",
      null,
      "Bearer t1k",
      null,
    ]);
  });

  it("keeps the prefix when the address ends with a slash", async () => {
    const { send, urls } = recorder();
    const client = createApiClient({ address: "http://api.example/", fetch: send });
    await client.GET("/health");
    expect(urls).toEqual([`http://api.example${API_PREFIX}/health`]);
  });

  it("sends each method through the transport it is given, with its body and its answer", async () => {
    const { send, urls, requests } = recorder();
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    const { data, response } = await client.POST("/projects", { body: { label: "Poste" } });
    await client.DELETE("/me/sessions");

    expect(requests.map((request) => request.method)).toEqual(["POST", "DELETE"]);
    expect(urls).toEqual([
      `http://localhost:4010${API_PREFIX}/projects`,
      `http://localhost:4010${API_PREFIX}/me/sessions`,
    ]);
    expect(requests[0]?.headers.get("content-type")).toBe("application/json");
    expect(await requests[0]?.json()).toEqual({ label: "Poste" });
    // What the transport answered is what the caller reads.
    expect(response.status).toBe(200);
    expect(data).toEqual({});
  });

  it("marks the rejection of fetch as the API out of reach, and nothing else", async () => {
    const failure = new TypeError("fetch failed");
    const down = createApiClient({
      address: "http://api.invalid",
      fetch: () => Promise.reject(failure),
    });
    // Its digest is what the screen of failure receives of it in production.
    await expect(down.GET("/health")).rejects.toMatchObject({
      name: "Unreachable",
      cause: failure,
      digest: UNREACHABLE_DIGEST,
    });
    await expect(down.GET("/health")).rejects.toBeInstanceOf(Unreachable);

    const defect = new Error("a defect");
    const broken = createApiClient({
      address: "http://api.invalid",
      fetch: () => Promise.reject(defect),
    });
    await expect(broken.GET("/health")).rejects.toBe(defect);
  });

  it("uses the platform's fetch, looked up at each call, when none is given", async () => {
    const client = createApiClient({ address: "http://localhost:4010" });
    const urls: string[] = [];
    vi.stubGlobal("fetch", (request: Request) => {
      urls.push(request.url);
      return Promise.resolve(Response.json({ status: "ok" }));
    });
    const { data } = await client.GET("/health");
    expect(data).toEqual({ status: "ok" });
    expect(urls).toEqual([`http://localhost:4010${API_PREFIX}/health`]);

    // Replaced after the client was made, and failing as it does when the API is down.
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("fetch failed")));
    await expect(client.GET("/health")).rejects.toBeInstanceOf(Unreachable);
  });
});

/** A rejection of `fetch` as undici makes it, its cause carrying the code of the network. */
function rejection(code: string): TypeError {
  return new TypeError("fetch failed", { cause: Object.assign(new Error(code), { code }) });
}

/** A transport that fails as told, then answers an empty object; the requests it was sent. */
function failing(...failures: TypeError[]) {
  const sent: Request[] = [];
  const send = (request: Request): Promise<Response> => {
    sent.push(request);
    const failure = failures.shift();
    return failure === undefined ? Promise.resolve(Response.json({})) : Promise.reject(failure);
  };
  return { send, sent };
}

describe("a connection the API drops before answering (#1145)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it.each(["UND_ERR_SOCKET", "ECONNRESET", "EPIPE"])(
    "sends a read dropped by %s once more, and says so in the log of the server",
    async (code) => {
      const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
      const { send, sent } = failing(rejection(code));
      const client = createApiClient({ address: "http://localhost:4010", fetch: send });
      const { data } = await client.GET("/health");
      expect(data).toEqual({});
      expect(sent.map((request) => request.method)).toEqual(["GET", "GET"]);
      expect(warn).toHaveBeenCalledOnce();
      expect(warn.mock.calls[0]?.[0]).toBe(
        `The API dropped the connection of GET http://localhost:4010${API_PREFIX}/health`,
      );
    },
  );

  it("never sends a write again: the API may have done it before closing", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const dropped = rejection("UND_ERR_SOCKET");
    const { send, sent } = failing(dropped, dropped, dropped, dropped);
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    await expect(client.POST("/projects", { body: { label: "Poste" } })).rejects.toMatchObject({
      name: "Unreachable",
      cause: dropped,
    });
    await expect(client.DELETE("/me/sessions")).rejects.toBeInstanceOf(Unreachable);
    expect(sent.map((request) => request.method)).toEqual(["POST", "DELETE"]);
    expect(warn).not.toHaveBeenCalled();
  });

  it("is the API out of reach when the read sent once more is dropped too: never silence", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const second = rejection("ECONNRESET");
    const { send, sent } = failing(rejection("UND_ERR_SOCKET"), second);
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    await expect(client.GET("/health")).rejects.toMatchObject({
      name: "Unreachable",
      cause: second,
      digest: UNREACHABLE_DIGEST,
    });
    expect(sent).toHaveLength(2);
  });

  it("sends a read again for a dropped connection alone, not for an API that refuses it", async () => {
    const refused = rejection("ECONNREFUSED");
    const { send, sent } = failing(refused);
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    await expect(client.GET("/health")).rejects.toMatchObject({ cause: refused });
    expect(sent).toHaveLength(1);
  });

  it("asks for a connection of its own for each request when its connections are closed, and none otherwise", async () => {
    const { send, sent } = failing();
    const closed = createApiClient({
      address: "http://localhost:4010",
      fetch: send,
      connections: "closed",
    });
    await closed.GET("/health");
    await closed.POST("/projects", { body: { label: "Poste" } });
    const kept = createApiClient({ address: "http://localhost:4010", fetch: send });
    await kept.GET("/health");
    expect(sent.map((request) => request.headers.get("Connection"))).toEqual([
      "close",
      "close",
      null,
    ]);
  });
});

describe("the module of the client", () => {
  afterEach(() => {
    vi.doMock("server-only", () => ({}));
    vi.resetModules();
  });

  it("refuses to load outside the server of Next", async () => {
    vi.doUnmock("server-only");
    vi.resetModules();
    await expect(import("./client")).rejects.toThrow("Client Component");
  });
});
