// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dense grids of the administration in their pages (#514, #515): the accounts and the access
 * roles, each given its configuration here, on the side of the browser — a configuration reads the
 * rows by functions, which never cross from a server component to a client one. The page hands each
 * data only: the rows of the answer, what the address asked, the settings the session read — and,
 * for the accounts, where the page stands —, and whether the session may modify them.
 * Read only: no cell is entered.
 *
 * The totals row says how many the list holds — for the accounts, as the server counts those it
 * retained (`meta.total`), never a count of the page; for the roles, the rows of the answer —,
 * never a sum.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import {
  type AccessRole,
  type AccessRoleSort,
  accessRoleGrid,
  type User,
  type UserPage,
  type UserSort,
  userGrid,
} from "./admin-grids";

/**
 * Render the grid of a page of the accounts, its totals row the number the server retained, with
 * their commands for a session that may modify them.
 */
export function UserGrid({
  users,
  page,
  query,
  preferences,
  editable,
}: {
  readonly users: readonly User[];
  readonly page: UserPage;
  readonly query: GridQuery<UserSort>;
  readonly preferences: GridPreferences | undefined;
  /** Whether the session may modify the accounts (`platformOffer`). */
  readonly editable: boolean;
}) {
  const t = useTranslations("admin.users");
  const config = useMemo(() => userGrid(editable), [editable]);
  return (
    <DenseGrid
      config={config}
      rows={users}
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
  const config = useMemo(() => accessRoleGrid(editable), [editable]);
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
