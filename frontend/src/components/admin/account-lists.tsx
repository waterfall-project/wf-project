// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The accounts and the access roles (FBS-1.1, FBS-1.2, US-0250), each a dense grid under its title
 * (#514, #515), in the order the server gave them: each account with its origin, its access roles
 * and the node it is attached to — named as the server resolves them — and whether it is active, a
 * deactivated one staying listed unless a state is chosen (WF-ADM-0050, WF-ADM-0060), filtered
 * by origin, by node, by access role and by state, a page of the list the server pages, and the
 * commands of the accounts for a session that may modify them, which EP-03 wires; each access role,
 * predefined or composed, with how many accounts hold it (WF-ADM-0010, WF-ADM-0090), filtered by
 * kind and between bounds of their holders, and the commands of the roles for a session that may
 * modify them, which EP-03 wires; and the matrix of the permissions, a row for each permission of
 * the catalogue as `listPermissions` gives it, gathered under the name of the function of the
 * second level it covers — or the kind of the action it guards —, a column for each role, which
 * holds it or not (WF-ADM-0100), where EP-03 modifies a role. The forms belong to the epic of the
 * administration, and no screen creates a permission.
 *
 * A list says it is empty only when nothing narrows it: a search or a filter that retains nothing
 * keeps its grid, the search shown to be changed.
 */
import { Check, KeyRound, ShieldCheck, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { ChoiceFilter } from "@/components/grid/choice-filter";
import { type Bounds, bounded, type RefusedBounds, refusedSides } from "@/components/grid/filters";
import { ListPages } from "@/components/grid/list-pages";
import { OFFSET, type GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { RangeFilter } from "@/components/grid/range-filter";
import { type FilterValue, ValuesFilter } from "@/components/grid/values-filter";
import { CELL, ICON } from "@/components/projects/project-tables";
import { type NodeChoice, OrgNodeFilter } from "@/components/reference/reference-filters";
import { BoundsRefused, ReferenceSection } from "@/components/reference/section";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { functionAt } from "@/navigation/functions";

import { AccessRoleGrid, UserGrid } from "./admin-grid";
import type { AccessRoleSort, User, UserPage, UserSort } from "./admin-grids";
import { CreateCommand, LaterCommands, LaterNotice } from "./later-commands";
import { HOLDER_COUNT, PREDEFINED } from "./role-address";
import {
  ACCESS_ROLES,
  INCLUDE_INACTIVE,
  IS_ACTIVE,
  ORG_NODE,
  ORIGINS,
  USER_ORIGINS,
  type UserOrigin,
  USERS_LIST,
} from "./user-address";

type AccessRole = components["schemas"]["AccessRole"];
type Permission = components["schemas"]["Permission"];

/** An access role the accounts may be restricted to, by its identifier and its label. */
export interface RoleChoice {
  readonly id: string;
  readonly label: string;
}

/**
 * The accounts of a page of the list, filtered by origin, by node, by access role — one at least of
 * those chosen, an account without a role retained by none: choosing every role still filters —
 * and by state — the active or the deactivated ones alone; none, every account —, or that the
 * installation has none — only when the list holds none at all and nothing narrows it: a page asked
 * beyond its end is no empty list; its pages say where it stands (`ListPages`). For a session that
 * may modify the accounts, the region that says what their commands do, which the screen shares
 * with the command of its header (`LaterCommands`) — before the list, so that it speaks when the
 * list is empty too.
 */
export function UserList({
  users,
  page,
  query,
  preferences,
  origins,
  nodes,
  orgNode,
  roles,
  accessRoles,
  active,
  editable,
}: {
  readonly users: readonly User[];
  readonly page: UserPage;
  readonly query: GridQuery<UserSort>;
  readonly preferences: GridPreferences | undefined;
  /** The origins the address restricts the accounts to; none, every one. */
  readonly origins: readonly UserOrigin[];
  /** The nodes of organisation the accounts may be restricted to, in the order of the tree. */
  readonly nodes: readonly NodeChoice[];
  /** The node the address restricts the accounts to, if any. */
  readonly orgNode: string | undefined;
  /** The access roles the accounts may be restricted to; none when the session reads none. */
  readonly roles: readonly RoleChoice[];
  /** The access roles the address restricts the accounts to; none, every account. */
  readonly accessRoles: readonly string[];
  /**
   * The state the address restricts the accounts to: the active ones alone, the deactivated ones
   * alone; none, every account — what the grid shows, the choice says.
   */
  readonly active: boolean | undefined;
  /** Whether the session may modify the accounts (`platformOffer`). */
  readonly editable: boolean;
}) {
  const t = useTranslations("admin.users");
  const named = useTranslations("enums.UserOrigin");
  const narrowed =
    query.search !== undefined ||
    origins.length > 0 ||
    orgNode !== undefined ||
    accessRoles.length > 0 ||
    active !== undefined;
  const choices: FilterValue<UserOrigin>[] = USER_ORIGINS.map((origin) => ({
    value: origin,
    text: named(origin),
  }));
  return (
    <>
      {/* Outside the section, which an empty list empties: the command of the header is told. */}
      {editable ? <LaterNotice /> : null}
      <ReferenceSection
        title={t("title")}
        icon={Users}
        empty={page.total === 0 && !narrowed ? t("none") : undefined}
        fill
      >
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <ValuesFilter
            name={ORIGINS}
            label={t("originFilter")}
            every={t("everyOrigin")}
            values={choices}
            chosen={origins}
            page={OFFSET}
          />
          <OrgNodeFilter name={ORG_NODE} nodes={nodes} chosen={orgNode} page={OFFSET} />
          {/* No role the session reads, none offered. */}
          {roles.length === 0 ? null : (
            <ValuesFilter
              name={ACCESS_ROLES}
              label={t("roleFilter")}
              every={t("everyRole")}
              values={roles.map((role) => ({ value: role.id, text: role.label }))}
              chosen={accessRoles}
              page={OFFSET}
              exhaustive={false}
            />
          )}
          <ChoiceFilter
            name={IS_ACTIVE}
            label={t("stateFilter")}
            every={t("everyState")}
            choices={[
              { value: "true", text: t("activeAccounts") },
              { value: "false", text: t("inactiveAccounts") },
            ]}
            chosen={active === undefined ? undefined : String(active)}
            page={OFFSET}
            lifts={[INCLUDE_INACTIVE]}
          />
        </div>
        <UserGrid
          users={users}
          page={page}
          query={query}
          preferences={preferences}
          editable={editable}
        />
        <ListPages list={USERS_LIST} texts="admin.pages" page={page} shown={users.length} />
      </ReferenceSection>
    </>
  );
}

/** The filters of the access roles, as the address asks them, and what the API refused of them. */
export interface RoleFilters {
  /** The kind the address restricts the roles to: predefined, composed; none, both. */
  readonly predefined: boolean | undefined;
  /** The bounds of the number of holders the address sets. */
  readonly holders: Bounds;
  /** The bounds the API refused (422), the list then unread; none when it was read. */
  readonly refused?: RefusedBounds | undefined;
}

/** The filters of the access roles: their kind, a choice, and the bounds of their holders. */
function RoleFilterBar({ filters }: { readonly filters: RoleFilters }) {
  const t = useTranslations();
  return (
    <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
      <ChoiceFilter
        name={PREDEFINED}
        label={t("admin.accessRoles.kindFilter")}
        every={t("admin.accessRoles.everyKind")}
        choices={[
          { value: "true", text: t("admin.accessRoles.predefinedRoles") },
          { value: "false", text: t("admin.accessRoles.composedRoles") },
        ]}
        chosen={filters.predefined === undefined ? undefined : String(filters.predefined)}
      />
      <RangeFilter
        label={t("admin.accessRoles.bounds")}
        kind="count"
        columns={[
          {
            column: HOLDER_COUNT,
            label: t("grid.columns.holders"),
            bounds: filters.holders,
            refused: refusedSides(filters.refused, HOLDER_COUNT),
          },
        ]}
      />
    </div>
  );
}

/**
 * The access roles, each predefined or composed, with how many accounts hold it, filtered by kind
 * and between bounds of their holders; for a session that may modify them, the command that
 * creates one, and those that modify and delete each. Bounds the API refuses (422) leave the list
 * unread, the bound said at its field, a sentence standing for the grid.
 */
export function AccessRoleList({
  roles,
  query,
  preferences,
  filters,
  editable,
}: {
  readonly roles: readonly AccessRole[];
  readonly query: GridQuery<AccessRoleSort>;
  readonly preferences: GridPreferences | undefined;
  readonly filters: RoleFilters;
  /** Whether the session may modify the access roles (`platformOffer`). */
  readonly editable: boolean;
}) {
  const t = useTranslations("admin.accessRoles");
  const narrowed =
    query.search !== undefined || filters.predefined !== undefined || bounded(filters.holders);
  let list: ReactNode;
  if (filters.refused !== undefined) {
    list = <BoundsRefused />;
  } else if (roles.length === 0 && !narrowed) {
    // Empty only when nothing narrows it; the command that creates a role is offered all the same.
    list = <p className="text-sm text-muted-foreground">{t("none")}</p>;
  } else {
    list = (
      <AccessRoleGrid roles={roles} query={query} preferences={preferences} editable={editable} />
    );
  }
  const shown = (
    <>
      <RoleFilterBar filters={filters} />
      {list}
    </>
  );
  return (
    <ReferenceSection title={t("title")} icon={ShieldCheck}>
      {editable ? (
        <LaterCommands>
          <CreateCommand kind="role" />
          <LaterNotice />
          {shown}
        </LaterCommands>
      ) : (
        shown
      )}
    </ReferenceSection>
  );
}

/**
 * The permissions of the catalogue, in its order, gathered into runs of those that cover the same
 * function of the second level — or, outside any function, that are of the same kind. A run follows
 * the order of the catalogue: nothing is moved.
 */
function runsOf(permissions: readonly Permission[]): Permission[][] {
  const runs: Permission[][] = [];
  for (const permission of permissions) {
    const last = runs.at(-1);
    const head = last?.[0];
    if (last !== undefined && head !== undefined && sameRun(head, permission)) {
      last.push(permission);
    } else {
      runs.push([permission]);
    }
  }
  return runs;
}

/** Whether two permissions cover the same function, or are of the same kind outside any. */
function sameRun(one: Permission, other: Permission): boolean {
  const fbs = one.fbs_code ?? null;
  return fbs === (other.fbs_code ?? null) && (fbs !== null || one.kind === other.kind);
}

/**
 * What heads a run: the name of its function — never its code of the FBS, an internal key the user
 * has no use for (decision of the author on #515, 2026-10-08) —, or the kind of its actions, for a
 * function the navigation does not know.
 */
function RunHeading({ head }: { readonly head: Permission }) {
  const t = useTranslations();
  const fbs = head.fbs_code ?? null;
  const fn = fbs === null ? undefined : functionAt(fbs);
  return fn === undefined ? t(`enums.Permission.kind.${head.kind}`) : t(fn.label);
}

/** Whether a role holds a permission — said by a mark and a word, not by colour. */
function Held({ held }: { readonly held: boolean }) {
  const t = useTranslations("admin.permissions");
  return held ? (
    <span className="inline-flex items-center gap-1.5">
      <Check aria-hidden="true" className={ICON} />
      <span className="sr-only">{t("held")}</span>
    </span>
  ) : (
    <span className="sr-only">{t("notHeld")}</span>
  );
}

/**
 * The matrix of the permissions: a row for each permission of the catalogue, under the function it
 * covers, a column for each access role.
 */
export function PermissionMatrix({
  permissions,
  roles,
}: {
  readonly permissions: readonly Permission[];
  readonly roles: readonly AccessRole[];
}) {
  const t = useTranslations();
  const title = t("admin.permissions.title");
  // What each role holds, as the server lists it.
  const holds = roles.map((role) => ({ role, codes: new Set<string>(role.permissions) }));
  return (
    <ReferenceSection title={title} icon={KeyRound}>
      <Table aria-label={title} className="w-full">
        <TableHeader>
          <TableRow>
            <TableHead className={CELL}>{t("admin.permissions.function")}</TableHead>
            <TableHead className={CELL}>{t("admin.permissions.permission")}</TableHead>
            {roles.map((role) => (
              <TableHead key={role.access_role_id} className={`${CELL} text-center`}>
                {role.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        {runsOf(permissions).map((run) => (
          <TableBody key={run[0]?.code} className="border-t">
            {run.map((permission, at) => (
              <TableRow key={permission.code}>
                {at === 0 ? (
                  <TableHead scope="rowgroup" rowSpan={run.length} className={`${CELL} align-top`}>
                    <RunHeading head={permission} />
                  </TableHead>
                ) : null}
                <TableHead scope="row" className={`${CELL} font-normal`}>
                  {t(`permissions.${permission.code}`)}
                </TableHead>
                {holds.map(({ role, codes }) => (
                  <TableCell key={role.access_role_id} className={`${CELL} text-center`}>
                    <Held held={codes.has(permission.code)} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        ))}
      </Table>
    </ReferenceSection>
  );
}
