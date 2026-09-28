// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example, fakeClient } from "./fixtures";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const USER = "01926f3a-7c00-7000-8000-000000000301";
const ROLE = "01926f3a-7c00-7000-8000-000000000401";

describe("example", () => {
  it("reads the value of a fixture of the contract", () => {
    expect(example("project")).toMatchObject({ project_id: PROJECT });
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

  it("answers a creation with its status and records its body", async () => {
    const client = fakeClient({ "POST /projects": { example: "project", status: 201 } });
    const body = { label: "Modernisation du poste de commande" };
    const { data, response } = await client.POST("/projects", { body });
    expect(response.status).toBe(201);
    expect(data).toEqual(example("project"));
    expect(client.calls[0]).toMatchObject({ route: "POST /projects", body });
  });

  it("records the body of a partial update", async () => {
    const client = fakeClient({ "PATCH /projects/{project_id}": "project" });
    const body = { label: "Poste de commande", lock_version: 3 };
    await client.PATCH("/projects/{project_id}", {
      params: { path: { project_id: PROJECT } },
      body,
    });
    expect(client.calls[0]).toMatchObject({ path: `/projects/${PROJECT}`, body });
  });

  it("answers a refusal with the Problem as error, not data", async () => {
    const problem = { code: "LAST_ADMINISTRATOR", status: 409 } as const;
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

  it("goes through a sequence in turn, then repeats its last answer", async () => {
    const notFound = { problem: { code: "NOT_FOUND", status: 404 } } as const;
    const client = fakeClient({ "GET /projects": ["projects", notFound] });
    const statuses = [];
    for (let call = 0; call < 3; call += 1) {
      statuses.push((await client.GET("/projects")).response.status);
    }
    expect(statuses).toEqual([200, 404, 404]);
    expect(client.calls).toHaveLength(3);
  });

  it("keeps a sequence per route", async () => {
    const client = fakeClient({
      "GET /projects": ["projects", { status: 204 }],
      "GET /projects/{project_id}": "project",
    });
    await client.GET("/projects/{project_id}", { params: { path: { project_id: PROJECT } } });
    const { data } = await client.GET("/projects");
    expect(data).toEqual(example("projects"));
  });

  it("prefers the literal route to the one with a parameter", async () => {
    const client = fakeClient({
      "GET /projects/{project_id}/revisions/{revision_id}": { status: 204 },
      "GET /projects/{project_id}/revisions/comparison": { status: 204 },
    });
    const query = { from_revision_id: REVISION, to_revision_id: REVISION };
    const params = { path: { project_id: PROJECT }, query };
    await client.GET("/projects/{project_id}/revisions/comparison", { params });
    expect(client.calls[0]?.route).toBe("GET /projects/{project_id}/revisions/comparison");
  });

  it("does not answer a method its route was not given for", async () => {
    const client = fakeClient({ "GET /projects/{project_id}": "project" });
    const params = { path: { project_id: PROJECT } };
    await expect(
      client.PATCH("/projects/{project_id}", { params, body: { lock_version: 1 } }),
    ).rejects.toThrow(`fakeClient: no answer for PATCH /projects/${PROJECT}`);
    expect(client.calls).toEqual([]);
  });

  it("fails a call it has no answer for, an empty sequence included", async () => {
    const client = fakeClient({ "GET /projects": [] });
    await expect(client.GET("/projects")).rejects.toThrow(
      "fakeClient: no answer for GET /projects",
    );
    await expect(client.GET("/me")).rejects.toThrow("fakeClient: no answer for GET /me");
  });

  it("ignores a key that names no route", async () => {
    const answers = { "GET /projects": "projects", witness: "project" };
    const client = fakeClient(answers);
    const { data } = await client.GET("/projects");
    expect(data).toEqual(example("projects"));
  });

  it("records a multipart body as a form", async () => {
    const client = fakeClient({ "POST /file-uploads": { status: 204 } });
    const form = new FormData();
    form.append("file", new Blob(["a;b"], { type: "text/csv" }), "costs.csv");
    await client.POST("/file-uploads", {
      body: { file: "costs.csv" },
      bodySerializer: () => form,
    });
    const body = client.calls[0]?.body;
    expect(body).toBeInstanceOf(FormData);
    expect(body instanceof FormData ? body.get("file") : null).toBeInstanceOf(File);
  });

  it("records another body as a blob", async () => {
    const client = fakeClient({ "PUT /me/avatar": { status: 204 } });
    await client.PUT("/me/avatar", {
      body: "png",
      bodySerializer: (body: string) => new Blob([body], { type: "image/png" }),
      headers: { "content-type": "image/png" },
    });
    const body = client.calls[0]?.body;
    expect(body).toBeInstanceOf(Blob);
    expect(body instanceof Blob ? await body.text() : null).toBe("png");
  });
});
