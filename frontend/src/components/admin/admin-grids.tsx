// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configurations of the dense grids of the administration (#514, #515): the accounts (FBS-1.1)
 * and the access roles (FBS-1.2), each alone on its screen, under the names of the contract in the
 * address, each with the key of its settings in the account (WF-ADM-0040). Both are flat tables
 * whose every column the server sorts both ways (WF-IHM-0060), and which it searches — the roles on
 * their label, the accounts on their last name, first name, address and display name.
 *
 * - The accounts: each with its origin, its access roles and the node it is attached to — named
 *   as the server resolves them — and whether it is active, a deactivated one staying listed
 *   (WF-ADM-0050, WF-ADM-0060). The server pages them. For a session that may modify the accounts,
 *   the commands to modify each, to deactivate or reactivate it, and to attribute its roles, which
 *   EP-03 wires (`UserCommand`) — none deletes an account —, the last two as the account lists them
 *   (`available_commands`): the deactivation of the last administrator unavailable (WF-ADM-0120).
 * - The access roles: each predefined or composed, with how many accounts hold it (WF-ADM-0010,
 *   WF-ADM-0090); for a session that may modify the roles, its label entered in its cell and the
 *   command to delete it (`DeleteRole`) — unavailable while an account holds it (US-0380, #380).
 *
 * The server filters each on its columns (WF-IHM-0130, EP-02/L42f): the accounts by their origin,
 * their node, their access roles — one at least of those chosen — and their state; the roles by
 * their kind and between bounds of their holders, deactivated accounts counted, and kept (US-0380).
 *
 * Neither server nor client: the page reads the keys and the columns sorted; the grids, in the
 * browser, the rest — the functions that read a row never cross to the server.
 */
import { useTranslations } from "next-intl";

import { updateAccessRole } from "@/api/actions/access-roles";
import type { components, operations } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import {
  type CellEntry,
  type GridColumn,
  type GridConfig,
  type RowsWritten,
  sortColumns,
} from "@/components/grid/columns";
import { CONTRACT_ADDRESS } from "@/components/grid/query";
import { ActiveState } from "@/components/reference/section";
import { Badge } from "@/components/ui/badge";

import { UserCommand, type UserCommandName } from "./later-commands";
import { DeleteRole } from "./role-commands";
import { LABEL_LENGTH, ROLE_FILTERS } from "./role-address";

/** An account, as the contract gives it. */
export type User = components["schemas"]["User"];

/** An access role, as the contract gives it. */
export type AccessRole = components["schemas"]["AccessRole"];

/** Where a page stands in the accounts the server retained: their number, the totals row's. */
export type UserPage = components["schemas"]["PaginationMeta"];

/**
 * The roles the server answered a write with, shared by the table and the matrix of the screen
 * (`RoleAnswers`): read in an event, and recorded once answered.
 */
export interface RoleAnswered {
  /** The role as it stands now: the one last answered, or the one read when it is as new. */
  readonly latest: (read: AccessRole) => AccessRole;
  /** Keep a role answered, unless one newer is kept. */
  readonly record: (answered: AccessRole) => void;
}

/** The column of the contract the server sorts the accounts by. */
export type UserSort = NonNullable<
  NonNullable<operations["listUsers"]["parameters"]["query"]>["sort_by"]
>;

/** The column of the contract the server sorts the access roles by. */
export type AccessRoleSort = NonNullable<
  NonNullable<operations["listAccessRoles"]["parameters"]["query"]>["sort_by"]
>;

/** The keys of the settings of the two grids in the account: stable. */
export const USER_GRID_KEY = "users";
export const ACCESS_ROLE_GRID_KEY = "access_roles";

/** The origin of an account, in words. */
function Origin({ user }: { readonly user: User }) {
  const t = useTranslations("enums.UserOrigin");
  return t(user.origin);
}

/** The access roles of an account, as the server names them, or that it holds none. */
function HeldRoles({ user }: { readonly user: User }) {
  const t = useTranslations("admin.users");
  return user.access_role_labels.length === 0 ? (
    <span className="text-muted-foreground">{t("noRole")}</span>
  ) : (
    <span className="flex gap-1">
      {user.access_role_labels.map((label, at) => (
        <Badge key={user.access_role_ids[at] ?? label} variant="secondary">
          {label}
        </Badge>
      ))}
    </span>
  );
}

/** The node an account is attached to, as the server names it, or that it is attached to none. */
function Attachment({ user }: { readonly user: User }) {
  const t = useTranslations("admin.users");
  return user.org_node_label ?? <span className="text-muted-foreground">{t("noOrgNode")}</span>;
}

/** The width of a column of a command, its button. */
const COMMAND_WIDTH = 120;

/** A command of an account, which names it as the list does. */
function UserCommandCell({
  user,
  command,
}: {
  readonly user: User;
  readonly command: UserCommandName;
}) {
  const t = useTranslations("admin.users");
  return (
    <UserCommand
      command={command}
      name={t("named", { firstName: user.first_name, lastName: user.last_name })}
      offers={user.available_commands}
    />
  );
}

/** The columns of the commands of an account, for a session that may modify the accounts. */
function userCommandColumns(): GridColumn<User, UserSort, UserPage>[] {
  return (
    [
      ["modify", "modify", COMMAND_WIDTH],
      ["activation", "activation", COMMAND_WIDTH],
      ["assignRoles", "assignRoles", 170],
    ] as const
  ).map(([command, label, width]) => ({
    key: command,
    label,
    format: "text",
    width,
    value: () => null,
    render: (user) => <UserCommandCell user={user} command={command} />,
  }));
}

/**
 * The grid of the accounts — searched by the server on the last name, the first name, the address
 * and the display name, its search named after it, the accounts having no label — and, for a
 * session that may modify the accounts, their commands.
 */
export function userGrid(editable: boolean): GridConfig<User, UserSort, UserPage> {
  return {
    key: USER_GRID_KEY,
    name: "users",
    address: CONTRACT_ADDRESS,
    searched: true,
    rowKey: (user) => user.user_id,
    columns: [
      {
        key: "last_name",
        label: "lastName",
        format: "text",
        width: 160,
        pinned: true,
        contract: "last_name",
        value: (user) => user.last_name,
      },
      {
        key: "first_name",
        label: "firstName",
        format: "text",
        width: 140,
        contract: "first_name",
        value: (user) => user.first_name,
      },
      {
        key: "email",
        label: "email",
        format: "text",
        width: 260,
        contract: "email",
        value: (user) => user.email,
      },
      {
        key: "origin",
        label: "origin",
        format: "text",
        width: 230,
        contract: "origin",
        value: (user) => user.origin,
        render: (user) => <Origin user={user} />,
      },
      {
        key: "access_roles",
        label: "accessRoles",
        format: "text",
        width: 220,
        contract: "access_roles",
        value: (user) => user.access_role_labels[0],
        render: (user) => <HeldRoles user={user} />,
      },
      {
        key: "org_node",
        label: "attachment",
        format: "text",
        width: 220,
        contract: "org_node",
        value: (user) => user.org_node_label,
        render: (user) => <Attachment user={user} />,
      },
      {
        key: "is_active",
        label: "state",
        format: "text",
        width: 120,
        contract: "is_active",
        value: (user) => (user.is_active ? "active" : "inactive"),
        render: (user) => <ActiveState active={user.is_active} />,
      },
      ...(editable ? userCommandColumns() : []),
    ],
  };
}

/** Whether an access role is predefined or composed, in words. */
function RoleKind({ role }: { readonly role: AccessRole }) {
  const t = useTranslations("admin.accessRoles");
  return role.is_predefined ? t("predefined") : t("composed");
}

/** The columns of the commands of a role, for a session that may modify the roles. */
function commandColumns(): GridColumn<AccessRole, AccessRoleSort, null>[] {
  return (["delete"] as const).map((command) => ({
    key: command,
    label: command,
    format: "text",
    width: COMMAND_WIDTH,
    value: () => null,
    render: (role) => <DeleteRole role={role} />,
  }));
}

/**
 * The renaming of a role in its cell, from the version the screen holds of it — the one read, or
 * one the matrix or a renaming answered since (`RoleAnswered`) —, with its permissions; the answer
 * kept for the matrix as for the table.
 */
function renaming(answers: RoleAnswered | undefined): CellEntry<AccessRole, null> {
  let answered = 0;
  return {
    kind: { type: "text", maxLength: LABEL_LENGTH },
    in: () => true,
    value: (role) => role.label,
    write: async (shown, label): Promise<Outcome<RowsWritten<AccessRole, null>>> => {
      if (label === null) {
        // A text entered is never emptied (`cell-values.ts`): a defect of the front.
        throw new Error("a role is never left without a label");
      }
      const role = answers?.latest(shown) ?? shown;
      const outcome = await updateAccessRole(role.access_role_id, {
        label,
        permissions: role.permissions,
        lock_version: role.lock_version,
      });
      if (outcome.kind !== "done") {
        return outcome;
      }
      answers?.record(outcome.data);
      answered += 1;
      const written = { rows: [outcome.data], changed: [], parts: [], totals: undefined };
      return { kind: "done", data: { ...written, order: answered } };
    },
  };
}

/**
 * The grid of the access roles: the label, the kind, the number of accounts that hold it — each
 * sorted by the server —, and, for a session that may modify the roles, its commands, its renaming
 * writing from the roles the screen holds (`answers`).
 */
export function accessRoleGrid(
  editable: boolean,
  answers?: RoleAnswered,
): GridConfig<AccessRole, AccessRoleSort, null> {
  return {
    key: ACCESS_ROLE_GRID_KEY,
    name: "accessRoles",
    searched: true,
    rowKey: (role) => role.access_role_id,
    filters: ROLE_FILTERS,
    // A role answered prevails over the same role read while it is newer, by its counter.
    fresher: (answered, read) =>
      answered.lock_version === read.lock_version
        ? undefined
        : answered.lock_version > read.lock_version,
    columns: [
      {
        key: "label",
        label: "label",
        format: "text",
        width: 240,
        pinned: true,
        contract: "label",
        value: (role) => role.label,
        entry: editable ? renaming(answers) : undefined,
      },
      {
        key: "is_predefined",
        label: "roleKind",
        format: "text",
        width: 130,
        contract: "is_predefined",
        value: (role) => (role.is_predefined ? "predefined" : "composed"),
        render: (role) => <RoleKind role={role} />,
      },
      {
        key: "holder_count",
        label: "holders",
        format: "decimal",
        width: 150,
        contract: "holder_count",
        value: (role) => role.holder_count.toString(),
      },
      ...(editable ? commandColumns() : []),
    ],
  };
}

/** The columns of the contract the server sorts the accounts and the roles by. */
export const USER_SORTS = sortColumns(userGrid(false));
export const ACCESS_ROLE_SORTS = sortColumns(accessRoleGrid(false));
