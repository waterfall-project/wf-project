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
 * never put in their place. Nothing is written until the button of a choice is pressed, and every
 * account selected is written, the server deciding what the screen may hold stale.
 * Every prop is data, never a function (défaut n° 12 de `typescript.md`).
 */
"use client";

import { useTranslations } from "next-intl";
import { type ReactNode, useState } from "react";

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
  return (
    <>
      {roles.length === 0 ? null : (
        <BulkChoice
          label={t("bulk.addRole")}
          apply={t("bulk.apply", { command: t("bulk.addRole") })}
          waiting={waiting}
          onApply={(role, back) => {
            return writes.bulk(rows, { kind: "add_role", role }, back);
          }}
        >
          {roles.map((role) => (
            <option key={role.id} value={role.id}>
              {role.label}
            </option>
          ))}
        </BulkChoice>
      )}
      <BulkChoice
        label={t("bulk.attach")}
        apply={t("bulk.apply", { command: t("bulk.attach") })}
        waiting={waiting}
        onApply={(node, back) => {
          return writes.bulk(rows, { kind: "attach", node: node === NO_NODE ? null : node }, back);
        }}
      >
        <option value={NO_NODE}>{t("noOrgNode")}</option>
        {nodes.map((node) => (
          <option key={node.id} value={node.id}>
            {treeLabel(node.level, named("choice", { code: node.code, label: node.label }))}
          </option>
        ))}
      </BulkChoice>
      {[true, false].map((active) => (
        <Button
          key={String(active)}
          type="button"
          variant="ghost"
          size="sm"
          aria-busy={waiting}
          {...(waiting ? { "aria-disabled": true } : {})}
          className={`${BAR_BUTTON} ${UNAVAILABLE}`}
          onClick={(event) => {
            if (!waiting) {
              void writes.bulk(rows, { kind: "activation", active }, event.currentTarget);
            }
          }}
        >
          {t(active ? "bulk.activate" : "bulk.deactivate")}
        </Button>
      ))}
    </>
  );
}

/** The look of a button of the bar. */
const BAR_BUTTON = "h-6 text-xs text-background hover:bg-background/15 hover:text-background";

/** A button that cannot be pressed now, as `aria-disabled` says (the same as the exit command). */
const UNAVAILABLE = "aria-disabled:cursor-not-allowed aria-disabled:opacity-50";

/** The value of the choice « Aucun » of the attachment: no identifier of a node is written so. */
const NO_NODE = "none";

/**
 * A choice of the bar and its button: the choice is only made in the list, and nothing is written
 * until the button is pressed — a native list fires `change` at each arrow key, so that walking it
 * with the keyboard would write the first value to every account selected.
 */
function BulkChoice({
  label,
  apply,
  waiting,
  onApply,
  children,
}: {
  readonly label: string;
  readonly apply: string;
  readonly waiting: boolean;
  readonly onApply: (value: string, back: HTMLElement) => Promise<boolean>;
  readonly children: ReactNode;
}) {
  const t = useTranslations("admin.users");
  const [value, setValue] = useState("");
  return (
    <div className="flex shrink-0 items-center gap-1">
      <div className="w-40 shrink-0">
        <NativeSelect
          aria-label={label}
          aria-busy={waiting}
          className="h-6 rounded-sm border-background/40 bg-transparent text-xs text-background"
          value={value}
          onChange={(event) => {
            setValue(event.currentTarget.value);
          }}
        >
          <option value="">{label}</option>
          {children}
        </NativeSelect>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label={apply}
        aria-busy={waiting}
        {...(waiting || value === "" ? { "aria-disabled": true } : {})}
        className={`${BAR_BUTTON} ${UNAVAILABLE}`}
        onClick={(event) => {
          if (value !== "" && !waiting) {
            // The choice stays shown while its group is under way, and is cleared when it ends;
            // a group that does not start (nothing selected) leaves it as it is.
            void onApply(value, event.currentTarget).then((ended) => {
              if (ended) {
                setValue("");
              }
            });
          }
        }}
      >
        {t("bulk.applyShort")}
      </Button>
    </div>
  );
}
