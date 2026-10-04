// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way through the pages of a list the server pages — the actual costs, the journal of their
 * imports —: the links to the page before and the page after the one shown, when there are, by the
 * pagination of shadcn/ui. A list never shows one of its pages as if it were the whole; a page
 * asked beyond its end says so, and leads back to its last page. A page turned only changes the
 * address (`offset`, `imports_offset`), from the address last asked: a sort or a filter under way
 * is kept.
 */
"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { usePendingLink } from "@/components/grid/pending-address";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";

import { COSTS_PAGE, IMPORTS_PAGE, pageHref } from "./address";
import type { ListPage } from "./cost-grid";

/** The lists of the screen that the server pages, by the parameter of their page. */
const PAGES = { costs: COSTS_PAGE, imports: IMPORTS_PAGE } as const;

/** A link to another page of a list: the same screen, its query kept, the page changed. */
function PageLink({
  list,
  offset,
  direction,
}: {
  readonly list: keyof typeof PAGES;
  readonly offset: number;
  readonly direction: "previous" | "next";
}) {
  const t = useTranslations(`actualCosts.pages.${list}`);
  const pathname = usePathname();
  const { href, onClick } = usePendingLink((query) =>
    pageHref(pathname, query, PAGES[list], offset),
  );
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
 * Render the links to the pages before and after the one shown, of `shown` rows; a page beyond
 * the end leads back to the last one.
 */
export function ListPages({
  list,
  page,
  shown,
}: {
  readonly list: keyof typeof PAGES;
  readonly page: ListPage;
  readonly shown: number;
}) {
  const t = useTranslations(`actualCosts.pages.${list}`);
  const beyond = shown === 0 && page.offset > 0 && page.offset >= page.total;
  const before = page.offset > 0;
  const after = page.offset + shown < page.total;
  if (!before && !after) {
    return null;
  }
  const previous = beyond
    ? Math.floor(Math.max(0, page.total - 1) / page.limit) * page.limit
    : Math.max(0, page.offset - page.limit);
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      {beyond ? <p>{t("beyond")}</p> : null}
      <Pagination aria-label={t("label")}>
        <PaginationContent>
          {before ? <PageLink list={list} offset={previous} direction="previous" /> : null}
          {after ? <PageLink list={list} offset={page.offset + shown} direction="next" /> : null}
        </PaginationContent>
      </Pagination>
    </div>
  );
}
