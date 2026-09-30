// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The empty states of the shell: what a screen says when there is nothing to show, and where
 * it leads to fill it — no project, or none the user contributes to when the filter of the list
 * is what empties it, which the filter shown above the list lifts; a project without a
 * revision, which leads to its revisions when the session may read them; an installation whose
 * minimum reference data is
 * incomplete, which names each missing prerequisite (`getReferenceReadiness`, WF-CYC-0120)
 * and leads to the function of the reference that provides it, when the session may read it.
 *
 * Each is shown on an example of the contract named after it (`fixtures/api/`): `empty` for
 * the projects and the revisions, `incomplete` for the reference.
 */
import { FolderSearch, GitBranch, Inbox, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useId } from "react";

import type { components } from "@/api/generated/schema";
import { buttonVariants } from "@/components/ui/button";
import { functionOf, type PlatformFunction } from "@/navigation/functions";

const EMPTY = "flex flex-col items-start gap-2 py-6 text-sm text-muted-foreground";
const SENTENCE = "flex items-center gap-2";
const ICON = "size-4 shrink-0";
const ACTION = buttonVariants({ variant: "outline", size: "sm", className: "text-foreground" });
const LINK = "font-medium text-foreground underline";

/** Whether the empty list of projects was filtered on those the user contributes to. */
export interface NoProjectsProps {
  readonly filtered: boolean;
}

/**
 * Say there is no project — none the user contributes to, when the filter is what empties the
 * list: the filter shown above the list lifts it, with its own link.
 */
export function NoProjects({ filtered }: NoProjectsProps) {
  const t = useTranslations("emptyStates");
  return (
    <div className={EMPTY}>
      <p className={SENTENCE}>
        <FolderSearch aria-hidden="true" className={ICON} />
        {t(filtered ? "noContributedProjects" : "noProjects")}
      </p>
    </div>
  );
}

/** Where a project without a revision leads: the function of its revisions. */
export interface NoRevisionsProps {
  /**
   * The address of the function of the revisions of the project; none when the session may
   * not read them.
   */
  readonly revisions: string | undefined;
}

/** Say a project has no revision yet, and lead to its revisions. */
export function NoRevisions({ revisions }: NoRevisionsProps) {
  const t = useTranslations("emptyStates");
  return (
    <div className={EMPTY}>
      <p className={SENTENCE}>
        <Inbox aria-hidden="true" className={ICON} />
        {t("noRevisions")}
      </p>
      {revisions === undefined ? null : (
        <Link href={revisions} className={ACTION}>
          <GitBranch aria-hidden="true" />
          {t("revisions")}
        </Link>
      )}
    </div>
  );
}

/** A prerequisite of the minimum reference data. */
type Prerequisite = components["schemas"]["ReferenceReadiness"]["missing"][number];

/** The function of the reference where each prerequisite is provided (FBS-3). */
const PROVIDED_BY: Readonly<Record<Prerequisite, PlatformFunction>> = {
  default_calendar_with_hours: "resource_settings",
  active_cost_category: "cost_settings",
  active_resource_role: "resource_settings",
};

/** The state of the reference data, and the permissions of the session that reads it. */
export interface ReferenceIncompleteProps {
  readonly readiness: components["schemas"]["ReferenceReadiness"];
  readonly permissions: readonly components["schemas"]["PermissionCode"][];
}

/**
 * Name each prerequisite the reference data lacks, each a link to the function that provides
 * it when the session may read it; nothing when the reference data is complete.
 */
export function ReferenceIncomplete({ readiness, permissions }: ReferenceIncompleteProps) {
  const t = useTranslations();
  const title = useId();
  if (readiness.is_complete) {
    return null;
  }
  return (
    <section aria-labelledby={title} className="space-y-2 border-b pb-4 text-sm">
      <h2 id={title} className="flex items-center gap-2 text-base font-semibold">
        <TriangleAlert aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
        {t("referenceReadiness.title")}
      </h2>
      <p>{t("referenceReadiness.explanation")}</p>
      <ul className="list-disc space-y-1 pl-6">
        {readiness.missing.map((prerequisite) => {
          const fn = functionOf(PROVIDED_BY[prerequisite]);
          const label = t(`enums.ReferenceReadiness.missing.${prerequisite}`);
          return (
            <li key={prerequisite}>
              {permissions.includes(`${fn.permission}.read`) ? (
                <Link href={fn.route} className={LINK}>
                  {label}
                </Link>
              ) : (
                label
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
