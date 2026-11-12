// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dense grid of the journal of audit in its page (FBS-1.5): given its configuration here, on
 * the side of the browser — a configuration reads the rows by functions, which never cross from a
 * server component to a client one. The page hands it data only: the inscriptions of the page,
 * where the page stands, what the address asked, the settings the session read, and what the
 * session may consult — the projects it may open, the functions it may read —, which its links lead
 * to. Read only: no cell is entered.
 *
 * The totals row says how many inscriptions the server retained (`meta.total`), never a count of
 * the page.
 */
"use client";

import { useTranslations } from "next-intl";
import { type ReactNode, useMemo } from "react";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import type { AuditFilters } from "./audit-address";
import { type AuditNames, useAuditChips } from "./audit-chips";
import {
  type AuditEvent,
  type AuditPage,
  type AuditReach,
  type AuditSort,
  auditGrid,
} from "./audit-columns";

/** Render the grid of a page of the journal, its totals row the number the server retained. */
export function AuditGrid({
  events,
  page,
  query,
  preferences,
  reach,
  filters,
  names,
  panel,
}: {
  readonly events: readonly AuditEvent[];
  readonly page: AuditPage;
  readonly query: GridQuery<AuditSort>;
  readonly preferences: GridPreferences | undefined;
  /** What the session may consult: where its links lead. */
  readonly reach: AuditReach;
  /** What the address filters the journal on, and the names found for it: told as chips under the bar. */
  readonly filters?: AuditFilters | undefined;
  readonly names?: AuditNames | undefined;
  /** The filters of the screen, which the bar folds into its panel (#2916); none, no panel. */
  readonly panel?: ReactNode;
}) {
  const t = useTranslations("admin.auditLog");
  const chips = useAuditChips(filters, names);
  // What the session may consult written out: a key that changes only when it does, whatever the
  // object.
  const key = JSON.stringify(reach);
  const config = useMemo(() => auditGrid(JSON.parse(key) as AuditReach), [key]);
  return (
    <DenseGrid
      config={config}
      rows={events}
      totals={page}
      totalsCaption={(retained) => t("count", { count: retained.total })}
      query={query}
      preferences={preferences}
      filtering={panel === undefined ? undefined : { panel, chips }}
    />
  );
}
