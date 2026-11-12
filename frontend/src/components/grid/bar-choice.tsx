// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a grid on one object of a column, as a compact menu in the bar of the grid
 * (WF-IHM-0130, #2916/L6): the menu of one choice of `CheckMenu`, its label on the button, one
 * choice that lifts the filter. What a choice does with the address is that of `ChoiceFilter`
 * (`useChoice`): the page reads the grid anew, which the server filters, the choice shown
 * meanwhile; an object the address names that is not offered stays chosen, under its identifier.
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { CheckMenu } from "./check-menu";
import type { Choice } from "./choice-filter";
import { useChoice } from "./use-choice";

/** Render the filter of a grid on one object of a column, as a menu of the bar. */
export function BarChoice({
  name,
  label,
  every,
  choices,
  chosen,
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
}) {
  const { shown, unoffered, choose } = useChoice(name, choices, chosen, []);
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
        choose(values[0] ?? "");
      }}
    />
  );
}
