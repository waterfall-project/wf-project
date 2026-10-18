// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import { createAccessRole, deleteAccessRole, updateAccessRole } from "./access-roles";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

type Schemas = components["schemas"];

const ROLE = "01926f3a-7c00-7000-8000-000000000701";
const LAST_ADMINISTRATOR = example("access_role_update_refused") as Problem & { status: 409 };

beforeEach(() => {
  refresh.mockReset();
});

describe("the server actions of the access roles", () => {
  it("create a role from its label and its permissions, and read nothing anew when the API refuses it", async () => {
    const refused: Problem & { status: 422 } = {
      code: "VALIDATION_FAILED",
      status: 422,
      fields: [{ pointer: "/label", code: "VALUE_TOO_LONG", params: { max_length: 100 } }],
    };
    const client = serve({ "POST /access-roles": { problem: refused } });
    const role: Schemas["AccessRoleWrite"] = {
      label: "Contrôle de gestion",
      permissions: ["audit_log.read"],
    };
    expect(await createAccessRole(role)).toMatchObject({ kind: "refused", problem: refused });
    expect(client.calls.map(({ route, body }) => [route, body])).toEqual([
      ["POST /access-roles", role],
    ]);
    expect(refresh).not.toHaveBeenCalled();
  });

  it("modify a role from the version read, and tell the last administrator the API refuses to deprive", async () => {
    const client = serve({
      "PATCH /access-roles/{access_role_id}": { problem: LAST_ADMINISTRATOR },
    });
    const role = { label: "Direction de projet", permissions: [], lock_version: 1 };
    expect(await updateAccessRole(ROLE, role)).toMatchObject({
      kind: "conflict",
      problem: { code: "LAST_ADMINISTRATOR" },
    });
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [`/access-roles/${ROLE}`, role],
    ]);
    expect(refresh).not.toHaveBeenCalled();
  });

  it("delete a role, and read the page anew", async () => {
    const client = serve({ "DELETE /access-roles/{access_role_id}": { status: 204 } });
    expect(await deleteAccessRole(ROLE)).toEqual({ kind: "done", data: null });
    expect(client.calls.map(({ path }) => path)).toEqual([`/access-roles/${ROLE}`]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("tell the role an account holds, which the API refuses to delete, and read nothing anew", async () => {
    const inUse = { code: "ACCESS_ROLE_IN_USE", status: 409 } as const;
    serve({ "DELETE /access-roles/{access_role_id}": { problem: inUse } });
    expect(await deleteAccessRole(ROLE)).toMatchObject({ kind: "conflict", problem: inUse });
    expect(refresh).not.toHaveBeenCalled();
  });
});
