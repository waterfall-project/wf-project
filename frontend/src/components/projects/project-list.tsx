// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pieces of the list of projects, the home (US-0090, US-0210): its filter on the projects
 * the user contributes to, visible and lifted by a link — never a restriction of reading
 * (WF-PRJ-0060) —; the projects themselves, in the order of the server, each a link to its page,
 * with its code and its state in words; the way through its pages, when the server holds more
 * than one page of them; and, when it holds none, that it is empty.
 */
import { Folder, ListFilter, X } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { NoProjects } from "@/components/system/empty-states";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ALL_PROJECTS, CONTRIBUTOR_PARAMETER, HOME } from "@/navigation/home";
import { type ListPage, pageHref, pageOffsets } from "@/navigation/pages";

/** A project, as the list reads it. */
export type ListedProject = components["schemas"]["Project"];

const LINK = buttonVariants({ variant: "outline", size: "sm" });
const CELL = "py-1.5";

/** The filter of the list: shown while it applies, with the link that lifts it; else offered. */
export function ContributorFilter({ filtered }: { readonly filtered: boolean }) {
  const t = useTranslations("projectList.filter");
  return (
    <section aria-label={t("label")} className="flex flex-wrap items-center gap-2 text-sm">
      {filtered ? (
        <>
          <Badge variant="outline">
            <ListFilter aria-hidden="true" />
            {t("mine")}
          </Badge>
          <Link href={ALL_PROJECTS} className={LINK}>
            <X aria-hidden="true" />
            {t("lift")}
          </Link>
        </>
      ) : (
        <Link href={HOME} className={LINK}>
          <ListFilter aria-hidden="true" />
          {t("apply")}
        </Link>
      )}
    </section>
  );
}

/** The projects of a page of the list, in the order the server gave them. */
export function ProjectTable({ projects }: { readonly projects: readonly ListedProject[] }) {
  const t = useTranslations();
  return (
    <Table aria-label={t("projectList.label")} className="w-full">
      <TableHeader>
        <TableRow>
          <TableHead className={CELL}>{t("projectList.columns.label")}</TableHead>
          <TableHead className={CELL}>{t("projectList.columns.code")}</TableHead>
          <TableHead className={CELL}>{t("projectList.columns.state")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {projects.map((project) => (
          <TableRow key={project.project_id}>
            <TableCell className={CELL}>
              <Link
                href={`/projects/${project.project_id}`}
                className="inline-flex items-center gap-1.5 font-medium underline-offset-4 hover:underline"
              >
                <Folder aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
                {project.label}
              </Link>
            </TableCell>
            <TableCell className={CELL}>{project.code}</TableCell>
            <TableCell className={CELL}>
              <Badge>{t(`enums.ProjectState.${project.state}`)}</Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/** The parameters a link to another page of the list keeps: its filter, when lifted. */
function keptQuery(filtered: boolean): URLSearchParams {
  return new URLSearchParams(filtered ? {} : { [CONTRIBUTOR_PARAMETER]: "false" });
}

/**
 * How many projects the list holds, and the links to the pages before and after this one, when
 * there are: the list never shows a page of it as if it were the whole. A page asked beyond the
 * end of the list says so, and leads back to its last page (`pageOffsets`).
 */
export function ProjectListPages({
  page,
  shown,
  filtered,
}: {
  readonly page: ListPage;
  readonly shown: number;
  readonly filtered: boolean;
}) {
  const t = useTranslations("projectList");
  const { beyond, previous, next } = pageOffsets(page, shown);
  const kept = keptQuery(filtered);
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <p className="text-muted-foreground">{t("count", { count: page.total })}</p>
      {beyond ? <p>{t("pages.beyond")}</p> : null}
      {previous !== undefined || next !== undefined ? (
        <Pagination aria-label={t("pages.label")}>
          <PaginationContent>
            {previous === undefined ? null : (
              <PaginationItem>
                <PaginationPrevious href={pageHref(HOME, kept, previous)}>
                  {t("pages.previous")}
                </PaginationPrevious>
              </PaginationItem>
            )}
            {next === undefined ? null : (
              <PaginationItem>
                <PaginationNext href={pageHref(HOME, kept, next)}>{t("pages.next")}</PaginationNext>
              </PaginationItem>
            )}
          </PaginationContent>
        </Pagination>
      ) : null}
    </div>
  );
}

/**
 * The projects of a page of the list, or that there is none: only when the list holds none at
 * all — a page asked beyond its end is no empty list, and leads back into it. The filter that
 * would empty it is lifted by the link the header already shows.
 */
export function ProjectList({
  projects,
  page,
  filtered,
}: {
  readonly projects: readonly ListedProject[];
  readonly page: ListPage;
  readonly filtered: boolean;
}) {
  if (page.total === 0) {
    return <NoProjects filtered={filtered} />;
  }
  return (
    <>
      {projects.length === 0 ? null : <ProjectTable projects={projects} />}
      <ProjectListPages page={page} shown={projects.length} filtered={filtered} />
    </>
  );
}
