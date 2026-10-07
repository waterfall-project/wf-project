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

import type { CellValue, Choice, EntryKind } from "./columns";

/**
 * Why an entry is not validated: a cell that may not be emptied left blank, a text too long, no
 * number of the language, an amount with more than two decimals, a whole number with a fraction.
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
  if (kind.type === "integer") {
    // Digits alone, as the contract takes a whole number: no sign, no separator, no fraction.
    // Nine digits at most keep the number exact.
    return /^\d{1,9}$/.test(text.trim())
      ? { value: text.trim().replace(/^0+(?=\d)/, "") }
      : { problem: "notANumber" };
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
    case "integer":
      return formatDecimal(value, locale);
    case "money":
      return formatMoney(value, locale);
    case "choice":
      return kind.choices().find((choice) => choice.id === value)?.label ?? "";
    case "text":
      return value;
  }
}

/**
 * The first choice that may be chosen whose name starts with what was typed, whatever its case
 * and its accents, in the order of the list.
 */
export function firstChoice(
  choices: readonly Choice[],
  typed: string,
  locale: Locale,
): Choice | undefined {
  const collator = new Intl.Collator(locale, { sensitivity: "base" });
  return choices.find(
    (choice) => choice.active && collator.compare(choice.label.slice(0, typed.length), typed) === 0,
  );
}

/**
 * The text an entry starts from: the character typed, or the value of the cell as one types it —
 * a number with the decimal separator of the language. A list starts from the choice made, or
 * from the first whose name starts with the character typed.
 */
export function startingText(
  kind: EntryKind,
  value: CellValue,
  typed: string | undefined,
  locale: Locale,
): string {
  if (typed !== undefined && kind.type === "choice") {
    return firstChoice(kind.choices(), typed, locale)?.id ?? value ?? "";
  }
  if (typed !== undefined) {
    return typed;
  }
  if (value === null || value === undefined) {
    return "";
  }
  return kind.type === "decimal" || kind.type === "money" ? editableDecimal(value, locale) : value;
}
