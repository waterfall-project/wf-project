// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the access roles on, told as chips under the bar of their table (WF-IHM-0130,
 * #2916): their kind, the bounds of their holders, and the periods and the authors of the audit
 * columns, as the address of the screen says them (`role-address.ts`, `audit-address.ts`).
 */
"use client";

import { useTranslations } from "next-intl";

import { useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";

import type { RoleFilters } from "./account-lists";
import { HOLDER_COUNT, PREDEFINED } from "./role-address";
import { useAuditChips } from "./user-chips";

/** The chips of the filters of the access roles that are on, in the order of the panel. */
export function useRoleChips(filters: RoleFilters): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  if (filters.predefined !== undefined) {
    kit.add(
      PREDEFINED,
      t("grid.columns.roleKind"),
      filters.predefined
        ? t("admin.accessRoles.predefinedRoles")
        : t("admin.accessRoles.composedRoles"),
      [PREDEFINED],
    );
  }
  kit.bounds(HOLDER_COUNT, t("grid.columns.holders"), "count", filters.holders);
  return [...kit.chips, ...useAuditChips(filters.audit, filters.authors)];
}
