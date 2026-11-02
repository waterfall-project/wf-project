// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configurations of the dense grids of the administration (#514, #515): the accounts (FBS-1.1)
 * and the access roles (FBS-1.2), each alone on its screen, under the names of the contract in the
 * address, each with the key of its settings in the account (WF-ADM-0040). Both are flat tables
 * whose every column the server sorts both ways (WF-IHM-0060), and which it searches — the roles on
 * their label, the accounts on their last name, first name, address and display name.
 *
 * - The accounts: each with its origin, the node it is attached to and its access roles — named
 *   as the server resolves them — and whether it is active, a deactivated one staying listed
 *   (WF-ADM-0050, WF-ADM-0060). The server pages them. For a session that may modify the accounts,
 *   the table is its own entry (US-0360, #379): the names of a local account in their cells, its
 *   state on a switch, its roles in a list of several choices, the link of a local account and its
 *   anonymisation on commands (`user-cells.tsx`) — none deletes an account —, the state, the roles
 *   and the anonymisation as the account lists their commands (`available_commands`): the
 *   deactivation of the last administrator unavailable (WF-ADM-0120); the anonymisation offered to a
 *   deactivated account only, and the reactivation and the anonymisation of an anonymised one
 *   unavailable (WF-ADM-0060). An anonymised account has neither name nor address: it shows the
 *   neutral label in place of its last name, nothing for the rest, and its names are not entered.
 * - The access roles: each predefined or composed, with how many accounts hold it (WF-ADM-0010,
 *   WF-ADM-0090); for a session that may modify the roles, its label entered in its cell and the
 *   command to delete it (`DeleteRole`) — unavailable while an account holds it (US-0380, #380).
 *
 * Both end on their audit columns (WF-DAT-0070, #936): when each row was created and last modified,
 * and by whom — an account deactivated since still named, an anonymised one by the neutral label,
 * the platform by its own (WF-ADM-0060).
 *
 * The server filters each on its columns (WF-IHM-0130, EP-02/L42f): the accounts by their origin,
 * their node, their access roles — one at least of those chosen — and their state; the roles by
 * their kind and between bounds of their holders, deactivated accounts counted; both by the period
 * and the author of their creation and of their last modification (`audit-address.ts`); the filters
 * of both kept with the settings of their grid (US-0360, US-0380).
 *
 * Neither server nor client: the page reads the keys and the columns sorted; the grids, in the
 * browser, the rest — the functions that read a row never cross to the server.
 */
import { useTranslations } from "next-intl";

import { updateAccessRole } from "@/api/actions/access-roles";
import { updateUser } from "@/api/actions/users";
import type { components, operations } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { KeptName } from "@/components/account/anonymized-name";
import {
  type CellEntry,
  type GridColumn,
  type GridConfig,
  type RowsWritten,
  sortColumns,
} from "@/components/grid/columns";
import { CONTRACT_ADDRESS } from "@/components/grid/query";
import { ActiveState } from "@/components/reference/section";

import { auditColumns } from "./audit-columns";
import { DeleteRole } from "./role-commands";
import { LABEL_LENGTH, ROLE_FILTERS } from "./role-address";
import {
  AnonymizeCommand,
  HeldRoles,
  RolesCell,
  ResendInvitationCommand,
  SetupLinkCommand,
  StateSwitch,
} from "./user-cells";
import { NAME_LENGTH, USER_FILTERS } from "./user-address";

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

/** The last name of an account, or the neutral label of an anonymised one, which has none. */
function LastName({ user }: { readonly user: User }) {
  return <KeptName name={user.last_name} />;
}

/** An access role an account may hold or be filtered by, by its identifier and its label. */
export interface RoleChoice {
  readonly id: string;
  readonly label: string;
}

/**
 * The writing of a name entered, within the writes of its row (`UserWrites.queue`): sent once those
 * under way are answered, from the version they left, its answer kept and said in the region of the
 * table.
 */
export type Renaming = (
  shown: User,
  send: (user: User) => Promise<Outcome<User>>,
) => Promise<Outcome<User>>;

/** The origin of an account, in words. */
function Origin({ user }: { readonly user: User }) {
  const t = useTranslations("enums.UserOrigin");
  return t(user.origin);
}

/** The node an account is attached to, as the server names it, or that it is attached to none. */
function Attachment({ user }: { readonly user: User }) {
  const t = useTranslations("admin.users");
  return user.org_node_label ?? <span className="text-muted-foreground">{t("noOrgNode")}</span>;
}

/** The width of a column of a command, its button. */
const COMMAND_WIDTH = 120;

/**
 * The entry of a name of a local account in its cell — the last name or the first name, never blank
 * —, written after the writes of its row under way, from the version they leave of the account
 * (`updateUser`, `Renaming`): the name of an account of the directory or of an identity provider is
 * theirs, and is not entered (WF-ADM-0050); an anonymised account has none to enter (WF-ADM-0060).
 */
function naming(
  field: "last_name" | "first_name",
  rename: Renaming | undefined,
): CellEntry<User, UserPage> {
  let answered = 0;
  return {
    kind: { type: "text", maxLength: NAME_LENGTH },
    in: (user) => user.origin === "local" && user.anonymized_at === null,
    value: (user) => user[field],
    write: async (shown, name): Promise<Outcome<RowsWritten<User, UserPage>>> => {
      if (name === null) {
        // A text entered is never emptied (`cell-values.ts`): a defect of the front.
        throw new Error("an account is never left without a name");
      }
      const send = (user: User) =>
        updateUser(user.user_id, { [field]: name, lock_version: user.lock_version });
      const outcome = await (rename === undefined ? send(shown) : rename(shown, send));
      if (outcome.kind !== "done") {
        return outcome;
      }
      answered += 1;
      const written = { rows: [outcome.data], changed: [], parts: [], totals: undefined };
      return { kind: "done", data: { ...written, order: answered } };
    },
  };
}

/** The column of the link of a local account, for a session that may modify the accounts. */
function setupLinkColumn(): GridColumn<User, UserSort, UserPage> {
  return {
    key: "password_link",
    label: "passwordLink",
    help: "users.password_link",
    format: "text",
    width: COMMAND_WIDTH,
    value: () => null,
    render: (user) => <SetupLinkCommand user={user} />,
  };
}

/** The column of the email of the link of a local account, for a session that may modify the accounts. */
function resendColumn(): GridColumn<User, UserSort, UserPage> {
  return {
    key: "resend_invitation",
    label: "resendInvitation",
    help: "users.resend_invitation",
    format: "text",
    width: COMMAND_WIDTH,
    value: () => null,
    render: (user) => <ResendInvitationCommand user={user} />,
  };
}

/** The column of the anonymisation of an account, for a session that may modify the accounts. */
function anonymizeColumn(): GridColumn<User, UserSort, UserPage> {
  return {
    key: "anonymize",
    label: "anonymize",
    help: "users.anonymize",
    format: "text",
    width: COMMAND_WIDTH,
    value: () => null,
    render: (user) => <AnonymizeCommand user={user} />,
  };
}

/** What the grid of the accounts writes with, for a session that may modify them. */
export interface UserEntry {
  /** The roles of the installation an account may be given, read by the cell alone (défaut n° 14). */
  readonly roles: () => readonly RoleChoice[];
  /** The writing of a name entered within the writes of its row (`UserWrites.queue`). */
  readonly rename: Renaming | undefined;
}

/**
 * The grid of the accounts — searched by the server on the last name, the first name, the address
 * and the first name followed by the last name, its search named after it, the accounts having no
 * label —, in the order of #379: the names, the address, the origin, the node, the roles and the
 * state; then its audit columns, the creation and the last modification, each its instant and its
 * author (`auditColumns`, #936). For a session that may modify the accounts, it is its own entry
 * (`entry`): the names of a local account in their cells, the state on a switch, the roles in a list
 * of several choices, and the link of a local account and the anonymisation of a deactivated one on
 * their commands — none deletes an account (WF-ADM-0060).
 */
export function userGrid(entry?: UserEntry): GridConfig<User, UserSort, UserPage> {
  return {
    key: USER_GRID_KEY,
    name: "users",
    address: CONTRACT_ADDRESS,
    searched: true,
    paged: true,
    rowKey: (user) => user.user_id,
    filters: USER_FILTERS,
    // An account answered prevails over the same account read while it is newer, by its counter.
    fresher: (answered, read) =>
      answered.lock_version === read.lock_version
        ? undefined
        : answered.lock_version > read.lock_version,
    columns: [
      {
        key: "last_name",
        label: "lastName",
        help: "users.lastName",
        format: "text",
        width: 160,
        pinned: true,
        contract: "last_name",
        value: (user) => user.last_name,
        render: (user) => <LastName user={user} />,
        entry: entry === undefined ? undefined : naming("last_name", entry.rename),
      },
      {
        key: "first_name",
        label: "firstName",
        help: "users.firstName",
        format: "text",
        width: 140,
        contract: "first_name",
        value: (user) => user.first_name,
        entry: entry === undefined ? undefined : naming("first_name", entry.rename),
      },
      {
        key: "email",
        label: "email",
        help: "users.email",
        format: "text",
        width: 260,
        contract: "email",
        value: (user) => user.email,
      },
      {
        key: "origin",
        label: "origin",
        help: "users.origin",
        format: "text",
        width: 230,
        contract: "origin",
        value: (user) => user.origin,
        render: (user) => <Origin user={user} />,
      },
      {
        key: "org_node",
        label: "attachment",
        help: "users.attachment",
        format: "text",
        width: 220,
        contract: "org_node",
        value: (user) => user.org_node_label,
        render: (user) => <Attachment user={user} />,
      },
      {
        key: "access_roles",
        label: "accessRoles",
        help: "users.accessRoles",
        format: "text",
        width: 240,
        contract: "access_roles",
        value: (user) => user.access_role_labels[0],
        render: (user) =>
          entry === undefined ? (
            <HeldRoles labels={user.access_role_labels} />
          ) : (
            <RolesCell user={user} roles={entry.roles()} />
          ),
      },
      {
        key: "is_active",
        label: "state",
        help: "users.state",
        format: "text",
        width: 140,
        contract: "is_active",
        value: (user) => (user.is_active ? "active" : "inactive"),
        render: (user) =>
          entry === undefined ? (
            <ActiveState active={user.is_active} />
          ) : (
            <StateSwitch user={user} />
          ),
      },
      ...auditColumns<User, UserPage>(),
      ...(entry === undefined ? [] : [setupLinkColumn(), resendColumn(), anonymizeColumn()]),
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
    help: "accessRoles.delete",
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
 * The grid of the access roles: the label, the kind, the number of accounts that hold it, its audit
 * columns (`auditColumns`, #936) — each sorted by the server —, and, for a session that may modify
 * the roles, its commands, its renaming writing from the roles the screen holds (`answers`).
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
        help: "accessRoles.label",
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
        help: "accessRoles.roleKind",
        format: "text",
        width: 130,
        contract: "is_predefined",
        value: (role) => (role.is_predefined ? "predefined" : "composed"),
        render: (role) => <RoleKind role={role} />,
      },
      {
        key: "holder_count",
        label: "holders",
        help: "accessRoles.holders",
        format: "decimal",
        width: 150,
        contract: "holder_count",
        value: (role) => role.holder_count.toString(),
      },
      ...auditColumns<AccessRole, null>(),
      ...(editable ? commandColumns() : []),
    ],
  };
}

/** The columns of the contract the server sorts the accounts and the roles by. */
export const USER_SORTS = sortColumns(userGrid());
export const ACCESS_ROLE_SORTS = sortColumns(accessRoleGrid(false));
