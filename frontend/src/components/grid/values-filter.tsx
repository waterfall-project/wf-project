// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a list on the values of one of its columns (WF-IHM-0130), beside its grid: a menu
 * of boxes to check (`CheckMenu`), one for each value of the contract, checked when the address
 * filters on it, and one for every value (#2916) —
 * the states of the risks and of the projects, the zones of the indices, the origins of the
 * accounts, the capacities of the contributors. A value chosen only changes the address, under the
 * name of the contract (`filters.ts`); the page reads the list anew, which the server filters. A
 * value chosen goes on from the address last asked (`usePendingAddress`): a second value chosen
 * before the first has arrived, or right after a sort, keeps them. The values asked show checked
 * until the server answers for them, then those of the address (défaut n° 21 de `typescript.md`).
 *
 * Every prop is data — the texts are given translated, or drawn already, as a badge —, never a
 * function: a server component hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { usePathname } from "next/navigation";
import { type ReactNode, useOptimistic, useTransition } from "react";

import { CheckMenu } from "./check-menu";
import { readFilter, readValues, type ValuesAddress, valuesHref } from "./filters";
import { usePendingAddress } from "./pending-address";

/** A value a list may be filtered on, with what names it: a text, or a badge drawn. */
export interface FilterValue<Value extends string> {
  readonly value: Value;
  readonly text: ReactNode;
}

/** Render the filter of a list on the values of a column, those the address names checked. */
export function ValuesFilter<Value extends string>({
  name,
  label,
  every,
  values,
  chosen,
  page,
  exhaustive,
  lifted,
  unnamed,
}: Pick<ValuesAddress<Value>, "name" | "page" | "exhaustive" | "lifted" | "unnamed"> & {
  /** The name of the menu: what the filter filters on. */
  readonly label: string;
  /** The text of the choice that lifts the filter. */
  readonly every: string;
  /** The values of the contract, in its order, each with its text. */
  readonly values: readonly FilterValue<Value>[];
  /** The values the address filters on. */
  readonly chosen: readonly Value[];
}) {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const filter = {
    name,
    values: values.map(({ value }) => value),
    page,
    exhaustive,
    lifted,
    unnamed,
  };
  // The values asked, pressed until the server answers for them: the buttons would otherwise show
  // the address until the navigation arrives — the choice seemingly undone for as long as the page
  // is read anew —, and again the address should another navigation replace it.
  const [shown, show] = useOptimistic(chosen);
  const [, startTransition] = useTransition();
  /** Filter on the values a change makes of those last asked. */
  const change = (make: (asked: readonly Value[]) => readonly Value[]) => {
    startTransition(() => {
      request((query) => {
        const href = valuesHref(pathname, query, filter, make(readFilter(query, filter)));
        // As the address asked names them: every value of an exhaustive filter lifts it.
        show(readValues(new URLSearchParams(href.split("?")[1] ?? ""), name, filter.values));
        return href;
      });
    });
  };
  return (
    <CheckMenu
      label={label}
      every={every}
      multiple
      options={values.map(({ value, text }) => ({ value, text }))}
      chosen={shown}
      onChange={(_values, toggled) => {
        change((asked) => {
          if (toggled === undefined) {
            return [];
          }
          const value = values.find((each) => each.value === toggled.value)?.value;
          if (value === undefined) {
            return asked;
          }
          return toggled.checked
            ? [...asked.filter((each) => each !== value), value]
            : asked.filter((each) => each !== value);
        });
      }}
    />
  );
}
