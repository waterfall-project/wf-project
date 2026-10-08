// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way through the pages of a list of the reference data the server pages (#509, #510, #533) —
 * the hourly rates, the natures and the categories of cost, the roles, the calendars —, several on
 * one screen: the links to the page before and the page after the one shown, when there are, by the
 * pagination of shadcn/ui, each named after its list. A list never shows one of its pages as if it
 * were the whole — its totals row says how many it holds —; a page asked beyond its end says so, and
 * leads back to its last page (`pageOffsets`, the one rule of every list, #317).
 *
 * A page turned only changes the address, under the name of the page of its grid (`offset`, after
 * its prefix), from the address last asked (`usePendingLink`): when that address reads the list
 * otherwise than the one shown — a sort, a search or a filter of its own under way —, the link leads
 * to its first page, the place of a row in the list shown meaning nothing in the other; a sort or a
 * page of another list of the screen leaves it as it is.
 */
"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { filterHref } from "@/components/grid/filters";
import { usePendingLink } from "@/components/grid/pending-address";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { type ListPage, pageOffsets } from "@/navigation/pages";

import { readingOf } from "./address";

/** A list of the reference data the server pages: its page in the address, and what it reads. */
export interface PagedList {
  /** The parameter of the address that names its page. */
  readonly page: string;
  /** The parameters of the address the list reads (`listReads`), its page among them. */
  readonly reads: readonly string[];
}

/** A link to another page of a list, or to its first one when the address last asked reads it otherwise. */
function PageLink({
  list,
  offset,
  direction,
}: {
  readonly list: PagedList;
  readonly offset: number;
  readonly direction: "previous" | "next";
}) {
  const t = useTranslations("reference.pages");
  const pathname = usePathname();
  const shown = useSearchParams();
  const others = list.reads.filter((name) => name !== list.page);
  const { href, onClick } = usePendingLink((query) => {
    const same = readingOf(query, others) === readingOf(new URLSearchParams(shown), others);
    const at = same ? offset : 0;
    return filterHref(pathname, query, list.page, at > 0 ? String(at) : undefined);
  });
  const Link = direction === "previous" ? PaginationPrevious : PaginationNext;
  return (
    <PaginationItem>
      <Link href={href} onClick={onClick} scroll={false}>
        {t(direction)}
      </Link>
    </PaginationItem>
  );
}

/**
 * Render the links to the pages before and after the one shown, of `shown` rows, named after the
 * list (`title`); nothing when the list holds one page.
 */
export function ReferencePages({
  list,
  title,
  page,
  shown,
}: {
  readonly list: PagedList;
  /** The title of the list, which names its pages among those of the screen. */
  readonly title: string;
  readonly page: ListPage;
  readonly shown: number;
}) {
  const t = useTranslations("reference.pages");
  const { beyond, previous, next } = pageOffsets(page, shown);
  if (previous === undefined && next === undefined) {
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      {beyond ? <p>{t("beyond")}</p> : null}
      <Pagination aria-label={t("label", { list: title })} className="mx-0 w-auto">
        <PaginationContent>
          {previous === undefined ? null : (
            <PageLink list={list} offset={previous} direction="previous" />
          )}
          {next === undefined ? null : <PageLink list={list} offset={next} direction="next" />}
        </PaginationContent>
      </Pagination>
    </div>
  );
}
