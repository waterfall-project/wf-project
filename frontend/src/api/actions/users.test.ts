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

import {
  anonymizeUser,
  createPasswordSetupLink,
  createUser,
  setUserAccessRoles,
  setUserActivation,
  updateUser,
} from "./users";

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

// Each account the example answering its write is of.
const LUCAS = "01926f3a-7c00-7000-8000-000000000305";
const CAMILLE = "01926f3a-7c00-7000-8000-000000000301";
const SACHA = "01926f3a-7c00-7000-8000-000000000304";
const NOE = "01926f3a-7c00-7000-8000-000000000307";
const ALIX = "01926f3a-7c00-7000-8000-000000000303";

beforeEach(() => {
  refresh.mockReset();
});

describe("the server actions of the accounts", () => {
  it("create a local account from its names and its address, and read the page anew", async () => {
    const client = serve({ "POST /users": { status: 201, example: "user_created" } });
    const user = { last_name: "Garnier", first_name: "Léa", email: "lea.garnier@example.com" };
    expect(await createUser(user)).toMatchObject({
      kind: "done",
      data: { last_name: "Garnier", origin: "local", lock_version: 1, invitation_sent: false },
    });
    expect(client.calls.map(({ route, body }) => [route, body])).toEqual([["POST /users", user]]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("tell the address another account holds, and read nothing anew [WF-ADM-0050-A]", async () => {
    const taken = example("user_email_taken") as Problem & { status: 409 };
    serve({ "POST /users": { problem: taken } });
    expect(
      await createUser({
        last_name: "Petit",
        first_name: "Lucas",
        email: "lucas.petit@example.com",
      }),
    ).toMatchObject({ problem: taken });
    expect(refresh).not.toHaveBeenCalled();
  });

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
    expect(await setUserActivation(NOE, { is_active: false, lock_version: 1 })).toMatchObject({
      kind: "done",
      data: { is_active: false },
    });
    expect(await setUserActivation(CAMILLE, { is_active: false, lock_version: 3 })).toMatchObject({
      kind: "conflict",
      problem: { code: "STATE_FORBIDS_OPERATION" },
    });
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [`/users/${NOE}/activation`, { is_active: false, lock_version: 1 }],
      [`/users/${CAMILLE}/activation`, { is_active: false, lock_version: 3 }],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("attribute the roles of an account, none included, and tell the last administrator the API refuses to deprive [WF-ADM-0120-A]", async () => {
    const client = serve({
      "PUT /users/{user_id}/access-roles": [
        "user_access_roles_set",
        { problem: example("user_access_roles_refused") as Problem & { status: 409 } },
      ],
    });
    const chiffreur = ["01926f3a-7c00-7000-8000-000000000705"];
    expect(
      await setUserAccessRoles(SACHA, { access_role_ids: chiffreur, lock_version: 1 }),
    ).toMatchObject({ kind: "done", data: { access_role_labels: ["Chiffreur"] } });
    expect(
      await setUserAccessRoles(CAMILLE, { access_role_ids: [], lock_version: 3 }),
    ).toMatchObject({
      kind: "conflict",
      problem: { code: "LAST_ADMINISTRATOR" },
    });
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [`/users/${SACHA}/access-roles`, { access_role_ids: chiffreur, lock_version: 1 }],
      [`/users/${CAMILLE}/access-roles`, { access_role_ids: [], lock_version: 3 }],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("ask the link of a local account, given once, and read nothing anew", async () => {
    const client = serve({
      "POST /users/{user_id}/password-link": [
        { status: 201, example: "password_setup_link" },
        { problem: example("password_link_not_local") as Problem & { status: 409 } },
      ],
    });
    expect(await createPasswordSetupLink(CAMILLE)).toMatchObject({
      kind: "done",
      data: { expires_at: "2026-06-03T15:05:00Z" },
    });
    expect(await createPasswordSetupLink(LUCAS)).toMatchObject({
      problem: { params: { missing_condition: "is_local_account" } },
    });
    expect(client.calls.map(({ path }) => path)).toEqual([
      `/users/${CAMILLE}/password-link`,
      `/users/${LUCAS}/password-link`,
    ]);
    expect(refresh).not.toHaveBeenCalled();
  });

  it("anonymise a deactivated account from the version read, and read the page anew; an active one refused [WF-ADM-0060-A]", async () => {
    const client = serve({
      "POST /users/{user_id}/anonymization": [
        "user_anonymized",
        { problem: example("user_anonymization_refused") as Problem & { status: 409 } },
      ],
    });
    expect(await anonymizeUser(ALIX, { lock_version: 2 })).toMatchObject({
      kind: "done",
      data: { last_name: null, email: null, anonymized_at: "2026-06-03T14:05:00Z" },
    });
    expect(refresh).toHaveBeenCalledOnce();
    expect(await anonymizeUser(NOE, { lock_version: 1 })).toMatchObject({
      problem: { params: { missing_condition: "is_deactivated_account" } },
    });
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [`/users/${ALIX}/anonymization`, { lock_version: 2 }],
      [`/users/${NOE}/anonymization`, { lock_version: 1 }],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });
});
