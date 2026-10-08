// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a list on one object of a column (WF-IHM-0130), chosen in a list of the browser
 * among those offered, in the order given — the node of organisation, the nature of the categories,
 * the author and the project of the journal of audit, the sub-project of the actual costs, the
 * horizon of a view of the portfolio —, and one choice that lifts the filter. An object the address
 * names that is not offered — none the session reads — stays chosen, under the name given or its
 * identifier, to be cleared. A choice only changes the address, under the name of the contract,
 * back to the first page of a list the server pages (`filterHref`); the page reads the list anew,
 * which the server filters. A choice goes on from the address last asked (`usePendingAddress`).
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { usePathname } from "next/navigation";
import { useId } from "react";

import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";

import { filterHref } from "./filters";
import { usePendingAddress } from "./pending-address";

/** An object a list may be filtered on, by its identifier and the text that names it. */
export interface Choice {
  readonly value: string;
  readonly text: string;
}

/** Render the filter of a list on one object of a column, the one the address names chosen. */
export function ChoiceFilter({
  id,
  name,
  label,
  every,
  choices,
  chosen,
  unknown,
  page,
}: {
  /** The identifier of its list, when another control gives the focus back to it. */
  readonly id?: string | undefined;
  /** The parameter of the address the filter writes, as the contract names it. */
  readonly name: string;
  /** What the filter filters on. */
  readonly label: string;
  /** The text of the choice that lifts the filter. */
  readonly every: string;
  readonly choices: readonly Choice[];
  /** The object the address filters on; none, every one. */
  readonly chosen: string | undefined;
  /** The name of the object chosen when it is not offered; its identifier otherwise. */
  readonly unknown?: string | undefined;
  /** The parameter of the page of a list the server pages, which a choice takes back to its first. */
  readonly page?: string | undefined;
}) {
  const own = useId();
  const select = id ?? own;
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const offered = chosen === undefined || choices.some((choice) => choice.value === chosen);
  return (
    <div className="flex items-center gap-2 text-sm">
      <Label htmlFor={select} className="whitespace-nowrap">
        {label}
      </Label>
      <div className="w-56 shrink-0">
        <NativeSelect
          id={select}
          value={chosen ?? ""}
          onChange={(event) => {
            const value = event.target.value;
            request((query) => filterHref(pathname, query, name, value, page));
          }}
        >
          <option value="">{every}</option>
          {choices.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.text}
            </option>
          ))}
          {offered ? null : <option value={chosen}>{unknown ?? chosen}</option>}
        </NativeSelect>
      </div>
    </div>
  );
}
