// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the user entered in the fields of a filter sent as a whole — a period, a text, the bounds of
 * a list —, dated by what the address filtered on when it was entered (`over`), the parameters of
 * the form alone: once the address names another — the entry applied and arrived, or another
 * reached back in the history —, the entry is forgotten, for good, and the fields show the address
 * anew, an address back to the one it was made over too; a change of the address the form does not
 * write — a sort, another filter — leaves it as it is. The form is never remounted for it, as a
 * `key` on the address would do: the control that sent it — the button, the field — stays and keeps
 * the focus, which would otherwise fall on the body of the document, the navigation keeping the
 * scroll and moving no focus (`usePendingAddress`).
 */
"use client";

import { useState } from "react";

/**
 * A state of a form dated by the address it was set over, `blank` before it is set: forgotten for
 * good once the address names another. Each update goes on from the state an update before it in
 * the same event left.
 */
export function useDatedState<Value>(
  over: string,
  blank: () => Value,
): readonly [Value, (update: (before: Value) => Value) => void] {
  const [state, setState] = useState(() => ({ over, value: blank() }));
  // The address names another: the state is forgotten now, not merely hidden, so that an address
  // back to the one it was set over shows that address, not the state given up.
  if (state.over !== over) {
    setState({ over, value: blank() });
  }
  const value = state.over === over ? state.value : blank();
  return [
    value,
    (update) => {
      setState((before) => ({
        over,
        value: update(before.over === over ? before.value : blank()),
      }));
    },
  ];
}

/** The entry of a form, and how to enter a field: a field never entered shows the address. */
export function useDatedEntry<Field extends string>(
  over: string,
): {
  readonly entered: Partial<Record<Field, string>>;
  readonly enter: (field: Field, value: string) => void;
} {
  const [entered, update] = useDatedState<Partial<Record<Field, string>>>(over, () => ({}));
  return {
    entered,
    enter: (field, value) => {
      update((before) => ({ ...before, [field]: value }));
    },
  };
}
