// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The matrix of the permissions as the place of their modification (US-0380, #380): each cell a
 * checkbox that writes its role whole — its label, its permissions in the order of the catalogue, the
 * version read (`updateAccessRole`), any set of them (WF-ADM-0020). The cell shows what was asked
 * until the server answers, the other cells of the role waiting for the answer, whose version the
 * next write goes from. A refusal is told above the matrix by the catalogue of the codes of error, on
 * the reading it was asked from alone (`Reactivations`), the cell showing the role as it was.
 */
"use client";

import { createContext, type ReactNode, useContext, useState } from "react";

import { updateAccessRole } from "@/api/actions/access-roles";
import type { components } from "@/api/generated/schema";
import { rejected } from "@/components/commands/rejection";
import { Reactivations, useListReport } from "@/components/reference/reactivation";
import { Checkbox } from "@/components/ui/checkbox";

import { ROLE_READS } from "./role-address";

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
  readonly write: (holding: Holding, code: PermissionCode, held: boolean) => void;
}

const WritesContext = createContext<Writes | undefined>(undefined);

/** The roles the matrix shows, the codes of the catalogue in its order, and the matrix. */
interface WritesProps {
  readonly order: readonly PermissionCode[];
  readonly roles: readonly AccessRole[];
  readonly children: ReactNode;
}

/** The writes of the permissions of the roles the matrix shows, and their refusals told above it. */
export function MatrixWrites(props: WritesProps) {
  return (
    <Reactivations reads={ROLE_READS}>
      <Writing {...props} />
    </Reactivations>
  );
}

/** The roles answered and the permissions asked, by role, and the writes that change them. */
function Writing({ order, roles, children }: WritesProps) {
  const list = useListReport();
  const [answered, setAnswered] = useState<ReadonlyMap<string, AccessRole>>(() => new Map());
  const [asked, setAsked] = useState<ReadonlyMap<string, ReadonlySet<PermissionCode>>>(
    () => new Map(),
  );
  const holding = (id: string): Holding | undefined => {
    const read = roles.find((role) => role.access_role_id === id);
    if (read === undefined) {
      return undefined;
    }
    const answer = answered.get(id);
    const role = answer !== undefined && answer.lock_version > read.lock_version ? answer : read;
    const codes = asked.get(id);
    return { role, codes: codes ?? new Set(role.permissions), writing: codes !== undefined };
  };
  const write = ({ role, codes, writing }: Holding, code: PermissionCode, held: boolean) => {
    if (writing) {
      return;
    }
    const id = role.access_role_id;
    const next = new Set(codes);
    if (held) {
      next.add(code);
    } else {
      next.delete(code);
    }
    setAsked((before) => new Map(before).set(id, next));
    // The reading the cell is checked on: its refusal is told on it alone.
    const reading = list?.reading ?? "";
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
          setAnswered((before) => new Map(before).set(id, outcome.data));
        } else {
          list?.report({ outcome, reading, names: {}, target: `permissions ${id}` });
        }
      });
  };
  return <WritesContext value={{ holding, write }}>{children}</WritesContext>;
}

/** The cell of a permission for a role: a checkbox that writes the role, named after both. */
export function PermissionCell({
  role,
  code,
  name,
}: {
  readonly role: string;
  readonly code: PermissionCode;
  readonly name: string;
}) {
  const writes = useContext(WritesContext);
  const holding = writes?.holding(role);
  if (holding === undefined) {
    return null;
  }
  return (
    <Checkbox
      checked={holding.codes.has(code)}
      aria-label={name}
      aria-busy={holding.writing}
      aria-disabled={holding.writing ? true : undefined}
      className="align-middle aria-disabled:opacity-50"
      onCheckedChange={(checked) => {
        writes?.write(holding, code, checked === true);
      }}
    />
  );
}
