// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the access roles (FBS-1.2, US-0380): a role created, modified — renamed, or
 * its permissions written by the matrix — or deleted (`createAccessRole`, `updateAccessRole`,
 * `deleteAccessRole`). The screen asks the server of Next, which calls the API (§4.3.1), and gets
 * back the outcome the one decoder makes of its answer (`src/api/problem.ts`): a refusal is told by
 * the catalogue of the codes of error — the role an account holds (`ACCESS_ROLE_IN_USE`), the last
 * administrator (`LAST_ADMINISTRATOR`, WF-ADM-0120).
 *
 * Every write answered reads the page anew: the table and the matrix list the roles as the server
 * retains them, a role created among them, a role deleted no longer — it is neither read nor
 * attributable (WF-ADM-0090) —, and the permissions of the session itself may have changed with
 * those of a role it holds, which the commands of the screen follow (WF-ADM-0110).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome, type Settled, settled } from "@/api/problem";
import { serverClient } from "@/api/server";

type Schemas = components["schemas"];

/** An access role, as the server answers a write of it. */
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

/**
 * Modify a role from the version read: its label and its permissions, whole. The change applies at
 * once to every account that holds it (WF-ADM-0090).
 */
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

/** Delete a role no account holds: logically, its trace kept (WF-DAT-0080). */
export async function deleteAccessRole(accessRoleId: string): Promise<Settled> {
  return settled(
    readAnew(
      await decode(() =>
        serverClient().DELETE("/access-roles/{access_role_id}", {
          params: { path: { access_role_id: accessRoleId } },
        }),
      ),
    ),
  );
}
