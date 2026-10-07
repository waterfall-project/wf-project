// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient, Unreachable } from "@/api/client";
import { SignedOut, UnexpectedAnswer } from "@/api/problem";
import { CONTEXT_PARAMETERS, type ContextParameter, readContext } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { readAddress, readProject, readProjectContext } from "./reading";

const server = vi.hoisted(() => ({
  client: undefined as ApiClient | undefined,
  // What the cache of React holds for the request; a test is one request.
  cached: new Map<unknown, Map<string, unknown>>(),
}));

// The cache of React, as a server component sees it: a function it wraps runs once per
// request and per arguments. Outside the renderer of the server, React's own runs it at
// every call, and the reads of a request could not be counted.
vi.mock("react", async (original) => {
  const react = await original<typeof import("react")>();
  const cache =
    <A extends unknown[], R>(fn: (...args: A) => R) =>
    (...args: A): R => {
      const calls = server.cached.get(fn) ?? new Map<string, unknown>();
      server.cached.set(fn, calls);
      const key = JSON.stringify(args);
      if (!calls.has(key)) {
        calls.set(key, fn(...args));
      }
      return calls.get(key) as R;
    };
  return { ...react, cache };
});

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const ELSEWHERE = "01926f3a-7c00-7000-8000-000000000899";
const REMAINING = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
const LIFECYCLE = `/projects/${PROJECT}/lifecycle`;
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;

const ANSWERS: FakeAnswers = {
  "GET /projects/{project_id}": "project",
  "GET /projects/{project_id}/revisions/{revision_id}": "revision",
  "GET /projects/{project_id}/subprojects": "subprojects",
};

let fake: FakeClient;

/** A request answered by the examples of the contract. */
function request(answers: FakeAnswers = {}) {
  server.cached.clear();
  fake = fakeClient({ ...ANSWERS, ...answers });
  server.client = fake;
}

/** Read the context of an address, for a screen that reads every parameter of the context. */
function read(address: string, reads: readonly ContextParameter[] = CONTEXT_PARAMETERS) {
  const [pathname = "", query = ""] = address.split("?");
  return readAddress(pathname, new URLSearchParams(query), reads);
}

beforeEach(() => {
  request();
});

describe("what a screen of a project reads in", () => {
  it("is its project and its revision, open to modification when a draft", async () => {
    const reading = await read(REMAINING);
    expect(reading).toMatchObject({
      pathname: REMAINING,
      project: { label: "Modernisation du poste de commande" },
      revision: { revision_id: REVISION, status: "draft" },
      edits: new Set(["edit_planning", "edit_estimate", "edit_remaining", "edit_risks"]),
      readOnly: false,
      filters: [],
    });
  });

  it("is read only on a marked revision [WF-IHM-0020-A]", async () => {
    request({ "GET /projects/{project_id}/revisions/{revision_id}": "revision_marked" });
    expect(await read(REMAINING)).toMatchObject({
      readOnly: true,
      edits: new Set(),
      revision: { status: "marked" },
    });
  });

  it("is not read only for one who may enter the estimate alone, and names that command", async () => {
    request({ "GET /projects/{project_id}/revisions/{revision_id}": "revision_estimator" });
    const reading = await read(REMAINING);
    expect(reading).toMatchObject({ readOnly: false, edits: new Set(["edit_estimate"]) });
    expect(typeof reading === "object" && reading.edits.has("edit_planning")).toBe(false);
  });

  it("is the project alone on a function of the project that carries no revision", async () => {
    expect(await read(LIFECYCLE)).toMatchObject({
      revision: undefined,
      edits: new Set(),
      readOnly: false,
    });
    expect(fake.calls.map((call) => call.route)).toEqual(["GET /projects/{project_id}"]);
  });

  it("names the sub-project a filter restricts to, and keeps the date as the address gives it", async () => {
    const reading = await read(`${LIFECYCLE}?as_of=2026-05-31&subproject_id=${SUBPROJECT}`);
    expect(reading).toMatchObject({
      filters: [
        { name: "subproject_id", value: SUBPROJECT, subproject: { code: "SP-CMD" } },
        { name: "as_of", value: "2026-05-31" },
      ],
    });
  });

  it("holds the filters the screen reads alone, and reads no sub-project for a screen that reads none [WF-IHM-0020-A]", async () => {
    // Un filtre actif est visible sans avoir à ouvrir le panneau de filtres — on an address whose
    // parameters the screen reads; a workload or a lifecycle reads neither, and shows no chip (#302).
    const address = `${LIFECYCLE}?as_of=2026-05-31&subproject_id=${SUBPROJECT}`;
    expect(await read(address, [])).toMatchObject({ filters: [] });
    expect(fake.calls.map((call) => call.route)).toEqual(["GET /projects/{project_id}"]);
    expect(await read(address, ["as_of"])).toMatchObject({
      filters: [{ name: "as_of", value: "2026-05-31" }],
    });
    expect(fake.calls.some((call) => call.route === "GET /projects/{project_id}/subprojects")).toBe(
      false,
    );
    expect(await read(address, ["subproject_id"])).toMatchObject({
      filters: [{ name: "subproject_id", value: SUBPROJECT, subproject: { code: "SP-CMD" } }],
    });
  });

  it("reads no sub-project for what belongs to none, nor names one the project lacks", async () => {
    const unassigned = await read(`${LIFECYCLE}?subproject_id=unassigned`);
    expect(unassigned).toMatchObject({
      filters: [{ name: "subproject_id", value: "unassigned", subproject: undefined }],
    });
    expect(fake.calls).toHaveLength(1);
    const elsewhere = await read(`${LIFECYCLE}?subproject_id=${ELSEWHERE}`);
    expect(elsewhere).toMatchObject({
      filters: [{ name: "subproject_id", value: ELSEWHERE, subproject: undefined }],
    });
  });

  it("is not found when the API finds neither the project nor the revision", async () => {
    request({ "GET /projects/{project_id}": NOT_FOUND });
    expect(await read(LIFECYCLE)).toBe("not_found");
    request({ "GET /projects/{project_id}/revisions/{revision_id}": NOT_FOUND });
    expect(await read(REMAINING)).toBe("not_found");
  });

  it("throws on an answer other than not found: no session, or a failure of the server", async () => {
    request({
      "GET /projects/{project_id}": { problem: { code: "SESSION_REQUIRED", status: 401 } },
    });
    await expect(read(LIFECYCLE)).rejects.toBeInstanceOf(SignedOut);
    request({ "GET /projects/{project_id}/subprojects": NOT_FOUND });
    const reading = await read(`${LIFECYCLE}?subproject_id=${SUBPROJECT}`);
    expect(reading).toMatchObject({ filters: [{ name: "subproject_id", subproject: undefined }] });
  });

  it("is not found at an address that is no screen of a project", async () => {
    expect(await read("/projects/a.b/lifecycle")).toBe("not_found");
    expect(await read("/system")).toBe("not_found");
  });

  it("throws the API out of reach, which the screen of failure announces", async () => {
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    const context = readContext(REMAINING, new URLSearchParams());
    await expect(
      context && readProjectContext(REMAINING, context, CONTEXT_PARAMETERS),
    ).rejects.toBeInstanceOf(Unreachable);
  });

  it.each([502, 503, 504])(
    "throws the API out of reach when a gateway answers %i without the envelope",
    async (status) => {
      server.cached.clear();
      server.client = createApiClient({
        address: "http://gateway.invalid",
        fetch: () =>
          Promise.resolve(
            new Response("<html>Bad gateway</html>", {
              status,
              headers: { "content-type": "text/html" },
            }),
          ),
      });
      const search = new URLSearchParams({ subproject_id: SUBPROJECT });
      const context = readContext(REMAINING, search);
      await expect(
        context && readProjectContext(REMAINING, context, CONTEXT_PARAMETERS),
      ).rejects.toBeInstanceOf(Unreachable);
    },
  );

  it("still refuses a failure of the service the API tells in its envelope, by its correlation identifier", async () => {
    server.cached.clear();
    server.client = createApiClient({
      address: "http://api.invalid",
      fetch: () =>
        Promise.resolve(
          Response.json(
            {
              code: "COMPONENT_UNAVAILABLE",
              status: 503,
              params: { component: "database" },
              correlation_id: "req-7f3a",
            },
            { status: 503, headers: { "content-type": "application/problem+json" } },
          ),
        ),
    });
    const context = readContext(LIFECYCLE, new URLSearchParams());
    const failure = context && readProjectContext(LIFECYCLE, context, CONTEXT_PARAMETERS);
    await expect(failure).rejects.toBeInstanceOf(UnexpectedAnswer);
    await expect(failure).rejects.toMatchObject({
      status: 503,
      digest: "WATERFALL_CORRELATION;req-7f3a",
    });
  });

  it("reads the project once for the request, however many ask", async () => {
    await Promise.all([read(REMAINING), readProject(PROJECT), read(LIFECYCLE)]);
    const projects = fake.calls.filter((call) => call.route === "GET /projects/{project_id}");
    expect(projects).toHaveLength(1);
  });
});
