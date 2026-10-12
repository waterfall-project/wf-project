// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the accounts (FBS-1.1, US-0360): a local account created, an account
 * modified — the names of a local one —, deactivated or reactivated — never deleted (WF-ADM-0060) —,
 * anonymised once deactivated, its access roles attributed, each decoded into an outcome
 * (`src/api/problem.ts`); and the link by which the holder of a local account sets its password,
 * handed to who asked it (WF-ADM-0140). Every write answered reads the page anew: the accounts as the server retains them, and the permissions of
 * the session, which an attribution of its own roles may have changed (WF-ADM-0110). The link reads
 * nothing anew: it changes nothing the page shows.
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

/**
 * Create a local account from its names and its address (WF-ADM-0050), and say whether the invitation
 * that carries its link went.
 */
export async function createUser(
  user: Schemas["UserCreate"],
): Promise<Outcome<Schemas["UserCreated"]>> {
  return readAnew(await decode(() => serverClient().POST("/users", { body: user })));
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

/**
 * Anonymise a deactivated account from the version read, irreversibly (WF-ADM-0060): the screen asks
 * the confirmation first, the server none.
 */
export async function anonymizeUser(
  userId: string,
  anonymization: Schemas["UserAnonymizationWrite"],
): Promise<Outcome<User>> {
  return readAnew(
    await decode(() =>
      serverClient().POST("/users/{user_id}/anonymization", {
        params: { path: { user_id: userId } },
        body: anonymization,
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

/** Ask the link by which the holder of a local account sets its password, given once. */
export async function createPasswordSetupLink(
  userId: string,
): Promise<Outcome<Schemas["PasswordSetupLink"]>> {
  return decode(() =>
    serverClient().POST("/users/{user_id}/password-link", {
      params: { path: { user_id: userId } },
    }),
  );
}
