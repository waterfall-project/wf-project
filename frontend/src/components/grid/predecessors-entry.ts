// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The entry of the column of the predecessors, as Microsoft Project takes it (WF-PLA-0030,
 * WF-PLA-0160): the links of a task separated by a semicolon, each the row number of its
 * predecessor, the code of the type of the link in the language of the interface — « FD », « DD »,
 * « FF », « DF » in French, « FS », « SS », « FF », « SF » in English; none for finish to start —,
 * and its lag, positive or negative — a lead —, in the unit of a duration or as a percentage of the
 * duration of the predecessor: `3FD+2 j ; 5DD`, `4-50%`. The lag is read by `parseDuration`, whose
 * suffixes it shares (WF-PLA-0160), and kept in its unit, never converted.
 *
 * A row number is resolved to the task it names by the grid, which knows the rows it read: a number
 * it does not know is not entered (`unknownRow`). The value validated is neutral of language —
 * each link by its row, its task, its type and its lag in the contract's terms — and goes back to
 * text by the same names (`predecessorsText`). Never through a float (WF-DAT-0100).
 */
import type { components } from "@/api/generated/schema";
import { formatDecimal, parseDecimal } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

import { durationOf, parseDuration } from "./cell-values";

/** The type of a link (WF-PLA-0030). */
export type LinkType = components["schemas"]["LinkType"];

/** The unit of a lag: those of a duration, and the percentage of the predecessor (WF-PLA-0030). */
export type LagUnit = components["schemas"]["LagUnit"];

/** A link to a predecessor as the grid reads it, its row number with it. */
export type PredecessorLink = components["schemas"]["Predecessor"];

/** A link as the contract writes it, which `setPredecessors` takes. */
export type PredecessorWrite = components["schemas"]["PredecessorWrite"];

/** Why the text of the predecessors is not validated: no link of the form, no row of that number. */
export type PredecessorsProblem = "notPredecessors" | "unknownRow";

/**
 * What the column names in the language of the interface, and knows of the grid: the code of each
 * type of link, the suffix of each unit of a lag, and the task a row number names.
 */
export interface PredecessorNames {
  readonly code: (link: LinkType) => string;
  readonly suffix: (unit: LagUnit) => string;
  /** The identifier of the task of a row number the grid read; none for a number it did not. */
  readonly resolve: (row: number) => string | undefined;
}

/** Every type of link, in the order of the contract: one it adds fails the type check here. */
const LINK_TYPES = {
  finish_to_start: true,
  start_to_start: true,
  finish_to_finish: true,
  start_to_finish: true,
} as const satisfies Record<LinkType, true>;

/** Whether a text is a type of link of the contract. */
function isLinkType(text: string): text is LinkType {
  return Object.hasOwn(LINK_TYPES, text);
}

/** Every type of link, in the order of the contract. */
const LINKS: readonly LinkType[] = Object.keys(LINK_TYPES).filter(isLinkType);

/** Every unit of a lag, in the order of the contract: one it adds fails the type check here. */
const LAG_UNITS = {
  min: true,
  h: true,
  d: true,
  w: true,
  mo: true,
  emin: true,
  eh: true,
  ed: true,
  ew: true,
  emo: true,
  percent: true,
} as const satisfies Record<LagUnit, true>;

/** Whether a text is a unit of a lag of the contract. */
function isLagUnit(text: string): text is LagUnit {
  return Object.hasOwn(LAG_UNITS, text);
}

/** A decimal of the contract that reads as zero: `0`, `-0`, `0.00`. */
const ZERO = /^-?0+(\.0+)?$/;

/** The separator of the links, in the text of an entry and in the value validated. */
const SEPARATOR = ";";

/** The separator of the parts of a link in the value validated, which no part holds. */
const PART = "|";

/** A link: its row number, its code, then its lag with its sign — the three parts typed. */
const LINK = /^(\d{1,9})\s*([^+\-\d]*?)\s*(?:([+-])\s*(.+))?$/u;

/** A share of the predecessor typed, never negative: the sign is read apart. */
function shareOf(text: string, locale: Locale): PredecessorWrite["lag"] | undefined {
  const value = parseDecimal(text, locale);
  return value === undefined || value.startsWith("-") ? undefined : { value, unit: "percent" };
}

/**
 * The lag typed after its sign: a share of the duration of the predecessor (« 50 % »), or a
 * duration with the suffix of its unit, a number alone in days. None for what is neither.
 */
function lagOf(
  text: string,
  negative: boolean,
  locale: Locale,
  suffix: (unit: LagUnit) => string,
): PredecessorWrite["lag"] | undefined {
  const share = /^(.*?)\s*%$/u.exec(text);
  const duration = parseDuration(text, locale, suffix);
  const typed = share === null ? durationOf(duration ?? "") : shareOf(share[1] ?? "", locale);
  if (typed === undefined) {
    return undefined;
  }
  return {
    value: negative && !ZERO.test(typed.value) ? `-${typed.value}` : typed.value,
    unit: typed.unit,
  };
}

/** A link typed, or why it is not one. */
function linkOf(
  text: string,
  locale: Locale,
  names: PredecessorNames,
): PredecessorLink | PredecessorsProblem {
  const typed = LINK.exec(text);
  if (typed === null) {
    return "notPredecessors";
  }
  const [, number = "", code = "", sign, rest] = typed;
  const written = code.toLocaleLowerCase(locale);
  const type =
    code === ""
      ? "finish_to_start"
      : LINKS.find((each) => names.code(each).toLocaleLowerCase(locale) === written);
  const lag =
    rest === undefined
      ? ({ value: "0", unit: "d" } as const)
      : lagOf(rest, sign === "-", locale, names.suffix);
  if (type === undefined || lag === undefined) {
    return "notPredecessors";
  }
  const row = Number(number);
  const task = names.resolve(row);
  return task === undefined
    ? "unknownRow"
    : { predecessor_node_id: task, predecessor_row_number: row, link_type: type, lag };
}

/** A link as the value validated holds it. */
function valueOfLink(link: PredecessorLink): string {
  const { predecessor_row_number: row, predecessor_node_id: task, link_type: type, lag } = link;
  return [row.toString(), task, type, lag.value, lag.unit].join(PART);
}

/** The value an entry validates, from the links it holds; none for no link. */
export function predecessorsValue(
  links: readonly PredecessorLink[] | undefined,
): string | undefined {
  return links === undefined || links.length === 0
    ? undefined
    : links.map(valueOfLink).join(SEPARATOR);
}

/**
 * The links a value validated holds, as the grid reads them; none for a value that is not one,
 * which no entry makes.
 */
export function predecessorsOf(value: string): PredecessorLink[] | undefined {
  const links: PredecessorLink[] = [];
  for (const part of value.split(SEPARATOR)) {
    const [row = "", task = "", type = "", lag = "", unit = "", ...rest] = part.split(PART);
    if (
      rest.length > 0 ||
      task === "" ||
      !isLinkType(type) ||
      !isLagUnit(unit) ||
      !/^\d+$/.test(row)
    ) {
      return undefined;
    }
    links.push({
      predecessor_node_id: task,
      predecessor_row_number: Number(row),
      link_type: type,
      lag: { value: lag, unit },
    });
  }
  return links;
}

/** The links to send of those an entry validated: the contract's, without the row number. */
export function predecessorsWritten(links: readonly PredecessorLink[]): PredecessorWrite[] {
  return links.map(({ predecessor_node_id, link_type, lag }) => ({
    predecessor_node_id,
    link_type,
    lag,
  }));
}

/**
 * The links typed, as the value an entry validates — `null` for a text without any link, which
 * empties the predecessors —, or why the text is not one.
 */
export function parsePredecessors(
  text: string,
  locale: Locale,
  names: PredecessorNames,
): { readonly value: string | null } | { readonly problem: PredecessorsProblem } {
  const links: PredecessorLink[] = [];
  for (const segment of text.split(SEPARATOR).map((each) => each.trim())) {
    if (segment === "") {
      continue;
    }
    const link = linkOf(segment, locale, names);
    if (typeof link === "string") {
      return { problem: link };
    }
    links.push(link);
  }
  return { value: predecessorsValue(links) ?? null };
}

/** A lag written as it is typed: its sign, its value in the language, its unit. */
function lagText(
  lag: PredecessorWrite["lag"],
  locale: Locale,
  suffix: (unit: LagUnit) => string,
): string {
  const sign = lag.value.startsWith("-") ? "-" : "+";
  const value = formatDecimal(lag.value.replace(/^-/, ""), locale);
  return `${sign}${value} ${suffix(lag.unit)}`;
}

/**
 * The links of a value validated as they are typed, in the language: the code of the type unless
 * the link is a plain finish to start, the lag unless it is zero. What the entry starts from, and
 * what the cell shows until the server answers.
 */
export function predecessorsText(value: string, locale: Locale, names: PredecessorNames): string {
  return (predecessorsOf(value) ?? [])
    .map(({ predecessor_row_number: row, link_type: type, lag }) => {
      const plain = ZERO.test(lag.value);
      const code = type === "finish_to_start" && plain ? "" : names.code(type);
      return `${row.toString()}${code}${plain ? "" : lagText(lag, locale, names.suffix)}`;
    })
    .join(`${SEPARATOR} `);
}
