// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pieces of the list of projects, the home (US-0090, US-0210, #522), on the side of the
 * server: its filter on the projects the user contributes to, always shown while it applies —
 * never a restriction of reading (WF-PRJ-0060) —, lifted by a link offered only to a session that
 * may read every project (`all_projects_read`, WF-ADM-0110): lifted for anyone else, the list
 * would show the same projects, and the link would promise what it does not do (WF-IHM-0090);
 * and the projects themselves, in the dense grid, or, when the server holds none, that it holds
 * none. A link of the filter keeps the rest of the address — the states, the sort, the search —,
 * back to the first page.
 */
import { ListFilter, X } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { parametersHref } from "@/components/portfolio/address";
import { NoProjects } from "@/components/system/empty-states";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { CONTRIBUTOR_PARAMETER, HOME } from "@/navigation/home";

import type { ListedProjectPage, ListedProjectRow, ListedProjectSort } from "./project-list-grid";
import { ProjectListGrid } from "./project-list-view";

const LINK = buttonVariants({ variant: "outline", size: "sm" });

/** What the filter of the list shows. */
export interface ContributorFilterProps {
  /** Whether the list is filtered on the projects the user contributes to. */
  readonly filtered: boolean;
  /** Whether the session may read the projects it does not contribute to. */
  readonly mayLift: boolean;
  /** The query of the address, which a link of the filter keeps. */
  readonly query: URLSearchParams;
}

/**
 * The filter of the list: shown while it applies, with the link that lifts it to a session that
 * may read every project; once lifted, the link that applies it again. A session that may not read
 * every project is always filtered (`mayLiftContributorFilter`): the badge alone, no link.
 */
export function ContributorFilter({ filtered, mayLift, query }: ContributorFilterProps) {
  const t = useTranslations("projectList.filter");
  return (
    <section aria-label={t("label")} className="flex flex-wrap items-center gap-2 text-sm">
      {filtered ? (
        <>
          <Badge variant="outline">
            <ListFilter aria-hidden="true" />
            {t("mine")}
          </Badge>
          {mayLift ? (
            <Link
              href={parametersHref(HOME, query, { [CONTRIBUTOR_PARAMETER]: "false" })}
              className={LINK}
            >
              <X aria-hidden="true" />
              {t("lift")}
            </Link>
          ) : null}
        </>
      ) : (
        <Link
          href={parametersHref(HOME, query, { [CONTRIBUTOR_PARAMETER]: undefined })}
          className={LINK}
        >
          <ListFilter aria-hidden="true" />
          {t("apply")}
        </Link>
      )}
    </section>
  );
}

/** What the list of projects shows: a page of the projects the server retained. */
export interface ProjectListProps {
  readonly projects: readonly ListedProjectRow[];
  readonly page: ListedProjectPage;
  readonly filtered: boolean;
  /** Whether the address narrows the list besides its filter: by states, or by a search. */
  readonly narrowed: boolean;
  readonly query: GridQuery<ListedProjectSort>;
  readonly preferences: GridPreferences | undefined;
}

/**
 * The projects of a page of the list, or that there is none: only when the list holds none at
 * all, and the address narrows it by nothing but its filter — a page asked beyond its end is no
 * empty list, and leads back into it; a list emptied by states or a search keeps its grid, whose
 * bar and filter change them. The filter that would empty it is lifted by the link the header
 * shows.
 */
export function ProjectList({
  projects,
  page,
  filtered,
  narrowed,
  query,
  preferences,
}: ProjectListProps) {
  if (page.total === 0 && !narrowed) {
    return <NoProjects filtered={filtered} />;
  }
  return (
    <ProjectListGrid projects={projects} page={page} query={query} preferences={preferences} />
  );
}
