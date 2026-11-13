// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a group of accounts selected is written with (`UserWrites.bulk`, US-1860/L3): one call for
 * each account, from the account as the writes before it left it. A role is added to those the
 * account holds, never put in their place. Every account is written, even one the screen shows as asked: the screen
 * may be stale, and the server decides (a 412 tells the account modified meanwhile).
 */
import { setUserAccessRoles, setUserActivation, updateUser } from "@/api/actions/users";
import type { Outcome } from "@/api/problem";

import type { User } from "./admin-grids";

/** What a group of accounts is written with. */
export type BulkAction =
  | { readonly kind: "add_role"; readonly role: string }
  | { readonly kind: "attach"; readonly node: string | null }
  | { readonly kind: "activation"; readonly active: boolean };

/** The write of an action on an account, from the account as the writes before it left it. */
export function bulkSend(action: BulkAction): (user: User) => Promise<Outcome<User>> {
  return async (user) => {
    switch (action.kind) {
      case "add_role":
        return setUserAccessRoles(user.user_id, {
          access_role_ids: user.access_role_ids.includes(action.role)
            ? user.access_role_ids
            : [...user.access_role_ids, action.role],
          lock_version: user.lock_version,
        });
      case "attach":
        return updateUser(user.user_id, {
          org_node_id: action.node,
          lock_version: user.lock_version,
        });
      case "activation":
        return setUserActivation(user.user_id, {
          is_active: action.active,
          lock_version: user.lock_version,
        });
    }
  };
}
