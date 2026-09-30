// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What an entry of a cell reads and shows (WF-IHM-0040): the text it starts from, the value it
 * validates — a number in the format of the language, as the exact decimal of the contract, the
 * identifier of a choice —,
 * and what the cell shows of it until the server answers. Never through a float (WF-DAT-0100).
 */
import { editableDecimal, formatDecimal, formatMoney, parseDecimal } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

import type { CellValue, EntryKind } from "./columns";

/**
 * Why an entry is not validated: a cell that may not be emptied left blank, a text too long, no
 * number of the language, an amount with more than two decimals.
 */
export type EntryProblem = "required" | "tooLong" | "notANumber" | "twoDecimals";

/**
 * The value an entry validates, as the contract writes it — a text as typed, a number as the
 * exact decimal of the contract, the identifier chosen, `null` for a cell emptied —, or why it is
 * not.
 */
export function parsedEntry(
  kind: EntryKind,
  text: string,
  locale: Locale,
): { readonly value: string | null } | { readonly problem: EntryProblem } {
  if (kind.type === "text") {
    if (text.trim() === "") {
      return { problem: "required" };
    }
    return text.length > kind.maxLength ? { problem: "tooLong" } : { value: text };
  }
  if (kind.type === "choice") {
    if (text === "") {
      return kind.nullable ? { value: null } : { problem: "required" };
    }
    return { value: text };
  }
  if (text.trim() === "") {
    return kind.nullable ? { value: null } : { problem: "required" };
  }
  const value = parseDecimal(text, locale, kind.type);
  if (value !== undefined) {
    return { value };
  }
  // A number of the language all the same, but with more decimals than an amount keeps.
  return parseDecimal(text, locale) === undefined
    ? { problem: "notANumber" }
    : { problem: "twoDecimals" };
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
    case "choice":
      return kind.choices.find((choice) => choice.id === value)?.label ?? "";
    case "text":
      return value;
  }
}

/**
 * The text an entry starts from: the character typed, or the value of the cell as one types it —
 * a number with the decimal separator of the language. A list starts from the choice made.
 */
export function startingText(
  kind: EntryKind,
  value: CellValue,
  typed: string | undefined,
  locale: Locale,
): string {
  if (typed !== undefined && kind.type !== "choice") {
    return typed;
  }
  if (value === null || value === undefined) {
    return "";
  }
  return kind.type === "decimal" || kind.type === "money" ? editableDecimal(value, locale) : value;
}
