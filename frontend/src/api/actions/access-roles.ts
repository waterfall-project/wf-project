// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the access roles (FBS-1.2, US-0380): a role created, modified — renamed, or
 * its permissions written — or deleted, decoded into an outcome (`src/api/problem.ts`). Every write
 * answered reads the page anew: the roles as the server retains them, and the permissions of the
 * session, which a role it holds may have changed (WF-ADM-0110).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome, type Settled, settled } from "@/api/problem";
import { serverClient } from "@/api/server";

type Schemas = components["schemas"];
type AccessRole = Schemas["AccessRole"];

/** Read the page anew once a write is answered. */
function readAnew<T>(outcome: Outcome<T>): Outcome<T> {
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/** Create a role from its label and its permissions — any set of them (WF-ADM-0020). */
export async function createAccessRole(
  role: Schemas["AccessRoleWrite"],
): Promise<Outcome<AccessRole>> {
  return readAnew(await decode(() => serverClient().POST("/access-roles", { body: role })));
}

/** Modify a role, whole, from the version read: at once for its holders (WF-ADM-0090). */
export async function updateAccessRole(
  accessRoleId: string,
  role: Schemas["AccessRoleUpdate"],
): Promise<Outcome<AccessRole>> {
  return readAnew(
    await decode(() =>
      serverClient().PATCH("/access-roles/{access_role_id}", {
        params: { path: { access_role_id: accessRoleId } },
        body: role,
      }),
    ),
  );
}

/**
 * Delete a role no account holds, from the version read: logically, its trace kept (WF-DAT-0080).
 * A role written since is not deleted (412, A-02).
 */
export async function deleteAccessRole(
  accessRoleId: string,
  lockVersion: number,
): Promise<Settled> {
  return settled(
    readAnew(
      await decode(() =>
        serverClient().DELETE("/access-roles/{access_role_id}", {
          params: { path: { access_role_id: accessRoleId }, query: { lock_version: lockVersion } },
        }),
      ),
    ),
  );
}
