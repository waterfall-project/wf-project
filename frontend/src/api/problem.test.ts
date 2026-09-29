// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example, type FakeAnswer, fakeClient } from "@/test/fixtures";

import {
  failureOf,
  SESSION_REQUIRED_DIGEST,
  UNREACHABLE_DIGEST,
} from "@/components/system/failure";

import { createApiClient, Unreachable } from "./client";
import { decode, reach, readOrFail, SignedOut, UnexpectedAnswer } from "./problem";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const TASK = {
  project_id: PROJECT,
  revision_id: REVISION,
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
  node_id: "01926f3a-7c00-7000-8000-000000000401",
};
const TASK_ROUTE =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task";

/** Write the label of a task, answered by the fake back as the test says. */
function writeTask(answer: FakeAnswer<typeof TASK_ROUTE>) {
  const client = fakeClient({ [TASK_ROUTE]: answer });
  return decode(() =>
    client.PATCH(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task",
      { params: { path: TASK }, body: { label: "Études", lock_version: 3 } },
    ),
  );
}

/** A client whose every call is answered by the function given, in place of the network. */
function answering(fetch: () => Promise<Response>) {
  return createApiClient({ address: "http://api.invalid", fetch });
}

describe("the decoder of an answer of the API", () => {
  it("gives back the answer of a success", async () => {
    const client = fakeClient({ "PATCH /me/preferences": "preferences" });
    const outcome = await decode(() =>
      client.PATCH("/me/preferences", { body: { language: "en" } }),
    );
    expect(outcome).toEqual({ kind: "done", data: example("preferences") });
  });

  it("keeps a refusal as the API sent it, to be rendered by its code and parameters", async () => {
    const refusal = {
      code: "NOT_CONTRIBUTOR",
      status: 403,
      params: { missing_condition: "is_contributor" },
    } as const;
    expect(await writeTask({ problem: refusal })).toEqual({
      kind: "refused",
      problem: refusal,
      conflictingObjectId: null,
    });
  });

  it("offers to reload an object changed since it was read (412)", async () => {
    const stale = {
      code: "STALE_LOCK_VERSION",
      status: 412,
      params: { conflicting_object_id: TASK.node_id, expected_lock_version: 4 },
    } as const;
    expect(await writeTask({ problem: stale })).toEqual({
      kind: "stale",
      problem: stale,
      conflictingObjectId: TASK.node_id,
    });
  });

  it("explains a conflict with the state of an object, which it names (409)", async () => {
    const conflict = {
      code: "TASK_COMPLETED",
      status: 409,
      params: { conflicting_object_id: TASK.node_id },
    } as const;
    expect(await writeTask({ problem: conflict })).toMatchObject({
      kind: "conflict",
      conflictingObjectId: TASK.node_id,
    });
  });

  it("leads to the sign-in page when there is no session (401)", async () => {
    const client = fakeClient({
      "PATCH /me/preferences": { problem: { code: "SESSION_REQUIRED", status: 401 } },
    });
    const outcome = await decode(() =>
      client.PATCH("/me/preferences", { body: { theme: "dark" } }),
    );
    expect(outcome).toMatchObject({ kind: "signed_out", problem: { code: "SESSION_REQUIRED" } });
  });

  it("tells an API out of reach apart from any refusal", async () => {
    const client = answering(() => Promise.reject(new TypeError("fetch failed")));
    const outcome = await decode(() => client.PATCH("/me/preferences", { body: {} }));
    expect(outcome).toEqual({ kind: "unreachable" });
  });

  it("takes an answer without the envelope for the unexpected error of the service", async () => {
    const client = answering(() =>
      Promise.resolve(
        new Response("<html>Internal error</html>", {
          status: 500,
          headers: { "content-type": "text/html" },
        }),
      ),
    );
    const outcome = await decode(() => client.PATCH("/me/preferences", { body: {} }));
    expect(outcome).toEqual({
      kind: "refused",
      problem: { code: "INTERNAL_ERROR", status: 500 },
      conflictingObjectId: null,
    });
  });

  it.each([502, 503, 504])(
    "takes a gateway's %i without the envelope for the API out of reach",
    async (status) => {
      const client = answering(() =>
        Promise.resolve(
          new Response("<html>Bad gateway</html>", {
            status,
            headers: { "content-type": "text/html" },
          }),
        ),
      );
      const outcome = await decode(() => client.PATCH("/me/preferences", { body: {} }));
      expect(outcome).toEqual({ kind: "unreachable" });
    },
  );

  it("keeps the refusal of an unavailable component, which the API sends in its envelope", async () => {
    const unavailable = {
      code: "COMPONENT_UNAVAILABLE",
      status: 503,
      params: { component: "database" },
    };
    const client = answering(() =>
      Promise.resolve(
        Response.json(unavailable, {
          status: 503,
          headers: { "content-type": "application/problem+json" },
        }),
      ),
    );
    const outcome = await decode(() => client.PATCH("/me/preferences", { body: {} }));
    expect(outcome).toEqual({ kind: "refused", problem: unavailable, conflictingObjectId: null });
  });

  it("takes a code the catalogue does not know for the unexpected error of the service", async () => {
    const client = answering(() =>
      Promise.resolve(
        Response.json(
          { code: "A_CODE_OF_A_NEWER_SERVICE", status: 403 },
          { status: 403, headers: { "content-type": "application/problem+json" } },
        ),
      ),
    );
    const outcome = await decode(() => client.PATCH("/me/preferences", { body: {} }));
    expect(outcome).toEqual({
      kind: "refused",
      problem: { code: "INTERNAL_ERROR", status: 403 },
      conflictingObjectId: null,
    });
  });

  it("lets a TypeError thrown elsewhere than by fetch through", async () => {
    const client = answering(() => Promise.resolve(Response.json({})));
    client.use({
      onRequest() {
        throw new TypeError("a defect");
      },
    });
    await expect(decode(() => client.PATCH("/me/preferences", { body: {} }))).rejects.toThrow(
      "a defect",
    );
    await expect(reach(() => Promise.reject(new TypeError("a defect")))).rejects.toThrow(
      "a defect",
    );
  });

  it("lets a defect through rather than take it for an API out of reach", async () => {
    const client = answering(() => Promise.reject(new Error("a defect")));
    await expect(decode(() => client.PATCH("/me/preferences", { body: {} }))).rejects.toThrow(
      "a defect",
    );
  });
});

/** A failure of the service, in the envelope of the contract, with its correlation identifier. */
function failure(correlationId: string): Response {
  return Response.json(
    { code: "INTERNAL_ERROR", status: 500, correlation_id: correlationId },
    { status: 500, headers: { "content-type": "application/problem+json" } },
  );
}

describe("a read a screen cannot do without", () => {
  const readiness = (client: ReturnType<typeof answering>) =>
    readOrFail("getReferenceReadiness", () => client.GET("/reference/readiness"));

  it("gives the data of a success", async () => {
    const client = fakeClient({ "GET /reference/readiness": "reference_readiness" });
    expect(await readiness(client)).toEqual(example("reference_readiness"));
  });

  it("is not found on a 404: the object does not exist, or may not be read", async () => {
    const client = fakeClient({
      "GET /projects/{project_id}/revisions": { problem: { code: "NOT_FOUND", status: 404 } },
    });
    const read = readOrFail("listRevisions", () =>
      client.GET("/projects/{project_id}/revisions", {
        params: { path: { project_id: PROJECT } },
      }),
    );
    await expect(read).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });

  it("throws the API out of reach, marked so for the screen of failure, when fetch rejects", async () => {
    const read = readiness(answering(() => Promise.reject(new TypeError("fetch failed"))));
    await expect(read).rejects.toBeInstanceOf(Unreachable);
    await expect(read).rejects.toMatchObject({ digest: UNREACHABLE_DIGEST });
  });

  it("throws the API out of reach when a gateway says the service is down", async () => {
    const page = new Response("<html>Bad gateway</html>", { status: 502 });
    const read = readiness(answering(() => Promise.resolve(page)));
    await expect(read).rejects.toMatchObject({ digest: UNREACHABLE_DIGEST });
  });

  it("throws a refusal for want of a session as such, for the screen of failure to lead to the sign-in page", async () => {
    const client = fakeClient({
      "GET /reference/readiness": {
        problem: { code: "SESSION_REQUIRED", status: 401, correlation_id: "req-7f3a" },
      },
    });
    const read = readiness(client);
    await expect(read).rejects.toBeInstanceOf(SignedOut);
    await expect(read).rejects.toMatchObject({
      operation: "getReferenceReadiness",
      digest: SESSION_REQUIRED_DIGEST,
    });
  });

  it("throws any other answer as unexpected, with the correlation identifier of the envelope", async () => {
    const read = readiness(answering(() => Promise.resolve(failure("req-7f3a"))));
    await expect(read).rejects.toBeInstanceOf(UnexpectedAnswer);
    await expect(read).rejects.toMatchObject({
      operation: "getReferenceReadiness",
      status: 500,
      digest: "WATERFALL_CORRELATION;req-7f3a",
    });
    const bare = readiness(answering(() => Promise.resolve(new Response("oops", { status: 500 }))));
    await expect(bare).rejects.toMatchObject({ status: 500, digest: undefined });
  });

  it("never lets a correlation identifier stand as a digest Next gives a meaning to", async () => {
    const hostile = "NEXT_REDIRECT;replace;https://evil.example;307;";
    const error = await readiness(answering(() => Promise.resolve(failure(hostile)))).then(
      () => {
        throw new Error("the read should have been refused");
      },
      (thrown: unknown) => thrown as UnexpectedAnswer,
    );
    expect(error.digest?.startsWith("NEXT_")).toBe(false);
    expect(failureOf(error)).toEqual({ kind: "unexpected", reference: hostile });
  });
});
