// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the accounts (FBS-1.1, US-0360): an account modified — the names of a local
 * one —, deactivated or reactivated — never deleted (WF-ADM-0060) —, its access roles attributed,
 * each decoded into an outcome (`src/api/problem.ts`). Every write answered reads the page anew: the
 * accounts as the server retains them, and the permissions of the session, which an attribution of
 * its own roles may have changed (WF-ADM-0110).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

type Schemas = components["schemas"];
type User = Schemas["User"];

/** Read the page anew once a write is answered. */
function readAnew<T>(outcome: Outcome<T>): Outcome<T> {
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/** Modify an account from the version read. */
export async function updateUser(
  userId: string,
  user: Schemas["UserUpdate"],
): Promise<Outcome<User>> {
  return readAnew(
    await decode(() =>
      serverClient().PATCH("/users/{user_id}", {
        params: { path: { user_id: userId } },
        body: user,
      }),
    ),
  );
}

/** Deactivate or reactivate an account from the version read: never delete it (WF-ADM-0060). */
export async function setUserActivation(
  userId: string,
  activation: Schemas["UserActivationWrite"],
): Promise<Outcome<User>> {
  return readAnew(
    await decode(() =>
      serverClient().PUT("/users/{user_id}/activation", {
        params: { path: { user_id: userId } },
        body: activation,
      }),
    ),
  );
}

/** Attribute its access roles to an account, from the version read: none, one or more. */
export async function setUserAccessRoles(
  userId: string,
  roles: Schemas["UserRolesWrite"],
): Promise<Outcome<User>> {
  return readAnew(
    await decode(() =>
      serverClient().PUT("/users/{user_id}/access-roles", {
        params: { path: { user_id: userId } },
        body: roles,
      }),
    ),
  );
}
