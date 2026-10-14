// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the audit columns of the tables of the accounts and of the access roles
 * (WF-IHM-0130, #936), as the address asks them (`audit-address.ts`): for the creation and for the
 * last modification, a period of local days, both included — sent as the start of the first and the
 * start of the day after the last (`PeriodFilter`, `day`), a side the API refused said at its field —,
 * and an author (`AuthorFilter`), an account chosen that the page does not offer named as the page
 * read it.
 *
 * Neither server nor client: the pages render it with their filters.
 */
import { useTranslations } from "next-intl";
import { Fragment } from "react";

import { PeriodFilter } from "@/components/grid/period-filter";

import { AUTHORS, type AuditFilters, type AuthorChoice, PERIODS, WRITTEN } from "./audit-address";
import { AuthorFilter } from "./author-filter";

/** Render the filters of the audit columns of a table. */
export function AuditFilterBar({
  filters,
  authors,
  searchable,
  page,
}: {
  readonly filters: AuditFilters;
  /** The accounts offered as authors, in the order the page gives them. */
  readonly authors: readonly AuthorChoice[];
  /** Whether other accounts may be found by a search of the accounts. */
  readonly searchable: boolean;
  /** The parameter of the page of a list the server pages, which a filter takes back to its first. */
  readonly page?: string | undefined;
}) {
  const t = useTranslations("grid.columns");
  return WRITTEN.map((column) => (
    <Fragment key={column}>
      <PeriodFilter
        label={t(`${column}At`)}
        kind="day"
        period={filters.periods[column]}
        refused={filters.refused?.[column]}
        names={PERIODS[column]}
        page={page}
      />
      <AuthorFilter
        label={t(`${column}By`)}
        names={AUTHORS[column]}
        chosen={filters.authors[column]}
        offered={authors}
        named={filters.named ?? []}
        searchable={searchable}
        page={page}
      />
    </Fragment>
  ));
}
