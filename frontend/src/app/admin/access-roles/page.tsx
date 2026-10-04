// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The access roles of the installation (FBS-1.2, US-0250), outside any project: each role,
 * predefined or composed, with how many accounts hold it; and the matrix of the permissions by
 * function of the second level, as `listPermissions` gives the catalogue, a column for each role
 * (WF-ADM-0100). Read only: no screen creates a permission, and the forms of the roles belong to the
 * epic of the administration. A read the API refuses, or cannot answer, is thrown for the pages of
 * the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { AccessRoleList, PermissionMatrix } from "@/components/admin/account-lists";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.accessRoles");
}

/** The title of the screen. */
function AccessRolesHeader() {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("accessRoles")}
      icon={FUNCTION_ICONS.access_roles}
      density={FUNCTION_DENSITY.access_roles}
    />
  );
}

/** Render the access roles and the matrix of their permissions. */
export default async function AccessRolesPage() {
  const client = serverClient();
  const [roles, permissions] = await Promise.all([
    readOrFail("listAccessRoles", () => client.GET("/access-roles")),
    readOrFail("listPermissions", () => client.GET("/permissions")),
  ]);
  return (
    <Screen density={FUNCTION_DENSITY.access_roles}>
      <AccessRolesHeader />
      <AccessRoleList roles={roles} />
      <PermissionMatrix permissions={permissions} roles={roles} />
    </Screen>
  );
}
