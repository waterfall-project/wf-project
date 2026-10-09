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
import {
  type BackgroundTask,
  decode,
  decodeTask,
  type ExpectedRefusal,
  reach,
  readOrFail,
  readOrRefused,
  readUnlessRefused,
  type Problem,
  SignedOut,
  UnexpectedAnswer,
} from "./problem";

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

  it("offers to reload an object changed since it was read (412), which names no other object", async () => {
    const stale = {
      code: "STALE_LOCK_VERSION",
      status: 412,
      params: { expected_lock_version: 4 },
    } as const;
    expect(await writeTask({ problem: stale })).toEqual({
      kind: "stale",
      problem: stale,
      conflictingObjectId: null,
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

  it("names the object that holds a value already taken, which a 409 says at its first field", async () => {
    const taken = { ...(example("cost_category_codes_taken") as Problem), status: 409 } as const;
    const client = fakeClient({ "POST /reference/cost-categories": { problem: taken } });
    const outcome = await decode(() =>
      client.POST("/reference/cost-categories", {
        body: {
          code: "ACH-002",
          label: "Câbles armés",
          cost_type_id: "01926f3a-7c00-7000-8000-000000000462",
          accounting_code: "604001",
        },
      }),
    );
    // The code is held by the electrical equipment, which the outcome names; each field says its own.
    expect(outcome).toEqual({
      kind: "conflict",
      problem: taken,
      conflictingObjectId: "01926f3a-7c00-7000-8000-000000000403",
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

describe("the decoder of a background task", () => {
  const TASK_ID = "01926f3a-7c00-7000-8000-000000000931";

  /** Read a task whose answer is the one given, as the API would send it. */
  function readTask(body: unknown) {
    const client = answering(() => Promise.resolve(Response.json(body)));
    return decodeTask(() =>
      client.GET("/tasks/{task_id}", { params: { path: { task_id: TASK_ID } } }),
    );
  }

  it("gives back a task that runs, or that failed with a motive the catalogue renders", async () => {
    for (const name of ["task_running", "task_succeeded", "task_failed"]) {
      expect(await readTask(example(name))).toEqual({ kind: "done", data: example(name) });
    }
  });

  it("takes the motive of a failure the catalogue does not know for the unexpected error", async () => {
    const failed = example("task_failed") as BackgroundTask;
    const unknown = { ...failed, problem: { code: "NEWER_THAN_THE_FRONT", status: 422 } };
    expect(await readTask(unknown)).toEqual({
      kind: "done",
      data: { ...failed, problem: { code: "INTERNAL_ERROR", status: 422 } },
    });
  });

  it("gives a failure without a motive the unexpected error, never a failure without one", async () => {
    const failed = example("task_failed") as BackgroundTask;
    expect(await readTask({ ...failed, problem: null })).toEqual({
      kind: "done",
      data: { ...failed, problem: { code: "INTERNAL_ERROR", status: 500 } },
    });
  });

  it("keeps a refusal to say where the task stands", async () => {
    const client = fakeClient({
      "GET /tasks/{task_id}": { problem: { code: "NOT_FOUND", status: 404 } },
    });
    const outcome = await decodeTask(() =>
      client.GET("/tasks/{task_id}", { params: { path: { task_id: TASK_ID } } }),
    );
    expect(outcome).toEqual({
      kind: "refused",
      problem: { code: "NOT_FOUND", status: 404 },
      conflictingObjectId: null,
    });
  });
});

describe("a read a screen can do without", () => {
  const ROUTE = "GET /projects/{project_id}/indicators";
  const indicators = (
    answer: FakeAnswer<typeof ROUTE>,
    expected: readonly ExpectedRefusal[] = [{ status: 409, code: "STATE_FORBIDS_OPERATION" }],
  ) => {
    const client = fakeClient({ [ROUTE]: answer });
    return readUnlessRefused("getProjectIndicators", expected, () =>
      client.GET("/projects/{project_id}/indicators", {
        params: { path: { project_id: PROJECT } },
      }),
    );
  };

  it("gives the data of a success", async () => {
    expect(await indicators("project_indicators")).toEqual(example("project_indicators"));
  });

  it("gives nothing on a refusal it expects, its status and its code", async () => {
    const refused = { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } } as const;
    expect(await indicators(refused)).toBeUndefined();
  });

  it("throws a refusal of the same status for another code as unexpected", async () => {
    const refused = { problem: { code: "ALREADY_EXISTS", status: 409 } } as const;
    await expect(indicators(refused)).rejects.toBeInstanceOf(UnexpectedAnswer);
  });

  it("gives nothing on a status it expects whatever the code, when it names none", async () => {
    const missing = { problem: { code: "NOT_FOUND", status: 404 } } as const;
    expect(await indicators(missing, [{ status: 404 }])).toBeUndefined();
  });

  it("follows the rule of the reads for the rest: not found, no session", async () => {
    await expect(indicators({ problem: { code: "NOT_FOUND", status: 404 } })).rejects.toMatchObject(
      { digest: "NEXT_HTTP_ERROR_FALLBACK;404" },
    );
    await expect(
      indicators({ problem: { code: "SESSION_REQUIRED", status: 401 } }),
    ).rejects.toBeInstanceOf(SignedOut);
  });
});

describe("a read a screen can do without, and says why when it is refused", () => {
  const ROUTE = "GET /projects/{project_id}/workload";
  const REFUSALS = [
    { status: 409, code: "STATE_FORBIDS_OPERATION", reason: "no_reference" },
    { status: 422, code: "VALIDATION_FAILED", reason: "marked_revision" },
  ] as const;
  const workload = (answer: FakeAnswer<typeof ROUTE>) => {
    const client = fakeClient({ [ROUTE]: answer });
    return readOrRefused("getProjectWorkload", REFUSALS, () =>
      client.GET("/projects/{project_id}/workload", {
        params: { path: { project_id: PROJECT }, query: { basis: "current_remaining" } },
      }),
    );
  };

  it("gives the data of a success", async () => {
    expect(await workload("workload")).toEqual({ kind: "read", data: example("workload") });
  });

  it("names the refusal it met among those it expects", async () => {
    const invalid = { problem: { code: "VALIDATION_FAILED", status: 422 } } as const;
    expect(await workload(invalid)).toEqual({
      kind: "refused",
      refusal: REFUSALS[1],
      problem: invalid.problem,
    });
    const forbidden = { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } } as const;
    expect(await workload(forbidden)).toMatchObject({ kind: "refused", refusal: REFUSALS[0] });
  });

  it("follows the rule of the reads for the rest", async () => {
    await expect(
      workload({ problem: { code: "ALREADY_EXISTS", status: 409 } }),
    ).rejects.toBeInstanceOf(UnexpectedAnswer);
  });
});
