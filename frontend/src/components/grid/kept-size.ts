// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The number of rows per page of a flat table recorded with the settings of its grid
 * (`GridPreferences.page_size`, WF-IHM-0060): each time the page shows a size that differs from the
 * one kept, the one shown. The address is the truth of the screen, and carries the size under the
 * name of the contract, `limit` — the choice of « Lignes par page » (`list-pages.tsx`) only changes
 * it —; the page finds the size kept again when the address says none (`readGridQuery`).
 */
"use client";

import { useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { CONTRACT_ADDRESS, DEFAULT_PAGE_SIZE, type GridAddress, pageSizeOf } from "./query";

/**
 * Record the size of the pages a grid shows when it differs from the one kept (`kept`, fifty when
 * the account keeps none): `record` receives the size to keep. An address that names no size, or
 * one the contract would refuse, records nothing; nor does a grid that is a tree (`offered` false),
 * which has no pages and offers no such choice.
 */
export function useKeptPageSize(
  address: GridAddress | undefined,
  kept: number | undefined,
  record: (size: number) => void,
  offered: boolean,
): void {
  const asked = pageSizeOf(useSearchParams().get((address ?? CONTRACT_ADDRESS).limit));
  useEffect(() => {
    if (offered && asked !== undefined && asked !== (kept ?? DEFAULT_PAGE_SIZE)) {
      record(asked);
    }
  }, [asked, kept, offered, record]);
}
