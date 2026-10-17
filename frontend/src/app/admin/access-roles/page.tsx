// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The access roles of the installation (FBS-1.2, US-0250), outside any project: each role,
 * predefined or composed, with how many accounts hold it, on a dense grid sorted, searched and
 * filtered by the server as the address asks under the names of the contract (#515, EP-02/L42f) —
 * `sort_by`, `sort_order`, `search`, the kind `is_predefined`, the bounds of the holders
 * `holder_count_min` and `holder_count_max`, the periods and the authors of the creation and of the
 * last modification of the roles — `created_at_from`, `updated_by_user_id`… —, a bound or a period
 * refused (422) leaving the grid unread, said at its field —, the authors offered those of the roles
 * unfiltered, an account chosen that none of them cites read by its names (`readChosenAuthors`);
 * the volumes of §4.6.2 count no roles, three of them predefined: the list holds in one page, which the contract does not
 * page —; and the matrix of the permissions by function of the second level, as `listPermissions`
 * gives the catalogue, a column for each role the table retains, in its order (WF-ADM-0100). A
 * session that may modify the roles creates one in line, renames and deletes it in the table, and
 * writes its permissions in the matrix (US-0380/L2), the roles answered shared by both
 * (`RoleAnswers`); another, none. An address that says nothing of the table — neither sort, nor
 * search, nor filter — leads, before anything is read, to the address of the search and the filters
 * the account keeps for it, if it keeps any (`restoredAddress`, WF-IHM-0060). No screen creates
 * a permission. A read the API refuses, or cannot answer, is thrown for the pages of the shell to
 * say.
 */
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { useTranslations } from "next-intl";

import { readOrFail, readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { AccessRoleList, PermissionMatrix } from "@/components/admin/account-lists";
import {
  ACCESS_ROLE_GRID_KEY,
  ACCESS_ROLE_SORTS,
  type AccessRoleSort,
} from "@/components/admin/admin-grids";
import {
  type AuditFilters,
  authorsOf,
  readAuditFilters,
  refusedAudit,
} from "@/components/admin/audit-address";
import { MatrixWrites } from "@/components/admin/permission-matrix";
import { RoleAnswers } from "@/components/admin/role-answers";
import {
  ACCESS_ROLES_PATH,
  HOLDER_COUNT,
  PREDEFINED,
  ROLE_KEPT,
  rolesNarrowed,
  rolesQuery,
} from "@/components/admin/role-address";
import { platformOffer } from "@/components/commands/offer";
import { type Bounds, readBoolean, readBounds, refusedBounds } from "@/components/grid/filters";
import { restoredAddress } from "@/components/grid/kept-address";
import { PendingAddress } from "@/components/grid/pending-address";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";
import { readChosenAuthors } from "../chosen-authors";

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

/** The refusal of bounds or of a period the server cannot apply (`listAccessRoles`, 422). */
const BOUNDS_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/**
 * Read the roles as the grid asks them — or the bounds and the periods the API refuses —, which the
 * matrix shows too, the catalogue of the permissions, and the authors of the roles: those of the list
 * unfiltered, read again only when the grid narrows it — the contract has no list of the authors.
 */
async function readRoles(filters: {
  readonly query: GridQuery<AccessRoleSort>;
  readonly predefined: boolean | undefined;
  readonly holders: Bounds;
  readonly audit: AuditFilters;
}) {
  const client = serverClient();
  const narrowed = rolesNarrowed(filters);
  const [listed, permissions, unfiltered] = await Promise.all([
    readOrRefused("listAccessRoles", BOUNDS_REFUSED, () =>
      client.GET("/access-roles", { params: { query: rolesQuery(filters) } }),
    ),
    readOrFail("listPermissions", () => client.GET("/permissions")),
    narrowed ? readOrFail("listAccessRoles", () => client.GET("/access-roles")) : undefined,
  ]);
  if (listed.kind !== "read") {
    const fields = listed.problem.fields ?? [];
    return {
      listed: [],
      refused: { bounds: refusedBounds(fields), periods: refusedAudit(fields) },
      authors: authorsOf(unfiltered ?? []),
      permissions,
    };
  }
  return {
    listed: listed.data,
    refused: undefined,
    authors: authorsOf(unfiltered ?? listed.data),
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
  const preferences = session?.display_preferences?.grids?.[ACCESS_ROLE_GRID_KEY] ?? undefined;
  // An address that says nothing of the table: the filters kept, before anything is read.
  const restored = restoredAddress(ACCESS_ROLES_PATH, search, ROLE_KEPT, preferences?.filters);
  if (restored !== undefined) {
    redirect(restored);
  }
  const query = readGridQuery(search, ACCESS_ROLE_SORTS, preferences?.sort);
  const predefined = readBoolean(search, PREDEFINED);
  const holders = readBounds(search, HOLDER_COUNT, "count");
  const audit = readAuditFilters(search);
  const { listed, refused, authors, permissions } = await readRoles({
    query,
    predefined,
    holders,
    audit,
  });
  // An account chosen as an author that no role cites, read by its names.
  const named = await readChosenAuthors(audit, authors);
  // What the list shows of its filters, a side of a bound or of a period the API refused said at its
  // field.
  const filters = {
    predefined,
    holders,
    refused: refused?.bounds,
    audit: { ...audit, refused: refused?.periods, named },
    authors,
  };
  const editable = platformOffer(session?.permissions, "access_roles") !== undefined;
  return (
    <Screen density={FUNCTION_DENSITY.access_roles}>
      <PendingAddress kept={ROLE_KEPT}>
        <AccessRolesHeader />
        {editable ? (
          // The roles the server answered, one source for the table and the matrix.
          <RoleAnswers>
            <AccessRoleList
              roles={listed}
              query={query}
              preferences={preferences}
              filters={filters}
              editable
            />
            <MatrixWrites order={permissions.map(({ code }) => code)} roles={listed}>
              <PermissionMatrix permissions={permissions} roles={listed} editable />
            </MatrixWrites>
          </RoleAnswers>
        ) : (
          <>
            <AccessRoleList
              roles={listed}
              query={query}
              preferences={preferences}
              filters={filters}
              editable={false}
            />
            <PermissionMatrix permissions={permissions} roles={listed} editable={false} />
          </>
        )}
      </PendingAddress>
    </Screen>
  );
}
