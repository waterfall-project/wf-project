// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the user entered in the fields of a filter sent as a whole — a period, a text —, dated by
 * what the address filtered on when it was entered (`over`): once the address names another — the
 * entry applied and arrived, or another reached back in the history —, the entry is forgotten, for
 * good, and the fields show the address anew, an address back to the one it was made over too. The
 * form is never remounted for it, as a `key` on the address would do: the control that sent it —
 * the button, the field — stays and keeps the focus, which would otherwise fall on the body of the
 * document, the navigation keeping the scroll and moving no focus (`usePendingAddress`).
 */
"use client";

import { useState } from "react";

/** The entry of a form, and how to enter a field: a field never entered shows the address. */
export function useDatedEntry<Field extends string>(
  over: string,
): {
  readonly entered: Partial<Record<Field, string>>;
  readonly enter: (field: Field, value: string) => void;
} {
  const [entry, setEntry] = useState<{
    readonly over: string;
    readonly fields: Partial<Record<Field, string>>;
  }>({ over, fields: {} });
  // The address names another: the entry is forgotten now, not merely hidden, so that an address
  // back to the one it was made over shows that address, not the entry given up.
  if (entry.over !== over) {
    setEntry({ over, fields: {} });
  }
  const entered = entry.over === over ? entry.fields : {};
  return {
    entered,
    enter: (field, value) => {
      setEntry({ over, fields: { ...entered, [field]: value } });
    },
  };
}
