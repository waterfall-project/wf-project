// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * « Lignes par page »: the choice of the number of rows of the pages of a flat table, 10, 25, 50
 * or 100 (WF-IHM-0060), beside its pagination. The size is carried by the address, under the name of
 * the contract (`limit`), like the page: a choice writes it and takes the list back to its first
 * page, the rows of a page of another size meaning nothing in this one, and goes on from the address
 * last asked (`usePendingAddress`). The grid records it with its settings once the page shows it
 * (`kept-size.ts`), and the page finds it again when the address names none. A tree has no pages,
 * and offers no such choice.
 */
"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useId, useOptimistic, useTransition } from "react";

import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";

import { filterHref } from "./filters";
import { usePendingAddress } from "./pending-address";
import { DEFAULT_PAGE_SIZE, PAGE_SIZES, pageSizeOf } from "./query";

/**
 * Render the choice of the size of the pages of a list: `size` is the parameter of the address that
 * names it, `page` the one that names the page it takes back to the first, `current` the size the
 * server read, and `title` the name of the list among those of its screen, if there are several.
 */
export function PageSizeChoice({
  size,
  page,
  current,
  title,
}: {
  readonly size: string;
  readonly page: string;
  readonly current: number;
  readonly title?: string | undefined;
}) {
  const t = useTranslations("grid.pageSize");
  const id = useId();
  const pathname = usePathname();
  const { request } = usePendingAddress();
  // The size chosen, shown until the server answers for it.
  const [shown, show] = useOptimistic(String(pageSizeOf(current) ?? DEFAULT_PAGE_SIZE));
  const [, startTransition] = useTransition();
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor={id} className="whitespace-nowrap">
        {t("label")}
      </Label>
      <div className="w-20 shrink-0">
        <NativeSelect
          id={id}
          value={shown}
          aria-label={title === undefined ? undefined : t("named", { list: title })}
          onChange={(event) => {
            const value = event.target.value;
            startTransition(() => {
              show(value);
              request((query) => filterHref(pathname, query, size, value, page));
            });
          }}
        >
          {PAGE_SIZES.map((each) => (
            <option key={each} value={String(each)}>
              {each}
            </option>
          ))}
        </NativeSelect>
      </div>
    </div>
  );
}
