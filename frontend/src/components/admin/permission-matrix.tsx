// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The matrix of the permissions (FBS-1.2, WF-ADM-0100, US-0380): a row for each permission of the
 * catalogue as `listPermissions` gives it, gathered under the name of the function of the second
 * level it covers — or the kind of the action it guards —, a column for each role the table of the
 * roles retains, in its order, which holds it or not. No screen creates a permission.
 *
 * It is the place of the modification of the permissions (#380): for a session that may modify the
 * roles, each cell is a checkbox, named after its permission and its role, which writes the role
 * whole — its label, its permissions in the order of the catalogue, the version read
 * (`updateAccessRole`). Any set of permissions may be composed (WF-ADM-0020). The cell shows what
 * was asked until the server answers, and the other cells of the role wait for the answer, which
 * carries the version the next write goes from: the role answered prevails over the role read while
 * it is newer, by its counter. A refusal is told above the matrix by the catalogue of the codes of
 * error — the last administrator (`LAST_ADMINISTRATOR`, WF-ADM-0120), the version stale (412) with
 * the offer to read the page anew —, on the reading it was asked from alone (`Reactivations`), and
 * the cell shows the role as it was. Every write answered reads the page anew (`access-roles.ts`).
 */
"use client";

import { Check, KeyRound } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { updateAccessRole } from "@/api/actions/access-roles";
import type { components } from "@/api/generated/schema";
import { rejected } from "@/components/commands/rejection";
import { CELL, ICON } from "@/components/projects/project-tables";
import { Reactivations, useListReport } from "@/components/reference/reactivation";
import { ReferenceSection } from "@/components/reference/section";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { functionAt } from "@/navigation/functions";

import { ROLE_READS } from "./role-address";

type AccessRole = components["schemas"]["AccessRole"];
type Permission = components["schemas"]["Permission"];
type PermissionCode = components["schemas"]["PermissionCode"];

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

/** A role as the matrix shows it, and the permissions it holds — those asked, while written. */
interface Holding {
  readonly role: AccessRole;
  readonly codes: ReadonlySet<PermissionCode>;
  readonly writing: boolean;
}

/**
 * The roles as the matrix shows them: each the newest of the role read and the role the server
 * answered, by its counter, with the permissions asked of it while they are written.
 */
function holdings(
  roles: readonly AccessRole[],
  answered: ReadonlyMap<string, AccessRole>,
  writing: ReadonlyMap<string, ReadonlySet<PermissionCode>>,
): Holding[] {
  return roles.map((read) => {
    const answer = answered.get(read.access_role_id);
    const role = answer !== undefined && answer.lock_version > read.lock_version ? answer : read;
    const asked = writing.get(role.access_role_id);
    return { role, codes: asked ?? new Set(role.permissions), writing: asked !== undefined };
  });
}

/** The permissions of a role and the version read, written by the cells of its column. */
function useRoleWrites(permissions: readonly Permission[]) {
  const list = useListReport();
  const [answered, setAnswered] = useState<ReadonlyMap<string, AccessRole>>(() => new Map());
  const [writing, setWriting] = useState<ReadonlyMap<string, ReadonlySet<PermissionCode>>>(
    () => new Map(),
  );
  const write = ({ role, codes, writing: busy }: Holding, code: PermissionCode, held: boolean) => {
    if (busy) {
      return;
    }
    const id = role.access_role_id;
    const asked = new Set(codes);
    if (held) {
      asked.add(code);
    } else {
      asked.delete(code);
    }
    setWriting((before) => new Map(before).set(id, asked));
    // The reading the cell is checked on: its refusal is told on it alone.
    const reading = list?.reading ?? "";
    const sent = permissions.map((permission) => permission.code).filter((each) => asked.has(each));
    void updateAccessRole(id, {
      label: role.label,
      permissions: sent,
      lock_version: role.lock_version,
    })
      .catch(rejected)
      .then((outcome) => {
        setWriting((before) => {
          const after = new Map(before);
          after.delete(id);
          return after;
        });
        if (outcome.kind === "done") {
          setAnswered((before) => {
            const known = before.get(id);
            return known !== undefined && known.lock_version >= outcome.data.lock_version
              ? before
              : new Map(before).set(id, outcome.data);
          });
        } else {
          list?.report({ outcome, reading, names: {}, target: `permissions ${id}` });
        }
      });
  };
  return { answered, writing, write };
}

/**
 * The cells of the matrix, each whether a role holds a permission: a checkbox that writes it, for a
 * session that may modify the roles, said otherwise by a mark and a word.
 */
function MatrixBody({
  permissions,
  roles,
  editable,
}: {
  readonly permissions: readonly Permission[];
  readonly roles: readonly AccessRole[];
  readonly editable: boolean;
}) {
  const t = useTranslations();
  const { answered, writing, write } = useRoleWrites(permissions);
  const holds = holdings(roles, answered, writing);
  return (
    <Table aria-label={t("admin.permissions.title")} className="w-full">
      <TableHeader>
        <TableRow>
          <TableHead className={CELL}>{t("admin.permissions.function")}</TableHead>
          <TableHead className={CELL}>{t("admin.permissions.permission")}</TableHead>
          {holds.map(({ role }) => (
            <TableHead key={role.access_role_id} className={`${CELL} text-center`}>
              {role.label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      {runsOf(permissions).map((run) => (
        <TableBody key={run[0]?.code} className="border-t">
          {run.map((permission, at) => {
            const name = t(`permissions.${permission.code}`);
            return (
              <TableRow key={permission.code}>
                {at === 0 ? (
                  <TableHead scope="rowgroup" rowSpan={run.length} className={`${CELL} align-top`}>
                    <RunHeading head={permission} />
                  </TableHead>
                ) : null}
                <TableHead scope="row" className={`${CELL} font-normal`}>
                  {name}
                </TableHead>
                {holds.map((holding) => {
                  const held = holding.codes.has(permission.code);
                  return (
                    <TableCell key={holding.role.access_role_id} className={`${CELL} text-center`}>
                      {editable ? (
                        <Checkbox
                          checked={held}
                          aria-label={t("admin.permissions.cell", {
                            permission: name,
                            role: holding.role.label,
                          })}
                          aria-busy={holding.writing}
                          aria-disabled={holding.writing ? true : undefined}
                          className="align-middle aria-disabled:opacity-50"
                          onCheckedChange={(checked) => {
                            write(holding, permission.code, checked === true);
                          }}
                        />
                      ) : (
                        <Held held={held} />
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            );
          })}
        </TableBody>
      ))}
    </Table>
  );
}

/**
 * The matrix of the permissions: a row for each permission of the catalogue, under the function it
 * covers, a column for each access role the table retains; written, for a session that may modify
 * the roles.
 */
export function PermissionMatrix({
  permissions,
  roles,
  editable,
}: {
  readonly permissions: readonly Permission[];
  /** The roles the table retains, in its order. */
  readonly roles: readonly AccessRole[];
  /** Whether the session may modify the access roles (`platformOffer`). */
  readonly editable: boolean;
}) {
  const t = useTranslations("admin.permissions");
  return (
    <ReferenceSection title={t("title")} icon={KeyRound}>
      {editable ? (
        <Reactivations reads={ROLE_READS}>
          <MatrixBody permissions={permissions} roles={roles} editable />
        </Reactivations>
      ) : (
        <MatrixBody permissions={permissions} roles={roles} editable={false} />
      )}
    </ReferenceSection>
  );
}
