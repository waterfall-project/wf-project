// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a filter on one object of a column does with its address, as `ChoiceFilter` (a list beside
 * its grid) and `BarChoice` (a menu of the bar) both do (WF-IHM-0130, #2916/L6): the object chosen,
 * shown until the server answers for it (défaut n° 21 de `typescript.md`); the object the address
 * names that is not offered, kept to be cleared; and the choice, which only changes the address
 * under the name of the contract, the parameters of the other choices lifted, from the address last
 * asked (`usePendingAddress`).
 */
"use client";

import { usePathname } from "next/navigation";
import { useOptimistic, useTransition } from "react";

import type { Choice } from "./choice-filter";
import { filterHref } from "./filters";
import { usePendingAddress } from "./pending-address";

/** What the filter shows and does: the value shown, the one unoffered, and the choice of a value. */
export interface ChoiceState {
  /** The value chosen, shown until the server answers for it; empty, every one. */
  readonly shown: string;
  /** The value the address names that the choices do not offer; none otherwise. */
  readonly unoffered: string | undefined;
  readonly choose: (value: string) => void;
}

/** Follow a filter on one object: `name` is the parameter it writes, as the contract names it. */
export function useChoice(
  name: string,
  choices: readonly Choice[],
  chosen: string | undefined,
  lifted: readonly string[],
): ChoiceState {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const [shown, show] = useOptimistic(chosen ?? "");
  const [, startTransition] = useTransition();
  const unoffered =
    chosen !== undefined && !choices.some((choice) => choice.value === chosen) ? chosen : undefined;
  // Every parameter the choices write: the one a choice writes, the others lifted.
  const names = [...new Set([name, ...choices.map((choice) => choice.name ?? name)])];
  return {
    shown,
    unoffered,
    choose: (value) => {
      const written = choices.find((choice) => choice.value === value)?.name ?? name;
      startTransition(() => {
        show(value);
        request((query) =>
          filterHref(pathname, query, written, value, [
            ...lifted,
            ...names.filter((each) => each !== written),
          ]),
        );
      });
    },
  };
}
