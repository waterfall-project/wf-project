// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { readContext } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { readAddress, readProject, readProjectContext, UnexpectedAnswer } from "./reading";

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

/** Read the context of an address. */
function read(address: string) {
  const [pathname = "", query = ""] = address.split("?");
  return readAddress(pathname, new URLSearchParams(query));
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
      edits: new Set(["edit_planning", "edit_estimate", "edit_remaining"]),
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
    await expect(read(LIFECYCLE)).rejects.toThrow(new UnexpectedAnswer("getProject", 401));
    request({ "GET /projects/{project_id}/subprojects": NOT_FOUND });
    const reading = await read(`${LIFECYCLE}?subproject_id=${SUBPROJECT}`);
    expect(reading).toMatchObject({ filters: [{ name: "subproject_id", subproject: undefined }] });
  });

  it("is not found at an address that is no screen of a project", async () => {
    expect(await read("/projects/a.b/lifecycle")).toBe("not_found");
    expect(await read("/system")).toBe("not_found");
  });

  it("is nothing when the API is out of reach, which the page says", async () => {
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    const context = readContext(REMAINING, new URLSearchParams());
    expect(context && (await readProjectContext(REMAINING, context))).toBeUndefined();
  });

  it("reads the project once for the request, however many ask", async () => {
    await Promise.all([read(REMAINING), readProject(PROJECT), read(LIFECYCLE)]);
    const projects = fake.calls.filter((call) => call.route === "GET /projects/{project_id}");
    expect(projects).toHaveLength(1);
  });
});
