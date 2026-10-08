// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way through the pages of a list the server pages — the actual costs, the journal of their
 * imports, the imports of a project (US-0260), the projects of the portfolio, the accounts —: the links to the
 * page before and the page after the one shown, when there are, by the pagination of shadcn/ui. A
 * list never shows one of its pages as if it were the whole; a page asked beyond its end says so,
 * and leads back to its last page. A page turned only changes the address (`offset`,
 * `imports_offset`), from the address last asked: a sort or a filter under way is kept, and the
 * list then starts from its first page.
 */
"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { EXCHANGES_PAGE } from "@/components/exchanges/offers";
import { usePendingLink } from "@/components/grid/pending-address";
import { OFFSET } from "@/components/grid/query";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { pageOffsets } from "@/navigation/pages";

import { COSTS_PAGE, IMPORTS_PAGE, pageHref, sameList } from "./address";
import type { ListPage } from "./cost-grid";

/**
 * The lists the server pages, by the parameter of their page and the texts of their links: those
 * of the actual costs, the imports of a project, the projects of the portfolio and the accounts,
 * which share the way through their pages.
 */
const PAGES = {
  costs: { name: COSTS_PAGE, texts: "actualCosts.pages.costs" },
  imports: { name: IMPORTS_PAGE, texts: "actualCosts.pages.imports" },
  exchanges: { name: EXCHANGES_PAGE, texts: "actualCosts.pages.exchanges" },
  projects: { name: OFFSET, texts: "portfolio.pages" },
  users: { name: OFFSET, texts: "admin.pages" },
} as const;

/**
 * A link to another page of a list: the same screen, its query kept, the page changed — or, when
 * the address last asked reads the list otherwise than the one shown, its first page. The journal
 * of the imports and the imports of a project read nothing of the address but their page.
 */
function PageLink({
  list,
  offset,
  direction,
}: {
  readonly list: keyof typeof PAGES;
  readonly offset: number;
  readonly direction: "previous" | "next";
}) {
  const t = useTranslations(PAGES[list].texts);
  const pathname = usePathname();
  const shown = useSearchParams();
  const { name } = PAGES[list];
  const { href, onClick } = usePendingLink((query) =>
    pageHref(
      pathname,
      query,
      name,
      list === "imports" ||
        list === "exchanges" ||
        sameList(query, new URLSearchParams(shown), name)
        ? offset
        : 0,
    ),
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
 * the end leads back to the last one (`pageOffsets`).
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
  const t = useTranslations(PAGES[list].texts);
  const { beyond, previous, next } = pageOffsets(page, shown);
  if (previous === undefined && next === undefined) {
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      {beyond ? <p>{t("beyond")}</p> : null}
      <Pagination aria-label={t("label")}>
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
