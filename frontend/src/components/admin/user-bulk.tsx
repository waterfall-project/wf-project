// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the bar of the actions on the accounts selected (#2917, US-1860/L3), for a session
 * that may modify them: « Ajouter un rôle », « Rattacher à », « Activer » and « Désactiver ». The
 * contract has no group operation: each account selected is written by its own call
 * (`setUserAccessRoles`, `updateUser`, `setUserActivation`), one after the other and with no
 * atomicity, from the version the screen holds; those answered stay written, and each refused is told
 * with its reason — a 412 for an account modified meanwhile, the last administrator that cannot be
 * deactivated — above the table (`UserWrites.bulk`). A role is added to those the account holds,
 * never put in their place; an account that is already as asked is not written.
 * Every prop is data, never a function (défaut n° 12 de `typescript.md`).
 */
"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { treeLabel } from "@/components/reference/org-tree";
import type { NodeChoice } from "@/components/reference/reference-filters";

import type { RoleChoice, User } from "./admin-grids";
import { useUserWrites } from "./user-commands";

/** The commands of the bar on the accounts selected `rows`. */
export function UserBulkCommands({
  rows,
  roles,
  nodes,
}: {
  readonly rows: readonly User[];
  /** The roles of the installation an account may be given; none when the session reads none. */
  readonly roles: readonly RoleChoice[];
  /** The active nodes an account may be attached to, in the order of the tree. */
  readonly nodes: readonly NodeChoice[];
}) {
  const t = useTranslations("admin.users");
  const named = useTranslations("reference.orgNodes");
  const writes = useUserWrites();
  if (writes === undefined) {
    return null;
  }
  const waiting = writes.bulking;
  const select = "h-6 rounded-sm border-background/40 bg-transparent text-xs text-background";
  return (
    <>
      {roles.length === 0 ? null : (
        <div className="w-40 shrink-0">
          <NativeSelect
            aria-label={t("bulk.addRole")}
            aria-busy={waiting}
            className={select}
            value=""
            onChange={(event) => {
              const role = event.currentTarget.value;
              if (role !== "" && !waiting) {
                writes.bulk(rows, { kind: "add_role", role }, event.currentTarget);
              }
            }}
          >
            <option value="">{t("bulk.addRole")}</option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.label}
              </option>
            ))}
          </NativeSelect>
        </div>
      )}
      <div className="w-40 shrink-0">
        <NativeSelect
          aria-label={t("bulk.attach")}
          aria-busy={waiting}
          className={select}
          value=""
          onChange={(event) => {
            const node = event.currentTarget.value;
            if (node !== "" && !waiting) {
              writes.bulk(
                rows,
                { kind: "attach", node: node === NO_NODE ? null : node },
                event.currentTarget,
              );
            }
          }}
        >
          <option value="">{t("bulk.attach")}</option>
          <option value={NO_NODE}>{t("noOrgNode")}</option>
          {nodes.map((node) => (
            <option key={node.id} value={node.id}>
              {treeLabel(node.level, named("choice", { code: node.code, label: node.label }))}
            </option>
          ))}
        </NativeSelect>
      </div>
      {[true, false].map((active) => (
        <Button
          key={String(active)}
          type="button"
          variant="ghost"
          size="sm"
          aria-busy={waiting}
          {...(waiting ? { "aria-disabled": true } : {})}
          className="h-6 text-xs text-background hover:bg-background/15 hover:text-background"
          onClick={(event) => {
            if (!waiting) {
              writes.bulk(rows, { kind: "activation", active }, event.currentTarget);
            }
          }}
        >
          {t(active ? "bulk.activate" : "bulk.deactivate")}
        </Button>
      ))}
    </>
  );
}

/** The value of the choice « Aucun » of the attachment: no identifier of a node is written so. */
const NO_NODE = "none";
