// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pieces of the list of projects, the home (US-0090, US-0210): its filter on the projects
 * the user contributes to, visible and lifted by a link — never a restriction of reading
 * (WF-PRJ-0060) —; the projects themselves, in the order of the server, each a link to its page,
 * with its code and its state in words; and the way through its pages, when the server holds
 * more than one page of them.
 */
import { ChevronLeft, ChevronRight, Folder, ListFilter, X } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ALL_PROJECTS, CONTRIBUTOR_PARAMETER, HOME } from "@/navigation/home";

/** A project, as the list reads it. */
export type ListedProject = components["schemas"]["Project"];

/** Where the list stands in the projects the server holds for it. */
export type ListPage = components["schemas"]["PaginationMeta"];

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

/** The address of another page of the list, its filter kept. */
function pageHref(filtered: boolean, offset: number): string {
  const query = new URLSearchParams();
  if (!filtered) {
    query.set(CONTRIBUTOR_PARAMETER, "false");
  }
  if (offset > 0) {
    query.set("offset", String(offset));
  }
  const text = query.toString();
  return text === "" ? HOME : `${HOME}?${text}`;
}

/**
 * How many projects the list holds, and the links to the pages before and after this one, when
 * there are: the list never shows a page of it as if it were the whole.
 */
export function ListPages({
  page,
  shown,
  filtered,
}: {
  readonly page: ListPage;
  readonly shown: number;
  readonly filtered: boolean;
}) {
  const t = useTranslations("projectList");
  const before = page.offset > 0;
  const after = page.offset + shown < page.total;
  return (
    <div className="flex items-center gap-2 text-sm">
      <p className="text-muted-foreground">{t("count", { count: page.total })}</p>
      {before || after ? (
        <nav aria-label={t("pages.label")} className="flex items-center gap-2">
          {before ? (
            <Link href={pageHref(filtered, Math.max(0, page.offset - page.limit))} className={LINK}>
              <ChevronLeft aria-hidden="true" />
              {t("pages.previous")}
            </Link>
          ) : null}
          {after ? (
            <Link href={pageHref(filtered, page.offset + shown)} className={LINK}>
              {t("pages.next")}
              <ChevronRight aria-hidden="true" />
            </Link>
          ) : null}
        </nav>
      ) : null}
    </div>
  );
}
