// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import { setUserAccessRoles, setUserActivation, updateUser } from "./users";

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

const LUCAS = "01926f3a-7c00-7000-8000-000000000305";
const CAMILLE = "01926f3a-7c00-7000-8000-000000000301";

beforeEach(() => {
  refresh.mockReset();
});

describe("the server actions of the accounts", () => {
  it("modify the names of an account from the version read", async () => {
    const client = serve({ "PATCH /users/{user_id}": "user_renamed" });
    const change = { last_name: "Petit-Laurent", lock_version: 1 };
    expect(await updateUser(LUCAS, change)).toMatchObject({
      kind: "done",
      data: { last_name: "Petit-Laurent", lock_version: 2 },
    });
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [`/users/${LUCAS}`, change],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("deactivate an account, and tell the last administrator the API refuses to deactivate [WF-ADM-0120-A]", async () => {
    const client = serve({
      "PUT /users/{user_id}/activation": [
        "user_deactivated",
        { problem: example("user_deactivation_refused") as Problem & { status: 409 } },
      ],
    });
    expect(await setUserActivation(LUCAS, { is_active: false, lock_version: 1 })).toMatchObject({
      kind: "done",
      data: { is_active: false },
    });
    expect(await setUserActivation(CAMILLE, { is_active: false, lock_version: 3 })).toMatchObject({
      kind: "conflict",
      problem: { code: "STATE_FORBIDS_OPERATION" },
    });
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [`/users/${LUCAS}/activation`, { is_active: false, lock_version: 1 }],
      [`/users/${CAMILLE}/activation`, { is_active: false, lock_version: 3 }],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("attribute the roles of an account, none included, and tell the last administrator deprived", async () => {
    const client = serve({
      "PUT /users/{user_id}/access-roles": [
        "user_access_roles_set",
        { problem: example("user_access_roles_refused") as Problem & { status: 409 } },
      ],
    });
    const chiffreur = ["01926f3a-7c00-7000-8000-000000000705"];
    expect(
      await setUserAccessRoles(LUCAS, { access_role_ids: chiffreur, lock_version: 1 }),
    ).toMatchObject({ kind: "done", data: { access_role_labels: ["Chiffreur"] } });
    expect(
      await setUserAccessRoles(CAMILLE, { access_role_ids: [], lock_version: 3 }),
    ).toMatchObject({
      problem: { code: "LAST_ADMINISTRATOR" },
    });
    expect(client.calls.map(({ body }) => body)).toEqual([
      { access_role_ids: chiffreur, lock_version: 1 },
      { access_role_ids: [], lock_version: 3 },
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });
});
