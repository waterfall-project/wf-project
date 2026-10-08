// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a list on the values of one of its columns (WF-IHM-0130), beside its grid: a button
 * for each value of the contract, pressed when the address filters on it, and one for every value —
 * the origins of the accounts, the capacities of the contributors. A value chosen only changes the
 * address, under the name of the contract (`filters.ts`); the page reads the list anew, which the
 * server filters. A value chosen goes on from the address last asked (`usePendingAddress`): a second
 * value chosen before the first has arrived, or right after a sort, keeps them.
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { Circle, CircleCheck, ListFilter } from "lucide-react";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";

import { readValues, valuesHref } from "./filters";
import { usePendingAddress } from "./pending-address";

/** A value a list may be filtered on, with the text that names it. */
export interface FilterValue<Value extends string> {
  readonly value: Value;
  readonly text: string;
}

/** Render the filter of a list on the values of a column, those the address names pressed. */
export function ValuesFilter<Value extends string>({
  name,
  label,
  every,
  values,
  chosen,
  page,
}: {
  /** The parameter of the address the filter writes, as the contract names it. */
  readonly name: string;
  /** The name of the group of buttons: what the filter filters on. */
  readonly label: string;
  /** The text of the button that lifts the filter. */
  readonly every: string;
  /** The values of the contract, in its order, each with its text. */
  readonly values: readonly FilterValue<Value>[];
  /** The values the address filters on. */
  readonly chosen: readonly Value[];
  /** The parameter of the page of a list the server pages, which a filter takes back to its first. */
  readonly page?: string;
}) {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const filter = {
    name,
    values: values.map(({ value }) => value),
    ...(page === undefined ? {} : { page }),
  };
  /** Filter on the values a change makes of those last asked. */
  const change = (make: (asked: readonly Value[]) => readonly Value[]) => {
    request((query) =>
      valuesHref(pathname, query, filter, make(readValues(query, name, filter.values))),
    );
  };
  const everyOne = chosen.length === 0;
  return (
    <div role="group" aria-label={label} className="flex flex-wrap items-center gap-1.5">
      <Button
        size="sm"
        variant={everyOne ? "default" : "outline"}
        aria-pressed={everyOne}
        onClick={() => {
          change(() => []);
        }}
      >
        <ListFilter aria-hidden="true" className="size-4" />
        {every}
      </Button>
      {values.map(({ value, text }) => {
        // Pressed as the address shows it; a change goes on from the values last asked.
        const pressed = chosen.includes(value);
        const Icon = pressed ? CircleCheck : Circle;
        return (
          <Button
            key={value}
            size="sm"
            variant={pressed ? "default" : "outline"}
            aria-pressed={pressed}
            onClick={() => {
              change((asked) =>
                asked.includes(value) ? asked.filter((each) => each !== value) : [...asked, value],
              );
            }}
          >
            <Icon aria-hidden="true" className="size-4" />
            {text}
          </Button>
        );
      })}
    </div>
  );
}
