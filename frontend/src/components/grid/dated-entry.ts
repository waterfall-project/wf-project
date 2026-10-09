// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the user entered in the fields of a filter sent as a whole — a period, a text, the bounds of
 * a list —, dated by what the address filtered on when it was entered (`over`), the parameters of
 * the form alone: once the address names another — the entry applied and arrived, or another
 * reached back in the history —, the entry is forgotten, for good, and the fields show the address
 * anew, an address back to the one it was made over too; a change of the address the form does not
 * write — a sort, another filter — leaves it as it is. An entry made while a navigation of the
 * screen was under way — typed on after a search sent, a bound typed while another was — survives
 * the arrival of that navigation, dated by the address it brought; never through the history: an
 * entry made over an address reached back, then given up by « Suivant », is forgotten even when the
 * address it comes to is the one a navigation once brought (`useAskedArrival`); and an entry sent
 * arrives as the address writes it, what was typed before the send forgotten (`sent`). The form is never
 * remounted for it, as a `key` on the address would do: the control that sent it — the button, the
 * field — stays and keeps the focus, which would otherwise fall on the body of the document, the
 * navigation keeping the scroll and moving no focus (`usePendingAddress`).
 */
"use client";

import { useState } from "react";

import { type Asked, useAskedArrival } from "./pending-address";

/** A state, the address it was set over, and the navigation under way when it was last set. */
interface Dated<Value> {
  readonly over: string;
  readonly value: Value;
  readonly during: Asked | undefined;
}

/**
 * A state of a form dated by the address it was set over, `blank` before it is set: forgotten for
 * good once the address names another, unless that address is the one the navigation under way
 * when the state was last set has brought. Each update goes on from the state an update before it
 * in the same event left. Sending the form settles its state (`sent`): what it sent arrives as the
 * address writes it — trimmed, its figures as the contract writes them —, never as it was typed,
 * and only what is typed after the send survives the arrival.
 */
export function useDatedState<Value>(
  over: string,
  blank: () => Value,
): readonly [Value, (update: (before: Value) => Value) => void, () => void] {
  const { underWay, arrived } = useAskedArrival();
  const [state, setState] = useState<Dated<Value>>(() => ({
    over,
    value: blank(),
    during: undefined,
  }));
  let dated = state;
  // The address names another: the state set while the navigation that brought it was under way
  // is kept, dated by it now; any other is forgotten now, not merely hidden, so that an address
  // back to the one it was set over shows that address, not the state given up.
  if (state.over !== over) {
    dated = { over, value: arrived(state.during) ? state.value : blank(), during: undefined };
    setState(dated);
  }
  return [
    dated.value,
    (update) => {
      const during = underWay();
      setState((before) => ({
        over,
        value: update(before.over === over ? before.value : blank()),
        during,
      }));
    },
    () => {
      setState((before) => ({ ...before, during: undefined }));
    },
  ];
}

/**
 * The entry of a form, how to enter a field — a field never entered shows the address —, and how
 * to settle the entry as the form sends it, before it navigates (`useDatedState`).
 */
export function useDatedEntry<Field extends string>(
  over: string,
): {
  readonly entered: Partial<Record<Field, string>>;
  readonly enter: (field: Field, value: string) => void;
  readonly sent: () => void;
} {
  const [entered, update, sent] = useDatedState<Partial<Record<Field, string>>>(over, () => ({}));
  return {
    entered,
    enter: (field, value) => {
      update((before) => ({ ...before, [field]: value }));
    },
    sent,
  };
}
