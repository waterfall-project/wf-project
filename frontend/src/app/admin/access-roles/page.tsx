// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The access roles of the installation (FBS-1.2, US-0250), outside any project: each role,
 * predefined or composed, with how many accounts hold it, on a dense grid sorted and searched by
 * the server as the address asks under the names of the contract (#515) — the volumes of §4.6.2
 * count no roles, three of them predefined: the list holds in one page, which the contract does not
 * page —; and the matrix of the permissions by function of the second level, as `listPermissions`
 * gives the catalogue, a column for each role (WF-ADM-0100), every role in the order the server
 * gives them, whatever the grid asks. A session that may modify the roles is offered the commands
 * to create, modify and delete one, which EP-03 wires (US-0380/L2); another, none. No screen creates
 * a permission. A read the API refuses, or cannot answer, is thrown for the pages of the shell to
 * say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { AccessRoleList, PermissionMatrix } from "@/components/admin/account-lists";
import {
  ACCESS_ROLE_GRID_KEY,
  ACCESS_ROLE_SORTS,
  type AccessRoleSort,
} from "@/components/admin/admin-grids";
import { platformOffer } from "@/components/commands/offer";
import { PendingAddress } from "@/components/grid/pending-address";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { requestSession } from "@/session/request";

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

/**
 * Read the roles as the grid asks them, every role for the matrix — the same reading when the grid
 * asks neither a search nor a sort —, and the catalogue of the permissions.
 */
async function readRoles(query: GridQuery<AccessRoleSort>) {
  const client = serverClient();
  const asked = {
    ...(query.search === undefined ? {} : { search: query.search }),
    ...(query.sort === undefined
      ? {}
      : { sort_by: query.sort.column, sort_order: query.sort.order }),
  };
  const narrowed = Object.keys(asked).length > 0;
  const [listed, every, permissions] = await Promise.all([
    readOrFail("listAccessRoles", () => client.GET("/access-roles", { params: { query: asked } })),
    narrowed ? readOrFail("listAccessRoles", () => client.GET("/access-roles")) : undefined,
    readOrFail("listPermissions", () => client.GET("/permissions")),
  ]);
  return { listed, every: every ?? listed, permissions };
}

/** Render the access roles and the matrix of their permissions. */
export default async function AccessRolesPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const [search, session] = await Promise.all([
    searchParams.then((asked) => pageSearch(asked)),
    requestSession(),
  ]);
  const preferences = session?.user.display_preferences?.grids?.[ACCESS_ROLE_GRID_KEY] ?? undefined;
  const query = readGridQuery(search, ACCESS_ROLE_SORTS, preferences?.sort);
  const { listed, every, permissions } = await readRoles(query);
  const editable = platformOffer(session?.permissions, "access_roles") !== undefined;
  return (
    <Screen density={FUNCTION_DENSITY.access_roles}>
      <PendingAddress>
        <AccessRolesHeader />
        <AccessRoleList
          roles={listed}
          query={query}
          preferences={preferences}
          editable={editable}
        />
        <PermissionMatrix permissions={permissions} roles={every} />
      </PendingAddress>
    </Screen>
  );
}
