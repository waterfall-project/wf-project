// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What an entry of a cell reads and shows (WF-IHM-0040): the text it starts from, the value it
 * validates — a number in the format of the language, as the exact decimal of the contract —,
 * and what the cell shows of it until the server answers. Never through a float (WF-DAT-0100).
 */
import { editableDecimal, formatDecimal, formatMoney, parseDecimal } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

import type { CellValue, EntryKind } from "./columns";

/**
 * The value an entry validates, as the contract writes it — a text as typed, a number as the
 * exact decimal of the contract, `null` for a cell emptied —; `undefined` for what is no number
 * of the language.
 */
export function parsedEntry(
  kind: EntryKind,
  text: string,
  locale: Locale,
): { readonly value: string | null } | undefined {
  if (kind.type === "text") {
    return { value: text };
  }
  if (text.trim() === "") {
    return kind.nullable ? { value: null } : undefined;
  }
  const value = parseDecimal(text, locale, kind.type);
  return value === undefined ? undefined : { value };
}

/** What a cell shows of a value validated, until the server answers. */
export function shownEntry(kind: EntryKind, value: string | null, locale: Locale): string {
  if (value === null) {
    return "";
  }
  switch (kind.type) {
    case "decimal":
      return formatDecimal(value, locale);
    case "money":
      return formatMoney(value, locale);
    case "text":
      return value;
  }
}

/**
 * The text an entry starts from: the character typed, or the value of the cell as one types it —
 * a number with the decimal separator of the language.
 */
export function startingText(
  kind: EntryKind,
  value: CellValue,
  typed: string | undefined,
  locale: Locale,
): string {
  if (typed !== undefined) {
    return typed;
  }
  if (value === null || value === undefined) {
    return "";
  }
  return kind.type === "text" ? value : editableDecimal(value, locale);
}
