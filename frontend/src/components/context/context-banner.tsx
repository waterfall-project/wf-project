// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The banner of the reading context, on every screen of the data of a project (WF-IHM-0020):
 * the project, the revision read — its version name, its status, whether it is the reference
 * —, that it is read only when it is, and the active filters as chips, visible without
 * opening any panel, each with a link that lifts it. An icon before each fact, whose name the
 * list of definitions gives to a screen reader; the states in badges, in words.
 *
 * A server component: what it shows is the reading of the page, and a filter is lifted by
 * following a link, not by a state of the browser. It hands the project on to the shell, which
 * names it in its side bar and its breadcrumb (`ShowProject`).
 */
import { Filter, Folder, GitBranch, Lock, X } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

import { ShowProject } from "@/components/shell/shown-project";
import { Badge } from "@/components/ui/badge";
import { formatPlanningDate } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";
import { UNASSIGNED, withoutFilter } from "@/navigation/context";

import type { Revision } from "./read-only";
import type { ContextFilter, ProjectReading, Subproject } from "./reading";

/** What the banner shows: the reading of the screen. */
export interface ContextBannerProps {
  readonly reading: ProjectReading;
}

const FACT = "flex items-center gap-1.5";
const ICON = "size-3.5 shrink-0 text-muted-foreground";

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
    <div className={FACT}>
      <dt>
        <GitBranch aria-hidden="true" className={ICON} />
        <span className="sr-only">{t("contextBanner.revision")}</span>
      </dt>
      <dd>{revision.version_name ?? t("contextBanner.currentRevision")}</dd>
      <dd>
        <Badge>{t(`enums.RevisionStatus.${revision.status}`)}</Badge>
      </dd>
      {revision.is_reference ? (
        <dd>
          <Badge variant="outline">{t("contextBanner.reference")}</Badge>
        </dd>
      ) : null}
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
      className="flex min-h-10 flex-wrap items-center gap-x-4 gap-y-1 border-b bg-muted px-5 py-1.5 text-xs text-foreground"
    >
      <ShowProject
        project={{
          project_id: project.project_id,
          label: project.label,
          code: project.code ?? null,
          state: project.state,
        }}
      />
      <dl className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <div className={FACT}>
          <dt>
            <Folder aria-hidden="true" className={ICON} />
            <span className="sr-only">{t("contextBanner.project")}</span>
          </dt>
          <dd className="font-medium">{project.label}</dd>
        </div>
        {revision === undefined ? null : <RevisionFacts revision={revision} />}
      </dl>
      {readOnly ? (
        <p className={`${FACT} font-medium`}>
          <Lock aria-hidden="true" className={ICON} />
          {t("contextBanner.readOnly")}
        </p>
      ) : null}
      {filters.length === 0 ? null : (
        <ul aria-label={t("contextBanner.filters")} className="ml-auto flex flex-wrap gap-1.5">
          {filters.map((filter) => {
            const text = filterText(filter);
            return (
              <li
                key={filter.name}
                className="flex h-6 items-center gap-1.5 rounded-full border bg-background pr-1 pl-2"
              >
                <Filter aria-hidden="true" className={ICON} />
                {text}
                <Link
                  href={withoutFilter(reading.pathname, reading.context, filter.name)}
                  aria-label={t("contextBanner.removeFilter", { filter: text })}
                  className="rounded-full p-0.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring"
                >
                  <X aria-hidden="true" className="size-3" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
