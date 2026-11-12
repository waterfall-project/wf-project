// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a grid on one object of a column, as a compact menu in the bar of the grid
 * (WF-IHM-0130, #2916/L6): the menu of one choice of `CheckMenu`, its label on the button, one
 * choice that lifts the filter. As `ChoiceFilter` does for a list beside its grid, a choice only
 * changes the address, under the name of the contract; the page reads the grid anew, which the
 * server filters, the choice shown meanwhile. A choice goes on from the address last asked
 * (`usePendingAddress`). An object the address names that is not offered stays chosen, under its
 * identifier, to be cleared.
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { usePathname } from "next/navigation";
import { useOptimistic, useTransition } from "react";

import { CheckMenu } from "./check-menu";
import type { Choice } from "./choice-filter";
import { filterHref } from "./filters";
import { usePendingAddress } from "./pending-address";

/** Render the filter of a grid on one object of a column, as a menu of the bar. */
export function BarChoice({
  name,
  label,
  every,
  choices,
  chosen,
  page,
  lifts = [],
}: {
  /** The parameter of the address the filter writes, as the contract names it. */
  readonly name: string;
  /** What the filter filters on: it names the menu. */
  readonly label: string;
  /** The text of the choice that lifts the filter. */
  readonly every: string;
  readonly choices: readonly Choice[];
  /** The object the address filters on; none, every one. */
  readonly chosen: string | undefined;
  /** The parameter of the page of a list the server pages, which a choice takes back to its first. */
  readonly page?: string | undefined;
  /** Parameters of the address a choice lifts besides the page. */
  readonly lifts?: readonly string[] | undefined;
}) {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  // The object chosen, shown until the server answers for it (défaut n° 21 de `typescript.md`).
  const [shown, show] = useOptimistic(chosen ?? "");
  const [, startTransition] = useTransition();
  const unoffered =
    chosen !== undefined && !choices.some((choice) => choice.value === chosen) ? chosen : undefined;
  // Every parameter the choices write: the one a choice writes, the others lifted.
  const names = [...new Set([name, ...choices.map((choice) => choice.name ?? name)])];
  return (
    <CheckMenu
      compact
      label={label}
      every={every}
      multiple={false}
      options={[
        ...choices.map((choice) => ({ value: choice.value, text: choice.text })),
        ...(unoffered === undefined ? [] : [{ value: unoffered, text: unoffered }]),
      ]}
      chosen={shown === "" ? [] : [shown]}
      onChange={(values) => {
        const value = values[0] ?? "";
        const written = choices.find((choice) => choice.value === value)?.name ?? name;
        startTransition(() => {
          show(value);
          request((query) =>
            filterHref(pathname, query, written, value, [
              ...(page === undefined ? [] : [page]),
              ...lifts,
              ...names.filter((each) => each !== written),
            ]),
          );
        });
      }}
    />
  );
}
