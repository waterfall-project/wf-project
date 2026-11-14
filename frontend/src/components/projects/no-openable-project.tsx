// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The home of an account that cannot read any project (`project_settings.read`, WF-IHM-0120,
 * #2915): a page that says so, never a refusal. Decided on what the session carries, never on the
 * name of a role, in three cases: the account has no role yet; it holds functions outside any
 * project, to which the page leads, as the navigation offers them; it holds permissions but none
 * that the home reaches — functions that are exercised in a project, or commands that are not
 * functions —, and needs the reading of the projects. Above, as on the list, the prerequisites the
 * reference data lacks (WF-CYC-0120).
 */
import { FolderSearch } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { ReferenceIncomplete } from "@/components/system/empty-states";
import { type FunctionGroup, readableGroups } from "@/navigation/functions";

type PermissionCode = components["schemas"]["PermissionCode"];

const SAYING = "flex flex-col items-start gap-2 py-6 text-sm text-muted-foreground";
const LINK = "font-medium text-foreground underline";

/** What the home of an account without project knows of its session. */
export interface NoOpenableProjectProps {
  readonly permissions: readonly PermissionCode[];
  /** Whether the account carries at least one access role. */
  readonly hasRole: boolean;
  readonly readiness: components["schemas"]["ReferenceReadiness"];
}

/** The groups of functions outside any project that the permissions read, empty groups left out. */
export function reachableGroups(permissions: readonly PermissionCode[]): FunctionGroup[] {
  return readableGroups(permissions)
    .map((group) => ({
      ...group,
      functions: group.functions.filter((fn) => fn.scope === "platform"),
    }))
    .filter((group) => group.functions.length > 0);
}

/** Render the home of an account that opens no project. */
export function NoOpenableProject({ permissions, hasRole, readiness }: NoOpenableProjectProps) {
  const t = useTranslations();
  const groups = reachableGroups(permissions);
  const noRole = !hasRole || permissions.length === 0;
  return (
    <Screen density="airy">
      <PageHeader title={t("homeWithoutProject.title")} icon={FolderSearch} helped={false} />
      <ReferenceIncomplete readiness={readiness} permissions={permissions} />
      {noRole || groups.length === 0 ? (
        <div className={SAYING}>
          <p className="flex items-center gap-2">
            <FolderSearch aria-hidden="true" className="size-4 shrink-0" />
            {t(noRole ? "homeWithoutProject.withoutRole" : "homeWithoutProject.inProjectOnly")}
          </p>
        </div>
      ) : (
        <div className="space-y-4 py-2 text-sm">
          <p>{t("homeWithoutProject.withFunctions")}</p>
          <nav aria-label={t("homeWithoutProject.functions")} className="space-y-3">
            {groups.map((group) => (
              <section key={group.code} className="space-y-1">
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
