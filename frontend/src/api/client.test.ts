// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it, vi } from "vitest";

import { UNREACHABLE_DIGEST } from "@/components/system/failure";

import { API_PREFIX, createApiClient, Dropped, Unreachable } from "./client";

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
        `The API dropped the connection of GET ${API_PREFIX}/health`,
      );
    },
  );

  it("sends a HEAD dropped once more, as any read", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { send, sent } = failing(rejection("UND_ERR_SOCKET"));
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    // The contract declares no HEAD: the request of a GET, made a HEAD as it leaves.
    client.use({ onRequest: ({ request }) => new Request(request, { method: "HEAD" }) });
    const { response } = await client.GET("/health");
    expect(response.status).toBe(200);
    expect(sent.map((request) => request.method)).toEqual(["HEAD", "HEAD"]);
  });

  it("writes the method and the path of a dropped read to the log, never its query", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { send } = failing(rejection("ECONNRESET"));
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    await client.GET("/tasks", { params: { query: { status: ["queued"] } } });
    expect(warn).toHaveBeenCalledOnce();
    // The whole of what is written: no query in it.
    expect(warn.mock.calls[0]?.[0]).toBe(
      `The API dropped the connection of GET ${API_PREFIX}/tasks`,
    );
  });

  it("never sends a write again: the API may have done it before closing", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const dropped = rejection("UND_ERR_SOCKET");
    const { send, sent } = failing(dropped, dropped, dropped, dropped);
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    await expect(client.POST("/projects", { body: { label: "Poste" } })).rejects.toMatchObject({
      name: "Dropped",
      cause: dropped,
    });
    await expect(client.DELETE("/me/sessions")).rejects.toBeInstanceOf(Dropped);
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

describe("a write whose connection is lost once it has left (US-2240)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it.each([
    "UND_ERR_SOCKET",
    "ECONNRESET",
    "EPIPE",
    "UND_ERR_HEADERS_TIMEOUT",
    "UND_ERR_BODY_TIMEOUT",
  ])(
    "marks a write lost by %s as dropped once sent, never sent again, told as the API out of reach to the screen of failure",
    async (code) => {
      const lost = rejection(code);
      const { send, sent } = failing(lost);
      const client = createApiClient({ address: "http://localhost:4010", fetch: send });
      const write = client.POST("/projects", { body: { label: "Poste" } });
      await expect(write).rejects.toBeInstanceOf(Dropped);
      // Still the API out of reach to whatever reads only that, the screen of failure included.
      await expect(write).rejects.toMatchObject({ cause: lost, digest: UNREACHABLE_DIGEST });
      expect(sent).toHaveLength(1);
    },
  );

  it("marks a PUT, a PATCH and a DELETE lost once sent as dropped, as well as a POST", async () => {
    const lost = () => rejection("UND_ERR_SOCKET");
    const { send, sent } = failing(lost(), lost(), lost());
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    const path = { project_id: "p", risk_id: "r" };
    await expect(
      client.PUT("/reference/org-nodes/{org_node_id}/activation", {
        params: { path: { org_node_id: "n" } },
        body: { is_active: false, lock_version: 1 },
      }),
    ).rejects.toBeInstanceOf(Dropped);
    await expect(
      client.PATCH("/projects/{project_id}/risks/{risk_id}", {
        params: { path },
        body: { label: "Retard", lock_version: 1 },
      }),
    ).rejects.toBeInstanceOf(Dropped);
    await expect(client.DELETE("/me/sessions")).rejects.toBeInstanceOf(Dropped);
    expect(sent.map((request) => request.method)).toEqual(["PUT", "PATCH", "DELETE"]);
  });

  it.each([
    "ECONNREFUSED",
    "ENOTFOUND",
    "EAI_AGAIN",
    "ENETUNREACH",
    "EHOSTUNREACH",
    "ENETDOWN",
    "EHOSTDOWN",
    "UND_ERR_CONNECT_TIMEOUT",
  ])(
    "marks a write that did not leave, refused by %s, as the API out of reach, not as dropped [WF-REV-0010-A]",
    async (code) => {
      const { send } = failing(rejection(code));
      const client = createApiClient({ address: "http://localhost:4010", fetch: send });
      const write = client.POST("/projects", { body: { label: "Poste" } });
      await expect(write).rejects.toBeInstanceOf(Unreachable);
      await expect(write).rejects.not.toBeInstanceOf(Dropped);
    },
  );

  // Codes undici gives, or the network does, that do not say the write never left: told as a
  // write that may have been done, never as one to do again.
  it.each([
    "UND_ERR_ABORTED",
    "UND_ERR_CLOSED",
    "UND_ERR_DESTROYED",
    "UND_ERR_RES_CONTENT_LENGTH_MISMATCH",
    "ETIMEDOUT",
    "ECONNABORTED",
  ])("marks a write rejected by %s, which does not say it never left, as dropped", async (code) => {
    const { send, sent } = failing(rejection(code));
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    await expect(client.POST("/projects", { body: { label: "Poste" } })).rejects.toBeInstanceOf(
      Dropped,
    );
    expect(sent).toHaveLength(1);
  });

  it("marks a write rejected without a code as dropped: nothing says it never left", async () => {
    const down = createApiClient({
      address: "http://localhost:4010",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    await expect(down.POST("/projects", { body: { label: "Poste" } })).rejects.toMatchObject({
      name: "Dropped",
      digest: UNREACHABLE_DIGEST,
    });
  });

  it("leaves a TypeError thrown before the request leaves, with no cause, as it is: a defect, not a write lost (WF-REV-0010-A)", async () => {
    const defect = new TypeError("Invalid URL");
    const down = createApiClient({
      address: "http://localhost:4010",
      fetch: () => Promise.reject(defect),
    });
    await expect(down.POST("/projects", { body: { label: "Poste" } })).rejects.toBe(defect);
  });

  it("marks a read rejected without a code as the API out of reach, not as dropped", async () => {
    const down = createApiClient({
      address: "http://localhost:4010",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    await expect(down.GET("/health")).rejects.not.toBeInstanceOf(Dropped);
  });

  it('leaves a TypeError of a read, with no cause and not saying "fetch failed", as it is: a defect, not the API out of reach (WF-REV-0010-A)', async () => {
    const defect = new TypeError("Invalid URL");
    const down = createApiClient({
      address: "http://localhost:4010",
      fetch: () => Promise.reject(defect),
    });
    await expect(down.GET("/health")).rejects.toBe(defect);
  });

  it("never marks a read as dropped: dropped twice, it is the API out of reach", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { send } = failing(rejection("UND_ERR_SOCKET"), rejection("UND_ERR_SOCKET"));
    const client = createApiClient({ address: "http://localhost:4010", fetch: send });
    const read = client.GET("/health");
    await expect(read).rejects.toBeInstanceOf(Unreachable);
    await expect(read).rejects.not.toBeInstanceOf(Dropped);
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
