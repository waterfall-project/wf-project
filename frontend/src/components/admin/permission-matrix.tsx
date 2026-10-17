// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The matrix of the permissions as the place of their modification (US-0380, #380): each cell a
 * checkbox that writes its role whole — its label, its permissions in the order of the catalogue, the
 * version the screen holds (`updateAccessRole`), any set of them (WF-ADM-0020). The cell shows what
 * was asked until the server answers, the other cells of the role waiting for the answer, which the
 * screen keeps for the matrix and the table alike (`RoleAnswers`): the next write, a cell or a
 * renaming, goes from its version. A refusal is told above the matrix by the catalogue of the codes
 * of error, on the reading it was asked from alone (`Reactivations`), the cell showing the role as it
 * was, and taking the focus back once the refusal is dismissed.
 */
"use client";

import { useTranslations } from "next-intl";
import { createContext, type ReactNode, useContext, useRef, useState } from "react";

import { updateAccessRole } from "@/api/actions/access-roles";
import type { components } from "@/api/generated/schema";
import { rejected } from "@/components/commands/rejection";
import { Reactivations, useListReport } from "@/components/reference/reactivation";
import { Checkbox } from "@/components/ui/checkbox";

import { ROLE_READS } from "./role-address";
import { newer, RoleAnswers, useRoleAnswers } from "./role-answers";

type AccessRole = components["schemas"]["AccessRole"];
type PermissionCode = components["schemas"]["PermissionCode"];

/** What a role holds as the matrix shows it, and whether a write of it is under way. */
interface Holding {
  readonly role: AccessRole;
  readonly codes: ReadonlySet<PermissionCode>;
  readonly writing: boolean;
}

/** The roles of the matrix as they show, and how a cell writes one. */
interface Writes {
  readonly holding: (role: string) => Holding | undefined;
  readonly write: (
    holding: Holding,
    code: PermissionCode,
    held: boolean,
    cell: HTMLElement | null,
  ) => void;
}

const WritesContext = createContext<Writes | undefined>(undefined);

/** The roles the matrix shows, the codes of the catalogue in its order, and the matrix. */
interface WritesProps {
  readonly order: readonly PermissionCode[];
  readonly roles: readonly AccessRole[];
  readonly children: ReactNode;
}

/**
 * The writes of the permissions of the roles the matrix shows, from the roles the screen holds
 * (`RoleAnswers`), and their refusals told above it.
 */
export function MatrixWrites(props: WritesProps) {
  return (
    <RoleAnswers>
      <Reactivations reads={ROLE_READS}>
        <Writing {...props} />
      </Reactivations>
    </RoleAnswers>
  );
}

/**
 * The permissions asked, by role, the roles as the screen holds them — read, or answered since —, and
 * the writes that change them.
 */
function Writing({ order, roles, children }: WritesProps) {
  const list = useListReport();
  const answers = useRoleAnswers();
  const [asked, setAsked] = useState<ReadonlyMap<string, ReadonlySet<PermissionCode>>>(
    () => new Map(),
  );
  const holding = (id: string): Holding | undefined => {
    const read = roles.find((role) => role.access_role_id === id);
    if (read === undefined) {
      return undefined;
    }
    const role = newer(read, answers?.answered.get(id));
    const codes = asked.get(id);
    return { role, codes: codes ?? new Set(role.permissions), writing: codes !== undefined };
  };
  const write = (
    { role: shown, writing }: Holding,
    code: PermissionCode,
    held: boolean,
    cell: HTMLElement | null,
  ) => {
    if (writing) {
      return;
    }
    // The role as the screen holds it now: an answer may have arrived since the last render.
    const role = answers?.latest(shown) ?? shown;
    const id = role.access_role_id;
    const next = new Set(role.permissions);
    if (held) {
      next.add(code);
    } else {
      next.delete(code);
    }
    setAsked((before) => new Map(before).set(id, next));
    // The reading the cell is checked on: its refusal is told on it alone.
    const generation = list?.generation ?? 0;
    const permissions = order.filter((each) => next.has(each));
    void updateAccessRole(id, { label: role.label, permissions, lock_version: role.lock_version })
      .catch(rejected)
      .then((outcome) => {
        setAsked((before) => {
          const after = new Map(before);
          after.delete(id);
          return after;
        });
        if (outcome.kind === "done") {
          answers?.record(outcome.data);
        } else {
          list?.report({ outcome, generation, names: {}, target: `permissions ${id}`, back: cell });
        }
      });
  };
  return <WritesContext value={{ holding, write }}>{children}</WritesContext>;
}

/**
 * The label of a role at the head of its column, as the screen holds the role: the one read, or the
 * one a renaming answered since, until the page read anew holds it (#976).
 */
export function RoleLabel({ role }: { readonly role: AccessRole }) {
  const answers = useRoleAnswers();
  return newer(role, answers?.answered.get(role.access_role_id)).label;
}

/**
 * The cell of a permission for a role: a checkbox that writes the role, named after both — the role
 * by its label as the screen holds it, a renaming answered included (#976).
 */
export function PermissionCell({
  role,
  code,
  permission,
}: {
  readonly role: string;
  readonly code: PermissionCode;
  /** The name of the permission, in the language of the screen. */
  readonly permission: string;
}) {
  const t = useTranslations("admin.permissions");
  const writes = useContext(WritesContext);
  const checkbox = useRef<HTMLButtonElement>(null);
  const holding = writes?.holding(role);
  if (holding === undefined) {
    return null;
  }
  return (
    <Checkbox
      ref={checkbox}
      checked={holding.codes.has(code)}
      aria-label={t("cell", { permission, role: holding.role.label })}
      aria-busy={holding.writing}
      aria-disabled={holding.writing ? true : undefined}
      className="align-middle aria-disabled:opacity-50"
      onCheckedChange={(checked) => {
        writes?.write(holding, code, checked === true, checkbox.current);
      }}
    />
  );
}
