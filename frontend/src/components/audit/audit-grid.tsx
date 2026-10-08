// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dense grid of the journal of audit in its page (FBS-1.5): given its configuration here, on
 * the side of the browser — a configuration reads the rows by functions, which never cross from a
 * server component to a client one. The page hands it data only: the inscriptions of the page,
 * where the page stands, what the address asked, the settings the session read, and the projects
 * the session may open, which its links lead to. Read only: no cell is entered.
 *
 * The totals row says how many inscriptions the server retained (`meta.total`), never a count of
 * the page.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import { type AuditEvent, type AuditPage, type AuditSort, auditGrid } from "./audit-columns";

/** Render the grid of a page of the journal, its totals row the number the server retained. */
export function AuditGrid({
  events,
  page,
  query,
  preferences,
  openable,
}: {
  readonly events: readonly AuditEvent[];
  readonly page: AuditPage;
  readonly query: GridQuery<AuditSort>;
  readonly preferences: GridPreferences | undefined;
  /** The projects the session may open, by their identifiers: those its links lead to. */
  readonly openable: readonly string[];
}) {
  const t = useTranslations("admin.auditLog");
  // The identifiers joined: a key that changes only when the projects do, whatever the array.
  const projects = openable.join(",");
  const config = useMemo(
    () => auditGrid(new Set(projects === "" ? [] : projects.split(","))),
    [projects],
  );
  return (
    <DenseGrid
      config={config}
      rows={events}
      totals={page}
      totalsCaption={(retained) => t("count", { count: retained.total })}
      query={query}
      preferences={preferences}
    />
  );
}
