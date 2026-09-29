// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example, type FakeAnswer, fakeClient } from "@/test/fixtures";

import { createApiClient } from "./client";
import { decode } from "./problem";

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
        new Response("<html>Bad gateway</html>", {
          status: 502,
          headers: { "content-type": "text/html" },
        }),
      ),
    );
    const outcome = await decode(() => client.PATCH("/me/preferences", { body: {} }));
    expect(outcome).toEqual({
      kind: "refused",
      problem: { code: "INTERNAL_ERROR", status: 502 },
      conflictingObjectId: null,
    });
  });

  it("lets a defect through rather than take it for an API out of reach", async () => {
    const client = answering(() => Promise.reject(new Error("a defect")));
    await expect(decode(() => client.PATCH("/me/preferences", { body: {} }))).rejects.toThrow(
      "a defect",
    );
  });
});
