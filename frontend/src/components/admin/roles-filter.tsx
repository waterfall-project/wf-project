// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of the accounts on their access roles (WF-IHM-0130, WF-ADM-0180): a menu of boxes to
 * check, one for each role the session reads, and « Sans rôle » first, for the accounts that hold
 * none — those a first connection through an external provider creates. The roles go to
 * `access_role_ids`, « Sans rôle » to `without_access_role`, both under the names of the contract:
 * the server retains the accounts that hold one of the roles or none at all, a choice only changes
 * the address and the page reads anew (`filters.ts`). The choice goes on from the address last asked
 * (`usePendingAddress`) and shows until the server answers for it (défaut n° 21 de `typescript.md`).
 *
 * Every prop is data (défaut n° 12 de `typescript.md`).
 */
"use client";

import { usePathname } from "next/navigation";
import { useOptimistic, useTransition } from "react";

import { CheckMenu } from "@/components/grid/check-menu";
import { filterHref, readValues, valuesHref } from "@/components/grid/filters";
import { usePendingAddress } from "@/components/grid/pending-address";

import type { RoleChoice } from "./admin-grids";
import { ACCESS_ROLES, readWithoutRole, WITHOUT_ACCESS_ROLE } from "./user-address";

/** The value of the box « Sans rôle »: no identifier of a role is written so. */
const WITHOUT = "without";

/** The roles and the « Sans rôle » box an address names, as the menu shows them checked. */
function checked(query: URLSearchParams, ids: readonly string[]): readonly string[] {
  return [...(readWithoutRole(query) ? [WITHOUT] : []), ...readValues(query, ACCESS_ROLES, ids)];
}

/** Render the filter of the accounts on their roles, those the address names checked. */
export function RolesFilter({
  label,
  every,
  without,
  roles,
  chosen,
  withoutRole,
  page,
}: {
  /** The name of the menu: what the filter filters on. */
  readonly label: string;
  /** The text of the choice that lifts the filter. */
  readonly every: string;
  /** The text of the box that retains the accounts without a role. */
  readonly without: string;
  /** The roles the session reads, as the server gives them. */
  readonly roles: readonly RoleChoice[];
  /** The roles the address filters on. */
  readonly chosen: readonly string[];
  /** Whether the address retains the accounts without a role. */
  readonly withoutRole: boolean;
  /** The parameter of the page of the list, which a filter takes back to its first. */
  readonly page?: string | undefined;
}) {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const ids = roles.map((role) => role.id);
  const filter = { name: ACCESS_ROLES, values: ids, page, exhaustive: false };
  const [shown, show] = useOptimistic(withoutRole ? [WITHOUT, ...chosen] : chosen);
  const [, startTransition] = useTransition();
  /** Filter on what a change makes of the roles and of « Sans rôle » last asked. */
  const change = (toggled: { readonly value: string; readonly checked: boolean } | undefined) => {
    startTransition(() => {
      request((query) => {
        const asked = readValues(query, ACCESS_ROLES, ids);
        const was = readWithoutRole(query);
        let roled: readonly string[] = asked;
        let nowWithout = was;
        if (toggled === undefined) {
          roled = [];
          nowWithout = false;
        } else if (toggled.value === WITHOUT) {
          nowWithout = toggled.checked;
        } else {
          roled = toggled.checked
            ? [...asked.filter((id) => id !== toggled.value), toggled.value]
            : asked.filter((id) => id !== toggled.value);
        }
        const withRoles = new URLSearchParams(
          valuesHref(pathname, query, filter, roled).split("?")[1] ?? "",
        );
        const href = filterHref(
          pathname,
          withRoles,
          WITHOUT_ACCESS_ROLE,
          nowWithout ? "true" : undefined,
          page ?? [],
        );
        show(checked(new URLSearchParams(href.split("?")[1] ?? ""), ids));
        return href;
      });
    });
  };
  return (
    <CheckMenu
      label={label}
      every={every}
      multiple
      options={[
        { value: WITHOUT, text: without },
        ...roles.map((role) => ({ value: role.id, text: role.label })),
      ]}
      chosen={shown}
      onChange={(_values, toggled) => {
        change(toggled);
      }}
    />
  );
}
