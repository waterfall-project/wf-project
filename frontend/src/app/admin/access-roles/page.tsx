// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The access roles of the installation (FBS-1.2, US-0250), outside any project: each role,
 * predefined or composed, with how many accounts hold it, on a dense grid sorted, searched and
 * filtered by the server as the address asks under the names of the contract (#515, EP-02/L42f) —
 * `sort_by`, `sort_order`, `search`, the kind `is_predefined`, the bounds of the holders
 * `holder_count_min` and `holder_count_max`, which, refused (422), leave the grid unread and are
 * said at their field —; the volumes of §4.6.2
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

import { readOrFail, readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { AccessRoleList, PermissionMatrix } from "@/components/admin/account-lists";
import {
  ACCESS_ROLE_GRID_KEY,
  ACCESS_ROLE_SORTS,
  type AccessRoleSort,
} from "@/components/admin/admin-grids";
import { HOLDER_COUNT, PREDEFINED, rolesQuery } from "@/components/admin/role-address";
import { platformOffer } from "@/components/commands/offer";
import { type Bounds, readBoolean, readBounds, refusedBounds } from "@/components/grid/filters";
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

/** The refusal of bounds the server cannot apply (`listAccessRoles`, 422). */
const BOUNDS_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/**
 * Read the roles as the grid asks them — or the bounds the API refuses —, every role for the matrix
 * — the same reading when the grid asks nothing of the server —, and the catalogue of the
 * permissions.
 */
async function readRoles(filters: {
  readonly query: GridQuery<AccessRoleSort>;
  readonly predefined: boolean | undefined;
  readonly holders: Bounds;
}) {
  const client = serverClient();
  const asked = rolesQuery(filters);
  const narrowed = Object.keys(asked).length > 0;
  const [listed, every, permissions] = await Promise.all([
    readOrRefused("listAccessRoles", BOUNDS_REFUSED, () =>
      client.GET("/access-roles", { params: { query: asked } }),
    ),
    narrowed ? readOrFail("listAccessRoles", () => client.GET("/access-roles")) : undefined,
    readOrFail("listPermissions", () => client.GET("/permissions")),
  ]);
  const read = listed.kind === "read" ? listed.data : undefined;
  return {
    listed: read ?? [],
    refused: listed.kind === "read" ? undefined : refusedBounds(listed.problem.fields ?? []),
    every: every ?? read ?? [],
    permissions,
  };
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
  const predefined = readBoolean(search, PREDEFINED);
  const holders = readBounds(search, HOLDER_COUNT, "count");
  const { listed, refused, every, permissions } = await readRoles({ query, predefined, holders });
  const editable = platformOffer(session?.permissions, "access_roles") !== undefined;
  return (
    <Screen density={FUNCTION_DENSITY.access_roles}>
      <PendingAddress>
        <AccessRolesHeader />
        <AccessRoleList
          roles={listed}
          query={query}
          preferences={preferences}
          filters={{ predefined, holders, refused }}
          editable={editable}
        />
        <PermissionMatrix permissions={permissions} roles={every} />
      </PendingAddress>
    </Screen>
  );
}
