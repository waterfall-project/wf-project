// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the journal of audit on, told as chips under the bar of its table (WF-IHM-0130,
 * #2916): the period, the nature of the author and the author, the actions, the project, the nature
 * of the object and the one object whose history is asked, and the correlation of a request, as
 * the address of the screen says them (`audit-address.ts`). An author, a project or an object the
 * journal does not name is told as it is chosen: by its names when the screen read them, never by
 * its identifier.
 */
"use client";

import { useTranslations } from "next-intl";

import { useAccountNaming } from "@/components/account/account-name";
import type { NamedAccount } from "@/components/account/initials";
import { useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";

import {
  ACTIONS,
  ACTOR_KIND,
  type AuditFilters,
  CORRELATION,
  FROM,
  OBJECT,
  OBJECT_KIND,
  type OBJECT_KINDS,
  PROJECT,
  TO,
  USER,
} from "./audit-address";
import { useObjectName } from "./audit-cells";

/** An account author of an inscription, by its identifier and the name it shows today. */
export interface AuthorChoice {
  readonly id: string;
  readonly name: string | null;
}

/** A project of the journal, by its identifier, its code and its label. */
export interface ProjectChoice {
  readonly id: string;
  readonly code: string | null;
  readonly label: string;
}

/** What the screen read of the filters the address asks, and the names it found for them. */
export interface AuditNames {
  /** The accounts authors of an inscription of the journal, by their names. */
  readonly users: readonly AuthorChoice[];
  /** The projects of the journal, by their codes and labels. */
  readonly projects: readonly ProjectChoice[];
  /**
   * The names the inscriptions shown give what the address names and no choice offers: the author
   * — null for an anonymised account —, the project, the object whose history is asked.
   */
  readonly named: {
    readonly user: string | null | undefined;
    /** The author chosen that no choice offers and no inscription names, read by its names. */
    readonly account?: NamedAccount | undefined;
    readonly project: Omit<ProjectChoice, "id"> | undefined;
    /** The object, by its label — none for a backup and for an anonymised account. */
    readonly object:
      { readonly label: string | null; readonly kind: (typeof OBJECT_KINDS)[number] } | undefined;
  };
}

/** How an author and a project are told: as the journal names them, else as the screen read them. */
function useTold(names: AuditNames | undefined) {
  const t = useTranslations();
  const naming = useAccountNaming();
  return {
    author: (id: string): string => {
      const found = names?.users.find((user) => user.id === id);
      if (found !== undefined) {
        return naming.kept(found.name);
      }
      if (names?.named.account !== undefined) {
        return naming.person(names.named.account);
      }
      return names?.named.user === undefined
        ? t("grid.filtering.authorUnknown")
        : naming.kept(names.named.user);
    },
    project: (id: string): string => {
      const project = names?.projects.find((each) => each.id === id) ?? names?.named.project;
      if (project === undefined) {
        // Never an identifier: a project the journal does not name is told by its kind.
        return t("grid.filtering.projectUnknown");
      }
      return project.code === null
        ? project.label
        : t("admin.auditLog.project", { code: project.code, label: project.label });
    },
  };
}

/** The chips of the filters of the journal that are on, in the order of the panel. */
export function useAuditChips(
  filters: AuditFilters | undefined,
  names: AuditNames | undefined,
): FilterChip[] {
  const t = useTranslations();
  const objectName = useObjectName();
  const told = useTold(names);
  const kit = useChipKit();
  if (filters === undefined || names === undefined) {
    return kit.chips;
  }
  kit.period("period", t("grid.columns.occurredAt"), "instant", filters, { from: FROM, to: TO });
  kit.values(
    ACTOR_KIND,
    t("admin.auditLog.filters.actorChip"),
    filters.actorKinds.map((kind) => t(`enums.AuditActorKind.${kind}`)),
  );
  if (filters.user !== undefined) {
    kit.add(USER, t("grid.columns.author"), told.author(filters.user), [USER]);
  }
  kit.values(
    ACTIONS,
    t("grid.columns.auditAction"),
    filters.actions.map((action) => t(`enums.AuditAction.${action}`)),
  );
  if (filters.project !== undefined) {
    kit.add(PROJECT, t("grid.columns.project"), told.project(filters.project), [PROJECT]);
  }
  if (filters.objectKind !== undefined) {
    kit.add(
      OBJECT_KIND,
      t("grid.columns.objectKind"),
      t(`enums.AuditObjectKind.${filters.objectKind}`),
      [OBJECT_KIND],
    );
  }
  if (filters.object !== undefined) {
    const { object } = names.named;
    kit.add(
      OBJECT,
      t("grid.columns.auditObject"),
      object === undefined ? t("grid.filtering.objectUnknown") : objectName(object),
      [OBJECT],
    );
  }
  if (filters.correlation !== undefined) {
    kit.add(CORRELATION, t("grid.columns.correlation"), filters.correlation, [CORRELATION]);
  }
  return kit.chips;
}
