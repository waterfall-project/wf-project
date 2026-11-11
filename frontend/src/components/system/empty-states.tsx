// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The empty states of the shell: what a screen says when there is nothing to show, and where
 * it leads to fill it — no project, or none the user contributes to when the filter of the list
 * is what empties it, which the filter shown above the list lifts; an installation whose
 * minimum reference data is incomplete, which names each missing prerequisite
 * (`getReferenceReadiness`, WF-CYC-0120) and leads to the function of the reference that provides
 * it, when the session may read it.
 *
 * The home of an account that cannot read any project (`project_settings.read`, WF-IHM-0120,
 * #2915) is a page that says so, never a refusal: it leads to the functions the account holds
 * outside any project, or, holding none, says it has no role yet.
 *
 * Each is shown on an example of the contract named after it (`fixtures/api/`): `empty` for
 * the projects, `incomplete` for the reference.
 */
import { FolderSearch, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { functionOf, type PlatformFunction, readableGroups } from "@/navigation/functions";

const EMPTY = "flex flex-col items-start gap-2 py-6 text-sm text-muted-foreground";
const SENTENCE = "flex items-center gap-2";
const ICON = "size-4 shrink-0";
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

/** A prerequisite of the minimum reference data. */
type Prerequisite = components["schemas"]["ReferenceReadiness"]["missing"][number];

/** The function of the reference where each prerequisite is provided (FBS-3). */
const PROVIDED_BY: Readonly<Record<Prerequisite, PlatformFunction>> = {
  default_calendar_with_hours: "resource_settings",
  active_cost_category: "cost_settings",
  active_provision_category: "cost_settings",
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
  if (readiness.is_complete) {
    return null;
  }
  return (
    <section aria-label={t("referenceReadiness.title")} className="space-y-2 border-b pb-4 text-sm">
      <h2 className="flex items-center gap-2 text-base font-semibold">
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

/** The permissions of the session, which decide what the home of an account without project says. */
export interface NoOpenableProjectProps {
  readonly permissions: readonly components["schemas"]["PermissionCode"][];
}

/**
 * Say that the account opens no project, and lead to the functions it holds outside any project,
 * as the navigation offers them; with none, that it has no role yet and that an administrator
 * must give it one. Decided on the permissions, never on the name of a role (WF-IHM-0120, #2915).
 */
export function NoOpenableProject({ permissions }: NoOpenableProjectProps) {
  const t = useTranslations();
  const groups = readableGroups(permissions)
    .map((group) => ({
      ...group,
      functions: group.functions.filter((fn) => fn.scope === "platform"),
    }))
    .filter((group) => group.functions.length > 0);
  return (
    <Screen density="airy">
      <PageHeader title={t("homeWithoutProject.title")} icon={FolderSearch} helped={false} />
      {groups.length === 0 ? (
        <div className={EMPTY}>
          <p className={SENTENCE}>
            <FolderSearch aria-hidden="true" className={ICON} />
            {t("homeWithoutProject.withoutRole")}
          </p>
        </div>
      ) : (
        <div className="space-y-4 py-2 text-sm">
          <p>{t("homeWithoutProject.withFunctions")}</p>
          <nav aria-label={t("homeWithoutProject.functions")} className="space-y-3">
            {groups.map((group) => (
              <section key={group.code} aria-label={t(group.label)} className="space-y-1">
                <h2 className="text-base font-semibold">{t(group.label)}</h2>
                <ul className="list-disc space-y-1 pl-6">
                  {group.functions.map((fn) => (
                    <li key={fn.code}>
                      <Link href={fn.route} className={LINK}>
                        {t(fn.label)}
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </nav>
        </div>
      )}
    </Screen>
  );
}
