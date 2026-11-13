// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the backups on, told as chips under the bar of their table (WF-IHM-0130, #2916):
 * the period they were taken in, their origins, their verifications, their marking and the bounds
 * of their size, as the address of the screen says them (`backup-address.ts`).
 */
"use client";

import { useTranslations } from "next-intl";

import { useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";

import {
  type BackupFilters,
  IS_RETAINED,
  ORIGINS,
  SIZE_BYTES,
  VERIFICATIONS,
} from "./backup-address";

/** The chips of the filters of the backups that are on, in the order of the panel. */
export function useBackupChips(filters: BackupFilters): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  kit.period("period", t("grid.columns.takenAt"), "day", filters.period);
  kit.values(
    ORIGINS,
    t("grid.columns.backupOrigin"),
    filters.origins.map((origin) => t(`enums.BackupOrigin.${origin}`)),
  );
  kit.values(
    VERIFICATIONS,
    t("grid.columns.verification"),
    filters.verifications.map((outcome) => t(`enums.BackupVerification.${outcome}`)),
  );
  if (filters.retained !== undefined) {
    kit.add(
      IS_RETAINED,
      t("grid.columns.retention"),
      filters.retained ? t("admin.backups.retainedOnes") : t("admin.backups.rotatingOnes"),
      [IS_RETAINED],
    );
  }
  kit.bounds(SIZE_BYTES, t("grid.columns.size"), "bytes", filters.size);
  return kit.chips;
}
