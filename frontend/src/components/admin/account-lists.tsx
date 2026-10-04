// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The accounts and the access roles (FBS-1.1, FBS-1.2, US-0250), in dense tables, in the order
 * the server gave them: each account with its origin, its access roles and the node it is attached
 * to — named as the server resolves them — and whether it is active, a deactivated one staying
 * listed (WF-ADM-0050, WF-ADM-0060); each access role, predefined or composed, with how many
 * accounts hold it (WF-ADM-0010, WF-ADM-0090); and the matrix of the permissions, a row for each
 * permission of the catalogue as `listPermissions` gives it, gathered under the function of the
 * second level it covers — or the kind of the action it guards —, a column for each role, which
 * holds it or not (WF-ADM-0100). Read only: the forms belong to the epic of the administration,
 * and no screen creates a permission.
 */
import { Check, KeyRound, ShieldCheck, Users } from "lucide-react";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import type { ListPage } from "@/components/admin/list-pages";
import { CELL, ICON, ListTable } from "@/components/projects/project-tables";
import { ActiveState, ReferenceSection } from "@/components/reference/section";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { functionAt } from "@/navigation/functions";

type User = components["schemas"]["User"];
type AccessRole = components["schemas"]["AccessRole"];
type Permission = components["schemas"]["Permission"];

/**
 * The accounts of a page of the list, or that the installation has none — only when the list holds
 * none at all: a page asked beyond its end is no empty list, and shows no table; its pages say where
 * it stands (`ListPages`).
 */
export function UserList({
  users,
  page,
}: {
  readonly users: readonly User[];
  readonly page: ListPage;
}) {
  const t = useTranslations("admin.users");
  const columns = useTranslations("reference.columns");
  const origins = useTranslations("enums.UserOrigin");
  return (
    <ReferenceSection
      title={t("title")}
      icon={Users}
      empty={page.total === 0 ? t("none") : undefined}
    >
      {users.length === 0 ? null : (
        <ListTable
          label={t("title")}
          columns={[
            t("lastName"),
            t("firstName"),
            t("email"),
            t("origin"),
            t("roles"),
            t("orgNode"),
            columns("state"),
          ]}
        >
          {users.map((user) => (
            <TableRow key={user.user_id}>
              <TableCell className={CELL}>{user.last_name}</TableCell>
              <TableCell className={CELL}>{user.first_name}</TableCell>
              <TableCell className={CELL}>{user.email}</TableCell>
              <TableCell className={CELL}>{origins(user.origin)}</TableCell>
              <TableCell className={CELL}>
                {user.access_role_labels.length === 0 ? (
                  <span className="text-muted-foreground">{t("noRole")}</span>
                ) : (
                  <ul className="flex flex-wrap gap-1">
                    {user.access_role_labels.map((label, at) => (
                      <li key={user.access_role_ids[at] ?? label}>
                        <Badge variant="secondary">{label}</Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </TableCell>
              <TableCell className={CELL}>
                {user.org_node_label ?? (
                  <span className="text-muted-foreground">{t("noOrgNode")}</span>
                )}
              </TableCell>
              <TableCell className={CELL}>
                <ActiveState active={user.is_active} />
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      )}
    </ReferenceSection>
  );
}

/** The access roles, each predefined or composed, with how many accounts hold it. */
export function AccessRoleList({ roles }: { readonly roles: readonly AccessRole[] }) {
  const t = useTranslations("admin.accessRoles");
  const columns = useTranslations("reference.columns");
  return (
    <ReferenceSection
      title={t("title")}
      icon={ShieldCheck}
      empty={roles.length === 0 ? t("none") : undefined}
    >
      <ListTable label={t("title")} columns={[columns("label"), t("kind"), t("holders")]}>
        {roles.map((role) => (
          <TableRow key={role.access_role_id}>
            <TableCell className={CELL}>{role.label}</TableCell>
            <TableCell className={CELL}>
              {role.is_predefined ? t("predefined") : t("composed")}
            </TableCell>
            <TableCell className={`${CELL} text-right tabular-nums`}>{role.holder_count}</TableCell>
          </TableRow>
        ))}
      </ListTable>
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

/** What heads a run: the code and the name of its function, or the kind of its actions. */
function RunHeading({ head }: { readonly head: Permission }) {
  const t = useTranslations();
  const fbs = head.fbs_code ?? null;
  if (fbs === null) {
    return t(`enums.Permission.kind.${head.kind}`);
  }
  const fn = functionAt(fbs);
  return (
    <span className="flex flex-col">
      <span className="text-xs text-muted-foreground tabular-nums">{fbs}</span>
      {fn === undefined ? null : <span>{t(fn.label)}</span>}
    </span>
  );
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
