// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way through the pages of a list of the administration the server pages — the accounts, the
 * backups —: how many the list holds, and the links to the page before and the page after the one
 * shown, when there are, by the pagination of shadcn/ui. A list never shows one of its pages as if
 * it were the whole; a page asked beyond its end says so, and leads back to its last page. The page
 * is asked by its `offset`, as the contract names it.
 */
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import type { SearchParameters } from "@/navigation/context";

/** Where a page of a list stands in it, as the server says. */
export type ListPage = components["schemas"]["PaginationMeta"];

/** The offset the address asks for, or none when it asks for none a server could take. */
export function offsetOf(search: SearchParameters): number | undefined {
  const value = search.get("offset");
  const offset = Number(value);
  return value !== null && Number.isSafeInteger(offset) && offset > 0 ? offset : undefined;
}

/** The address of a page of the list of a screen. */
function pageHref(path: string, offset: number): string {
  return offset > 0 ? `${path}?offset=${String(offset)}` : path;
}

/**
 * How many the list holds — the sentence given —, and the links to the pages before and after
 * this one, when there are.
 */
export function ListPages({
  path,
  page,
  shown,
  count,
}: {
  /** The address of the screen of the list. */
  readonly path: string;
  readonly page: ListPage;
  /** How many of the list this page shows. */
  readonly shown: number;
  /** How many the list holds, said in words. */
  readonly count: string;
}) {
  const t = useTranslations("admin.pages");
  const beyond = shown === 0 && page.offset >= page.total && page.total > 0;
  const before = page.offset > 0;
  const after = page.offset + shown < page.total;
  // The page before: the one just before, or the last page when the address asked one beyond.
  const previous = beyond
    ? Math.floor((page.total - 1) / page.limit) * page.limit
    : Math.max(0, page.offset - page.limit);
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <p className="text-muted-foreground">{count}</p>
      {beyond ? <p>{t("beyond")}</p> : null}
      {before || after ? (
        <Pagination aria-label={t("label")} className="mx-0 w-auto">
          <PaginationContent>
            {before ? (
              <PaginationItem>
                <PaginationPrevious href={pageHref(path, previous)}>
                  {t("previous")}
                </PaginationPrevious>
              </PaginationItem>
            ) : null}
            {after ? (
              <PaginationItem>
                <PaginationNext href={pageHref(path, page.offset + shown)}>
                  {t("next")}
                </PaginationNext>
              </PaginationItem>
            ) : null}
          </PaginationContent>
        </Pagination>
      ) : null}
    </div>
  );
}
