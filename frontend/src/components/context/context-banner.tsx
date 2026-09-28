// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The banner of the reading context, on every screen of the data of a project (WF-IHM-0020):
 * the project, the revision read — its version name, its status, whether it is the reference
 * —, that it is read only when it is, and the active filters as chips, visible without
 * opening any panel, each with a link that lifts it.
 *
 * A server component: what it shows is the reading of the page, and a filter is lifted by
 * following a link, not by a state of the browser.
 */
import { X } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

import { formatPlanningDate } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";
import { UNASSIGNED, withoutFilter } from "@/navigation/context";

import type { Revision } from "./read-only";
import type { ContextFilter, ProjectReading, Subproject } from "./reading";

/** What the banner shows: the reading of the screen. */
export interface ContextBannerProps {
  readonly reading: ProjectReading;
}

const BADGE = "rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground";

/**
 * A date the address carries, shown as a date of the contract; as it is when it is none — the
 * address is the user's to write, and the API refuses it.
 */
function addressDate(value: string, locale: Locale): string {
  try {
    return formatPlanningDate(value, locale);
  } catch {
    return value;
  }
}

/** The text of a chip: what the filter restricts. */
function useFilterText(): (filter: ContextFilter) => string {
  const t = useTranslations();
  const locale = useLocale();
  // A sub-project the project does not have is named by the identifier the address gives.
  const subprojectName = (value: string, subproject: Subproject | undefined) => {
    if (subproject !== undefined) {
      return t("contextBanner.subprojectName", { code: subproject.code, label: subproject.label });
    }
    return value === UNASSIGNED ? t("enums.SubprojectFilter.unassigned") : value;
  };
  return (filter) =>
    filter.name === "as_of"
      ? t("contextBanner.asOf", { date: addressDate(filter.value, locale) })
      : t("contextBanner.subproject", {
          subproject: subprojectName(filter.value, filter.subproject),
        });
}

/** The revision read: its name, its status, whether it is the reference. */
function RevisionFacts({ revision }: { readonly revision: Revision }) {
  const t = useTranslations();
  return (
    <div className="flex flex-wrap items-center gap-2">
      <dt className="text-muted-foreground">{t("contextBanner.revision")}</dt>
      <dd className="font-medium">{revision.version_name ?? t("contextBanner.currentRevision")}</dd>
      <dd className={BADGE}>{t(`enums.RevisionStatus.${revision.status}`)}</dd>
      {revision.is_reference ? <dd className={BADGE}>{t("contextBanner.reference")}</dd> : null}
    </div>
  );
}

/** Render the reading context of a screen of a project. */
export function ContextBanner({ reading }: ContextBannerProps) {
  const t = useTranslations();
  const filterText = useFilterText();
  const { project, revision, readOnly, filters } = reading;
  return (
    <section
      aria-label={t("contextBanner.label")}
      className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b bg-card px-6 py-2 text-sm text-card-foreground"
    >
      <dl className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <div className="flex items-center gap-2">
          <dt className="text-muted-foreground">{t("contextBanner.project")}</dt>
          <dd className="font-medium">{project.label}</dd>
        </div>
        {revision === undefined ? null : <RevisionFacts revision={revision} />}
      </dl>
      {readOnly ? <p className="font-medium">{t("contextBanner.readOnly")}</p> : null}
      {filters.length === 0 ? null : (
        <ul aria-label={t("contextBanner.filters")} className="flex flex-wrap gap-2">
          {filters.map((filter) => {
            const text = filterText(filter);
            return (
              <li
                key={filter.name}
                className="flex items-center gap-1 rounded-md bg-accent py-0.5 pr-1 pl-2 text-accent-foreground"
              >
                {text}
                <Link
                  href={withoutFilter(reading.pathname, reading.context, filter.name)}
                  aria-label={t("contextBanner.removeFilter", { filter: text })}
                  className="rounded-md p-0.5 outline-none focus-visible:ring-[3px] focus-visible:ring-ring"
                >
                  <X aria-hidden="true" className="size-3.5" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
