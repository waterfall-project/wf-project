// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way through the pages of a list of the administration the server pages — the accounts, the
 * backups —: how many the list holds, and the links to the page before and the page after the one
 * shown, when there are, by the pagination of shadcn/ui. A list never shows one of its pages as if
 * it were the whole; a page asked beyond its end says so, and leads back to its last page
 * (`pageOffsets`). The page is asked by its `offset`, as the contract names it, the other
 * parameters of the address kept by the links (#317). A list that holds nothing says so itself:
 * its pages say nothing.
 */
import { useTranslations } from "next-intl";

import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { type ListPage, pageHref, pageOffsets } from "@/navigation/pages";

/** Where a page of a list stands in it, as the server says. */
export type { ListPage } from "@/navigation/pages";

/**
 * How many the list holds — the sentence given —, and the links to the pages before and after
 * this one, when there are, the other parameters of the address — its filters, when it has —
 * kept.
 */
export function AdminListPages({
  path,
  query,
  page,
  shown,
  count,
}: {
  /** The address of the screen of the list. */
  readonly path: string;
  /** The parameters of the address of the screen, which the links keep. */
  readonly query: URLSearchParams;
  readonly page: ListPage;
  /** How many of the list this page shows. */
  readonly shown: number;
  /** How many the list holds, said in words. */
  readonly count: string;
}) {
  const t = useTranslations("admin.pages");
  if (page.total === 0) {
    // The list holds nothing, which the list itself says.
    return null;
  }
  const { beyond, previous, next } = pageOffsets(page, shown);
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <p className="text-muted-foreground">{count}</p>
      {beyond ? <p>{t("beyond")}</p> : null}
      {previous !== undefined || next !== undefined ? (
        <Pagination aria-label={t("label")} className="mx-0 w-auto">
          <PaginationContent>
            {previous === undefined ? null : (
              <PaginationItem>
                <PaginationPrevious href={pageHref(path, query, previous)}>
                  {t("previous")}
                </PaginationPrevious>
              </PaginationItem>
            )}
            {next === undefined ? null : (
              <PaginationItem>
                <PaginationNext href={pageHref(path, query, next)}>{t("next")}</PaginationNext>
              </PaginationItem>
            )}
          </PaginationContent>
        </Pagination>
      ) : null}
    </div>
  );
}
