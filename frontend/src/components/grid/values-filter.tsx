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
  lifts = [],
  said,
  flag,
}: Pick<ValuesAddress<Value>, "name" | "page" | "exhaustive" | "lifted" | "unnamed"> & {
  /** The name of the menu: what the filter filters on. */
  readonly label: string;
  /** The text of the choice that lifts the filter. */
  readonly every: string;
  /** The values of the contract, in its order, each with its text. */
  readonly values: readonly FilterValue<Value>[];
  /** The values the address filters on. */
  readonly chosen: readonly Value[];
  /**
   * Parameters of the address a choice lifts: those of before the filter, which it replaces
   * (`include_inactive=false`, which the state of the accounts now says).
   */
  readonly lifts?: readonly string[] | undefined;
  /**
   * What an address of before says of the values, by a parameter that `lifts` removes
   * (`include_inactive=false`: the active ones alone): the value it reads as, while the parameter
   * of the filter names none.
   */
  readonly said?:
    | { readonly name: string; readonly value: string; readonly reads: Value }
    | undefined;
  /**
   * One of the `values` that the address writes under a parameter of its own, `true` when checked
   * (« Sans rôle », `without_access_role`), beside the others, in union with them; it does not count
   * among the values of the filter (`exhaustive`).
   */
  readonly flag?: { readonly value: Value; readonly name: string } | undefined;
}) {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const filter = {
    name,
    values: values.map(({ value }) => value).filter((value) => value !== flag?.value),
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
        const base = new URLSearchParams(query);
        for (const lift of lifts) {
          base.delete(lift);
        }
        let asked = readFilter(query, filter);
        if (said !== undefined && query.get(name) === null && query.get(said.name) === said.value) {
          asked = [said.reads];
        }
        const next = make([
          ...(flag !== undefined && query.get(flag.name) === "true" ? [flag.value] : []),
          ...asked,
        ]);
        if (flag !== undefined) {
          if (next.includes(flag.value)) {
            base.set(flag.name, "true");
          } else {
            base.delete(flag.name);
          }
        }
        const href = valuesHref(pathname, base, filter, next);
        // As the address asked names them: every value of an exhaustive filter lifts it.
        const written = new URLSearchParams(href.split("?")[1] ?? "");
        show([
          ...(flag !== undefined && written.get(flag.name) === "true" ? [flag.value] : []),
          ...readValues(written, name, filter.values),
        ]);
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
