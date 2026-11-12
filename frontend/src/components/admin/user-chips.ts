// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the accounts on, told as chips under the bar of their table (WF-IHM-0020, #2916):
 * the origins, the node, the access roles, the state, and the periods and authors of the audit
 * columns, as the address of the screen says them (`user-address.ts`, `audit-address.ts`). A period
 * is told in the local days of the workstation, once in the browser (`PeriodFilter` does the same).
 */
"use client";

import { useTranslations } from "next-intl";

import { useAccountNaming } from "@/components/account/account-name";
import { useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";
import type { NodeChoice } from "@/components/reference/reference-filters";

import type { RoleChoice } from "./admin-grids";
import { AUTHORS, type AuditFilters, type AuthorChoice, PERIODS, WRITTEN } from "./audit-address";
import {
  ACCESS_ROLES,
  INCLUDE_INACTIVE,
  IS_ACTIVE,
  ORG_NODE,
  ORIGINS,
  type UserOrigin,
} from "./user-address";

/** What the address filters the accounts on, as the page read it. */
export interface UserFilters {
  readonly origins: readonly UserOrigin[];
  readonly orgNode: string | undefined;
  readonly accessRoles: readonly string[];
  readonly active: boolean | undefined;
  readonly audit: AuditFilters;
  /** The accounts offered as authors: those of the page shown. */
  readonly authors: readonly AuthorChoice[];
}

/** The chips of the filters of the accounts that are on, in the order of the panel. */
export function useUserChips(
  filters: UserFilters,
  nodes: readonly NodeChoice[],
  roles: readonly RoleChoice[],
): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  const add = kit.add;
  if (filters.origins.length > 0) {
    add(
      ORIGINS,
      t("grid.columns.origin"),
      filters.origins.map((origin) => t(`enums.UserOrigin.${origin}`)).join(", "),
      [ORIGINS],
    );
  }
  if (filters.orgNode !== undefined) {
    const node = nodes.find((each) => each.id === filters.orgNode);
    add(
      ORG_NODE,
      t("grid.columns.orgNode"),
      node === undefined
        ? filters.orgNode
        : t("reference.orgNodes.choice", { code: node.code, label: node.label }),
      [ORG_NODE],
    );
  }
  if (filters.accessRoles.length > 0) {
    add(
      ACCESS_ROLES,
      t("grid.columns.accessRoles"),
      filters.accessRoles.map((id) => roles.find((role) => role.id === id)?.label ?? id).join(", "),
      [ACCESS_ROLES],
    );
  }
  if (filters.active !== undefined) {
    add(
      IS_ACTIVE,
      t("admin.users.stateFilter"),
      filters.active ? t("admin.users.activeAccounts") : t("admin.users.inactiveAccounts"),
      [IS_ACTIVE, INCLUDE_INACTIVE],
    );
  }
  return [...kit.chips, ...useAccountAuditChips(filters.audit, filters.authors)];
}

/** The chips of the periods and the authors of the audit columns that are on. */
export function useAccountAuditChips(
  audit: AuditFilters,
  authors: readonly AuthorChoice[],
): FilterChip[] {
  const t = useTranslations();
  const naming = useAccountNaming();
  const kit = useChipKit();
  for (const column of WRITTEN) {
    kit.period(
      `${column}-period`,
      t(`grid.columns.${column}At`),
      "day",
      audit.periods[column],
      PERIODS[column],
    );
    const { user, kind } = audit.authors[column];
    if (user !== undefined || kind !== undefined) {
      const offered = authors.find((author) => author.id === user);
      const unoffered = audit.named?.find((account) => account.user_id === user);
      let who: string;
      if (user === undefined) {
        who =
          kind === "platform" ? t("enums.AuditActorKind.platform") : t("admin.audit.anyAccount");
      } else if (offered !== undefined) {
        who = naming.kept(offered.name);
      } else {
        who =
          unoffered === undefined ? t("grid.filtering.authorUnknown") : naming.person(unoffered);
      }
      kit.add(`${column}-author`, t(`grid.columns.${column}By`), who, [
        AUTHORS[column].user,
        AUTHORS[column].kind,
      ]);
    }
  }
  return kit.chips;
}
