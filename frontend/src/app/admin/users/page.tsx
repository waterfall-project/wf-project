// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The accounts of the installation (FBS-1.1, US-0250), outside any project: a page of the list the
 * server pages, deactivated accounts included — they stay listed, and may be reactivated
 * (WF-ADM-0060) —, each with its access roles and the node it is attached to, named by the server;
 * a dense grid (#514), sorted, searched — on the names and the address —, filtered by origin, by node
 * and by access role, and paged by the server, as the address asks under the names of the contract
 * (`sort_by`, `sort_order`, `search`, `origins`, `org_node_id`, `access_role_ids`, `is_active`,
 * `include_inactive`, `offset`), the nodes offered in the order of the tree, the roles as
 * `listAccessRoles` gives them — none to a session that may not read them; the
 * deactivated accounts listed unless the address says `include_inactive=false`. Every figure as the
 * API gives it: the front sorts, filters and pages nothing. No screen offers to delete an account;
 * a session that may modify the accounts is offered the commands — create a local account in the
 * header, modify, deactivate or reactivate, attribute the roles on each account —, which EP-03
 * wires (#379); another, none. A read the API refuses, or cannot answer, is thrown for the pages
 * of the shell to say; a tree of the organisation it does not find leaves the screen standing,
 * without a node to choose.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail, readUnlessRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { UserList } from "@/components/admin/account-lists";
import { USER_GRID_KEY, USER_SORTS } from "@/components/admin/admin-grids";
import { CreateCommand, LaterCommands } from "@/components/admin/later-commands";
import {
  ACCESS_ROLES,
  ORG_NODE,
  ORIGINS,
  readAccountState,
  USER_ORIGINS,
  usersQuery,
} from "@/components/admin/user-address";
import { platformOffer } from "@/components/commands/offer";
import { readValues } from "@/components/grid/filters";
import { PendingAddress } from "@/components/grid/pending-address";
import { readGridQuery } from "@/components/grid/query";
import { identifierOf } from "@/components/reference/address";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { OFFSET_PARAMETER, offsetOf } from "@/navigation/pages";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.users");
}

/** The title of the screen, and the command that creates a local account for who may. */
function UsersHeader({ editable }: { readonly editable: boolean }) {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("users")}
      icon={FUNCTION_ICONS.users}
      density={FUNCTION_DENSITY.users}
      actions={editable ? <CreateCommand kind="localAccount" /> : undefined}
    />
  );
}

/** The nodes of organisation the accounts may be restricted to, in the order of the tree. */
async function readNodes() {
  const nodes = await readUnlessRefused("listOrgNodes", [{ status: 404 }], () =>
    serverClient().GET("/reference/org-nodes"),
  );
  return (nodes ?? []).map((node) => ({
    id: node.org_node_id,
    code: node.code,
    label: node.label,
    level: node.level,
  }));
}

/**
 * The access roles the accounts may be restricted to, as the server gives them; none when the API
 * does not find them — a session that may not read the roles (WF-ADM-0110).
 */
async function readRoles() {
  const roles = await readUnlessRefused("listAccessRoles", [{ status: 404 }], () =>
    serverClient().GET("/access-roles"),
  );
  return (roles ?? []).map((role) => ({ id: role.access_role_id, label: role.label }));
}

/** Render the accounts of the page the address asks for. */
export default async function UsersPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const [search, session] = await Promise.all([
    searchParams.then((asked) => pageSearch(asked)),
    requestSession(),
  ]);
  const preferences = session?.display_preferences?.grids?.[USER_GRID_KEY] ?? undefined;
  const query = readGridQuery(search, USER_SORTS, preferences?.sort);
  const origins = readValues(search, ORIGINS, USER_ORIGINS);
  const orgNode = identifierOf(search, ORG_NODE);
  const active = readAccountState(search);
  const editable = platformOffer(session?.permissions, "users") !== undefined;
  const offset = offsetOf(search.get(OFFSET_PARAMETER));
  // The roles the address names among those the server gives: an identifier of none is not asked.
  const roles = await readRoles();
  const accessRoles = readValues(
    search,
    ACCESS_ROLES,
    roles.map((role) => role.id),
  );
  const [users, nodes] = await Promise.all([
    readOrFail("listUsers", () =>
      serverClient().GET("/users", {
        params: {
          query: usersQuery({ query, origins, orgNode, accessRoles, active, offset }),
        },
      }),
    ),
    readNodes(),
  ]);
  return (
    <Screen density={FUNCTION_DENSITY.users} fill>
      {/* The filters, the grid and the pages compose the changes they make to the address; the
      commands share the region that says what they do. */}
      <PendingAddress>
        <LaterCommands>
          <UsersHeader editable={editable} />
          <UserList
            users={users.items}
            page={users.meta}
            query={query}
            preferences={preferences}
            origins={origins}
            nodes={nodes}
            orgNode={orgNode}
            roles={roles}
            accessRoles={accessRoles}
            active={active}
            editable={editable}
          />
        </LaterCommands>
      </PendingAddress>
    </Screen>
  );
}
