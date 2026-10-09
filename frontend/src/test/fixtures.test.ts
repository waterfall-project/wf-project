// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, expectTypeOf, it } from "vitest";

import type { Problem } from "@/api/problem";

import { example, type FakeAnswers, fakeClient } from "./fixtures";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const USER = "01926f3a-7c00-7000-8000-000000000301";
const ROLE = "01926f3a-7c00-7000-8000-000000000401";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;
const MARK = "POST /projects/{project_id}/revisions/{revision_id}/mark";
const MARKING = { version_name: "V2", lock_version: 4 };

describe("example", () => {
  it("reads the value of a fixture of the contract", () => {
    expect(example("project")).toMatchObject({ project_id: PROJECT });
  });
});

describe("the answers of fakeClient", () => {
  it("are those the contract declares for the operation", () => {
    expectTypeOf<{ "GET /projects": "projects" }>().toExtend<FakeAnswers>();
    expectTypeOf<{ "GET /projects": "projects_empty" }>().toExtend<FakeAnswers>();
    expectTypeOf<{
      [MARK]: { example: "task_mark_queued"; status: 202 };
    }>().toExtend<FakeAnswers>();
    expectTypeOf<{ "GET /projects": typeof NOT_FOUND }>().toExtend<FakeAnswers>();
    expectTypeOf<{
      "DELETE /access-roles/{access_role_id}": { status: 204 };
    }>().toExtend<FakeAnswers>();
  });

  it("refuse an example the contract does not give the operation, or that status of it", () => {
    // A list of projects never receives a project alone, nor the list of another operation.
    expectTypeOf<{ "GET /projects": "project" }>().not.toExtend<FakeAnswers>();
    expectTypeOf<{ "GET /projects": "revisions" }>().not.toExtend<FakeAnswers>();
    expectTypeOf<{
      "GET /projects": { example: "project"; status: 200 };
    }>().not.toExtend<FakeAnswers>();
    // An operation the contract gives no fixture answers none: its creation, for one.
    expectTypeOf<{
      "POST /projects": { example: "project"; status: 201 };
    }>().not.toExtend<FakeAnswers>();
  });

  it("refuse a table keyed by any string, which names no operation", () => {
    // A `Record<string, string>` extends the answers — every key it has is optional there —,
    // and would serve any fixture to any operation: fakeClient takes none.
    expectTypeOf<Record<string, string>>().toExtend<FakeAnswers>();
    expectTypeOf<Parameters<typeof fakeClient<Record<string, string>>>[0]>().toBeNever();
    expectTypeOf<
      Parameters<typeof fakeClient<{ "GET /projects": "projects" }>>[0]
    >().toEqualTypeOf<{
      "GET /projects": "projects";
    }>();
  });

  it("refuse a status the operation does not declare", () => {
    expectTypeOf<{ "POST /file-uploads": { status: 204 } }>().not.toExtend<FakeAnswers>();
    expectTypeOf<{
      "GET /projects": { example: "projects"; status: 201 };
    }>().not.toExtend<FakeAnswers>();
    expectTypeOf<{
      "POST /projects": { problem: { code: "NOT_FOUND"; status: 404 } };
    }>().not.toExtend<FakeAnswers>();
  });

  it("refuse a status alone when it has a body, and a body when it has none", () => {
    expectTypeOf<{ "GET /projects": { status: 200 } }>().not.toExtend<FakeAnswers>();
    expectTypeOf<{
      "DELETE /access-roles/{access_role_id}": { example: "project"; status: 204 };
    }>().not.toExtend<FakeAnswers>();
  });

  it("refuse a name alone for a success other than 200, and a Problem for a success", () => {
    expectTypeOf<{ "POST /projects": "project" }>().not.toExtend<FakeAnswers>();
    expectTypeOf<{
      "GET /projects": { problem: { code: "NOT_FOUND"; status: 200 } };
    }>().not.toExtend<FakeAnswers>();
  });

  it("serve a body other than JSON as itself, never as a fixture", () => {
    expectTypeOf<{
      "GET /users/{user_id}/avatar": { body: Blob; type: "image/png"; status: 200 };
    }>().toExtend<FakeAnswers>();
    expectTypeOf<{
      "GET /metrics": { body: string; type: "text/plain"; status: 200 };
    }>().toExtend<FakeAnswers>();
    expectTypeOf<{ "GET /users/{user_id}/avatar": "project" }>().not.toExtend<FakeAnswers>();
    expectTypeOf<{
      "GET /users/{user_id}/avatar": { example: "project"; status: 200 };
    }>().not.toExtend<FakeAnswers>();
    expectTypeOf<{
      "GET /users/{user_id}/avatar": { body: string; type: "application/json"; status: 200 };
    }>().not.toExtend<FakeAnswers>();
    expectTypeOf<{
      "GET /projects": { body: string; type: "application/json"; status: 200 };
    }>().not.toExtend<FakeAnswers>();
  });

  it("refuse an operation the contract does not have", () => {
    expectTypeOf<{ "GET /me/avatar": { status: 204 } }>().not.toExtend<FakeAnswers>();
  });
});

describe("fakeClient", () => {
  it("answers a read with the named example, and records the call", async () => {
    const client = fakeClient({ "GET /projects/{project_id}": "project" });
    const params = { path: { project_id: PROJECT } };
    const { data, error } = await client.GET("/projects/{project_id}", { params });
    expect(data).toEqual(example("project"));
    expect(error).toBeUndefined();
    expect(client.calls).toEqual([
      {
        route: "GET /projects/{project_id}",
        path: `/projects/${PROJECT}`,
        query: new URLSearchParams(),
        body: undefined,
      },
    ]);
  });

  it("records the query the client serialized", async () => {
    const client = fakeClient({ "GET /projects/{project_id}/revisions": "revisions" });
    const params = { path: { project_id: PROJECT }, query: { limit: 20 } };
    await client.GET("/projects/{project_id}/revisions", { params });
    expect(client.calls[0]?.query.get("limit")).toBe("20");
  });

  it("answers a command with its status and records its body", async () => {
    const client = fakeClient({ [MARK]: { example: "task_mark_queued", status: 202 } });
    const params = { path: { project_id: PROJECT, revision_id: REVISION } };
    const { data, response } = await client.POST(
      "/projects/{project_id}/revisions/{revision_id}/mark",
      { params, body: MARKING },
    );
    expect(response.status).toBe(202);
    expect(data).toEqual(example("task_mark_queued"));
    expect(client.calls[0]).toMatchObject({ route: MARK, body: MARKING });
  });

  it("records the body of a partial update", async () => {
    const client = fakeClient({ "PATCH /me/preferences": "preferences_dark" });
    const body = { theme: "dark" } as const;
    const { data } = await client.PATCH("/me/preferences", { body });
    expect(data).toEqual(example("preferences_dark"));
    expect(client.calls[0]).toMatchObject({ path: "/me/preferences", body });
  });

  it("answers a refusal with the Problem as error, not data", async () => {
    // The deactivation of the last administrator, which the contract refuses (WF-ADM-0120).
    const problem = example("user_deactivation_refused") as Problem & { status: 409 };
    const client = fakeClient({ "PUT /users/{user_id}/activation": { problem } });
    const body = { is_active: false, lock_version: 1 };
    const params = { path: { user_id: USER } };
    const { data, error, response } = await client.PUT("/users/{user_id}/activation", {
      params,
      body,
    });
    expect(data).toBeUndefined();
    expect(error).toEqual(problem);
    expect(response.status).toBe(409);
    expect(response.headers.get("content-type")).toBe("application/problem+json");
    expect(client.calls[0]).toMatchObject({ route: "PUT /users/{user_id}/activation", body });
  });

  it("answers a deletion without a body", async () => {
    const client = fakeClient({ "DELETE /access-roles/{access_role_id}": { status: 204 } });
    const params = { path: { access_role_id: ROLE } };
    const { data, response } = await client.DELETE("/access-roles/{access_role_id}", { params });
    expect(response.status).toBe(204);
    expect(data).toBeUndefined();
    expect(client.calls[0]).toMatchObject({ path: `/access-roles/${ROLE}`, body: undefined });
  });

  it("serves a body other than JSON with its media type", async () => {
    const image = new Blob(["png"], { type: "image/png" });
    const client = fakeClient({
      "GET /users/{user_id}/avatar": { body: image, type: "image/png", status: 200 },
      "GET /metrics": { body: "waterfall_up 1", type: "text/plain", status: 200 },
    });
    const params = { path: { user_id: USER } };
    const avatar = await client.GET("/users/{user_id}/avatar", { params, parseAs: "blob" });
    expect(avatar.response.headers.get("content-type")).toBe("image/png");
    expect(await avatar.data?.text()).toBe("png");
    const metrics = await client.GET("/metrics", { parseAs: "text" });
    expect(metrics.data).toBe("waterfall_up 1");
  });

  it("goes through a sequence in turn, then repeats its last answer", async () => {
    const client = fakeClient({ "GET /projects": ["projects", NOT_FOUND] });
    const statuses = [];
    for (let call = 0; call < 3; call += 1) {
      statuses.push((await client.GET("/projects")).response.status);
    }
    expect(statuses).toEqual([200, 404, 404]);
    expect(client.calls).toHaveLength(3);
  });

  it("holds an answer until told, so that a later call is answered first", async () => {
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    const client = fakeClient(
      { "GET /projects": ["projects", NOT_FOUND] },
      { hold: (route, index) => (route === "GET /projects" && index === 0 ? held : undefined) },
    );
    const settled: number[] = [];
    const first = client.GET("/projects").then(({ response }) => settled.push(response.status));
    const second = client.GET("/projects").then(({ response }) => settled.push(response.status));
    await second;
    expect(settled).toEqual([404]);
    release();
    await first;
    expect(settled).toEqual([404, 200]);
    expect(client.calls).toHaveLength(2);
  });

  it("keeps a sequence per route", async () => {
    const client = fakeClient({
      "GET /projects": ["projects", NOT_FOUND],
      "GET /projects/{project_id}": "project",
    });
    await client.GET("/projects/{project_id}", { params: { path: { project_id: PROJECT } } });
    const { data } = await client.GET("/projects");
    expect(data).toEqual(example("projects"));
  });

  it("records calls made together in the order they were made", async () => {
    const client = fakeClient({
      [MARK]: { example: "task_mark_queued", status: 202 },
      "GET /projects": "projects",
    });
    const params = { path: { project_id: PROJECT, revision_id: REVISION } };
    await Promise.all([
      client.POST("/projects/{project_id}/revisions/{revision_id}/mark", {
        params,
        body: MARKING,
      }),
      client.GET("/projects"),
    ]);
    expect(client.calls.map((call) => call.route)).toEqual([MARK, "GET /projects"]);
    expect(client.calls[0]?.body).toEqual(MARKING);
  });

  it("answers a literal route by its own answer, never by one with a parameter", async () => {
    const client = fakeClient({
      "GET /projects/{project_id}/revisions/{revision_id}": NOT_FOUND,
      "GET /projects/{project_id}/risks/{risk_id}": NOT_FOUND,
    });
    const query = { from_revision_id: REVISION, to_revision_id: REVISION };
    await expect(
      client.GET("/projects/{project_id}/revisions/comparison", {
        params: { path: { project_id: PROJECT }, query },
      }),
    ).rejects.toThrow("fakeClient: no answer for GET /projects/{project_id}/revisions/comparison");
    await expect(
      client.GET("/projects/{project_id}/risks/matrix", {
        params: { path: { project_id: PROJECT } },
      }),
    ).rejects.toThrow("fakeClient: no answer for GET /projects/{project_id}/risks/matrix");
    expect(client.calls).toEqual([]);
  });

  it("does not answer a method its route was not given for", async () => {
    const client = fakeClient({ "GET /projects/{project_id}": "project" });
    const params = { path: { project_id: PROJECT } };
    await expect(
      client.PATCH("/projects/{project_id}", { params, body: { lock_version: 1 } }),
    ).rejects.toThrow("fakeClient: no answer for PATCH /projects/{project_id}");
    expect(client.calls).toEqual([]);
  });

  it("fails a call it has no answer for, an empty sequence included", async () => {
    const client = fakeClient({ "GET /projects": [] });
    await expect(client.GET("/projects")).rejects.toThrow(
      "fakeClient: no answer for GET /projects",
    );
    await expect(client.GET("/me")).rejects.toThrow("fakeClient: no answer for GET /me");
  });
});
