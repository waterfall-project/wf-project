// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dense grids of the administration in their pages (#514, #515): the accounts and the access
 * roles, each given its configuration here, on the side of the browser — a configuration reads the
 * rows by functions, which never cross from a server component to a client one. The page hands each
 * data only: the rows of the answer, what the address asked, the settings the session read — and,
 * for the accounts, where the page stands, and the roles of the installation —, and whether the
 * session may modify them: the accounts are entered in their table, the accounts the server answered
 * shown in place of those read while they are newer (`UserCommands`); the roles, their label.
 *
 * The totals row says how many the list holds — for the accounts, as the server counts those it
 * retained (`meta.total`), never a count of the page; for the roles, the rows of the answer —,
 * never a sum.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { useAccountNaming } from "@/components/account/account-name";
import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import { useRoleAnswers } from "./role-answers";
import {
  type AccessRole,
  type AccessRoleSort,
  accessRoleGrid,
  type RoleChoice,
  type User,
  type UserPage,
  type UserSort,
  userGrid,
} from "./admin-grids";
import { newer, useUserWrites } from "./user-commands";

/**
 * Render the grid of a page of the accounts, its totals row the number the server retained — its
 * own entry for a session that may modify them, within the commands of the table (`UserCommands`),
 * each account shown as the server last answered it while that is newer than the one read.
 */
export function UserGrid({
  users,
  page,
  query,
  preferences,
  roles,
  editable,
}: {
  readonly users: readonly User[];
  readonly page: UserPage;
  readonly query: GridQuery<UserSort>;
  readonly preferences: GridPreferences | undefined;
  /** The roles of the installation an account may be given; none when the session reads none. */
  readonly roles: readonly RoleChoice[];
  /** Whether the session may modify the accounts (`platformOffer`). */
  readonly editable: boolean;
}) {
  const t = useTranslations("admin.users");
  const naming = useAccountNaming();
  const writes = useUserWrites();
  const queue = writes?.queue;
  const answered = writes?.answered;
  const config = useMemo(
    () =>
      userGrid(
        editable
          ? {
              roles: () => roles,
              // A name entered waits for the writes of its row, and is said once answered.
              rename:
                queue === undefined
                  ? undefined
                  : (shown, send) =>
                      queue(shown, {
                        send,
                        said: (renamed) => t("renamed", { name: naming.person(renamed) }),
                      }),
            }
          : undefined,
      ),
    [editable, roles, queue, t, naming],
  );
  const shown = useMemo(
    () =>
      answered === undefined || answered.size === 0
        ? users
        : users.map((user) => newer(user, answered.get(user.user_id))),
    [users, answered],
  );
  return (
    <DenseGrid
      config={config}
      rows={shown}
      totals={page}
      totalsCaption={(retained) => t("count", { count: retained.total })}
      query={query}
      preferences={preferences}
    />
  );
}

/** Render the grid of the access roles, with their commands for a session that may modify them. */
export function AccessRoleGrid({
  roles,
  query,
  preferences,
  editable,
}: {
  readonly roles: readonly AccessRole[];
  readonly query: GridQuery<AccessRoleSort>;
  readonly preferences: GridPreferences | undefined;
  /** Whether the session may modify the access roles (`platformOffer`). */
  readonly editable: boolean;
}) {
  const t = useTranslations("admin.accessRoles");
  // The roles the server answered, which the renaming writes from, shared with the matrix.
  const answers = useRoleAnswers();
  const latest = answers?.latest;
  const record = answers?.record;
  const config = useMemo(
    () =>
      accessRoleGrid(
        editable,
        latest === undefined || record === undefined ? undefined : { latest, record },
      ),
    [editable, latest, record],
  );
  return (
    <DenseGrid
      config={config}
      rows={roles}
      totals={null}
      totalsCaption={() => t("count", { count: roles.length })}
      query={query}
      preferences={preferences}
    />
  );
}
