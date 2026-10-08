// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way through the pages of a list the server pages — the actual costs, the journal of their
 * imports, the imports of a project (US-0260), the projects of the home and of the portfolio, the
 * accounts, the journal of audit, the lists of the reference data (#509, #510, #533) —: the links to
 * the page before and the page after the one shown, when there are, by the pagination of shadcn/ui.
 * A list never shows one of its pages as if it were the whole — its totals row says how many it
 * holds —; a page asked beyond its end says so, and leads back to its last page (`pageOffsets`, the
 * one rule of every list, #317).
 *
 * A page turned only changes the address, under the name of the page of the list, from the address
 * last asked (`usePendingLink`): when that address reads the list otherwise than the one shown — a
 * sort, a search or a filter of its own under way (`readingOf`) —, the link leads to its first page,
 * the place of a row in the list shown meaning nothing in the other; a sort or a page of another
 * list of the screen leaves it as it is (#294).
 *
 * Every prop is data, never a function: a server component hands it over (défaut n° 12 de
 * `typescript.md`).
 */
"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { type ListPage, type PagedList, pageOffsets, readingOf } from "@/navigation/pages";

import { filterHref } from "./filters";
import { usePendingLink } from "./pending-address";

/**
 * The texts of the pages of a list alone on its screen, or of one of the costs: those of its links,
 * and the name of its pages.
 */
export type ListTexts =
  | "actualCosts.pages.costs"
  | "actualCosts.pages.imports"
  | "actualCosts.pages.exchanges"
  | "portfolio.pages"
  | "admin.pages";

/** The texts of the pages of a list among several of the reference data, named after its title. */
const NAMED = "reference.pages";

/** How the pages of a list are named: by texts of their own, or by the title of their list. */
type Naming =
  | { readonly texts: ListTexts; readonly title?: never }
  | {
      /** The title of the list, which names its pages among those of the screen. */
      readonly title: string;
      readonly texts?: never;
    };

/** A link to another page of a list, or to its first one when the address last asked reads it otherwise. */
function PageLink({
  list,
  offset,
  direction,
  text,
}: {
  readonly list: PagedList;
  readonly offset: number;
  readonly direction: "previous" | "next";
  readonly text: string;
}) {
  const pathname = usePathname();
  const shown = useSearchParams();
  const reads = list.reads.filter((name) => name !== list.page);
  const { href, onClick } = usePendingLink((query) => {
    const same = readingOf(query, reads) === readingOf(new URLSearchParams(shown), reads);
    const at = same ? offset : 0;
    return filterHref(pathname, query, list.page, at > 0 ? String(at) : undefined);
  });
  const Link = direction === "previous" ? PaginationPrevious : PaginationNext;
  return (
    <PaginationItem>
      <Link href={href} onClick={onClick} scroll={false}>
        {text}
      </Link>
    </PaginationItem>
  );
}

/**
 * Render the links to the pages before and after the one shown, of `shown` rows, named by the texts
 * of the list or after its title; nothing when the list holds one page.
 */
export function ListPages({
  list,
  page,
  shown,
  ...naming
}: {
  readonly list: PagedList;
  readonly page: ListPage;
  readonly shown: number;
} & Naming) {
  const t = useTranslations(naming.texts ?? NAMED);
  const named = useTranslations(NAMED);
  const { beyond, previous, next } = pageOffsets(page, shown);
  if (previous === undefined && next === undefined) {
    return null;
  }
  const label = naming.texts === undefined ? named("label", { list: naming.title }) : t("label");
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      {beyond ? <p>{t("beyond")}</p> : null}
      <Pagination aria-label={label}>
        <PaginationContent>
          {previous === undefined ? null : (
            <PageLink list={list} offset={previous} direction="previous" text={t("previous")} />
          )}
          {next === undefined ? null : (
            <PageLink list={list} offset={next} direction="next" text={t("next")} />
          )}
        </PaginationContent>
      </Pagination>
    </div>
  );
}
