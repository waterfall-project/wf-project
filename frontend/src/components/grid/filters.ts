// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of a list on the values of a column, as the address carries them, besides the sort
 * and the search of its grid (`query.ts`): a list of values of the contract — the origins of the
 * accounts, the capacities of the contributors —, written in one parameter, its values separated by
 * commas, as the contract declares every list (`explode: false`); and the bounds of a column of
 * figures, `<column>_min` and `<column>_max`, both included, as the contract names them for every
 * list (#545, `docs/api/DECISIONS.md`) — a period, `from` and `to`, is in `period.ts`. A
 * boolean column — the actual costs of the sub-projects, the state of an account — is filtered by
 * `true` or `false`, none retaining every row. A filter chosen only changes the
 * address, and the page reads anew: the server filters, never the front (WF-ARC-0020). A list the
 * server pages starts again from its first page, the place of a row in the list shown meaning
 * nothing in the one filtered otherwise.
 *
 * Pure, and neither server nor client: the page reads, the filter writes.
 */
import type { components } from "@/api/generated/schema";
import type { SearchParameters } from "@/navigation/context";

/**
 * The values a parameter of the address filters a list on, in the order of the contract given,
 * each once; none when it names none — every value, the server reading no filter. A value the
 * contract does not know is not asked: the API would refuse it.
 */
export function readValues<Value extends string>(
  search: SearchParameters,
  name: string,
  values: readonly Value[],
): readonly Value[] {
  const asked = new Set((search.get(name) ?? "").split(","));
  return values.filter((value) => asked.has(value));
}

/**
 * The address of the same screen with one filter set — or lifted, for none or an empty value —, the
 * rest of its query kept, and back to the first page of each list the server pages that it reads
 * (`pages`, the parameter of its page, or of the pages of the lists of a screen).
 */
export function filterHref(
  pathname: string,
  query: URLSearchParams,
  name: string,
  value: string | undefined,
  pages: string | readonly string[] = [],
): string {
  const next = new URLSearchParams(query);
  for (const page of typeof pages === "string" ? [pages] : pages) {
    next.delete(page);
  }
  if (value === undefined || value === "") {
    next.delete(name);
  } else {
    next.set(name, value);
  }
  const text = next.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}

/** A filter of a list on the values of a column, as the address writes it. */
export interface ValuesAddress<Value extends string> {
  /** The parameter of the address, as the contract names it. */
  readonly name: string;
  /** The values of the contract, in its order. */
  readonly values: readonly Value[];
  /** The parameter of the page of a list the server pages, which a filter takes back to its first. */
  readonly page?: string | undefined;
  /**
   * Whether every row holds one of the values, every one chosen then retaining every row: the
   * filter is lifted. Not so of the zones of the indices, which a project without an index is in
   * none of: every zone chosen still filters.
   */
  readonly exhaustive?: boolean | undefined;
}

/**
 * The address of the same screen filtered on other values of a column — none lifts the filter, and
 * every one too when every row holds one (`exhaustive`) —, written in the order of the contract,
 * back to the first page of a list the server pages.
 */
export function valuesHref<Value extends string>(
  pathname: string,
  query: URLSearchParams,
  filter: ValuesAddress<Value>,
  chosen: readonly Value[],
): string {
  const kept = filter.values.filter((value) => chosen.includes(value));
  const every = filter.exhaustive !== false && kept.length === filter.values.length;
  return filterHref(pathname, query, filter.name, every ? undefined : kept.join(","), filter.page);
}

/**
 * A figure of the contract a bound takes: an exact decimal, an amount of two decimals at most, a
 * depth of a tree, a whole number from 1, a count, a whole number from 0 — the holders of a role —,
 * or a size in bytes, a whole number from 0 of more digits than a count — a backup weighs gigabytes.
 */
export type FigureKind = "decimal" | "money" | "level" | "count" | "bytes";

/** The pattern of the contract of each kind of bound: `Decimal`, `Money`, a depth, a count, a size. */
export const FIGURES: Readonly<Record<FigureKind, RegExp>> = {
  decimal: /^-?\d+(\.\d+)?$/,
  money: /^-?\d+(\.\d{1,2})?$/,
  level: /^[1-9]\d{0,2}$/,
  count: /^(0|[1-9]\d{0,8})$/,
  bytes: /^(0|[1-9]\d{0,14})$/,
};

/** The two bounds of a column the address carries; none, no bound on that side. */
export interface Bounds {
  readonly min: string | undefined;
  readonly max: string | undefined;
}

/** The parameters that bound a column, as the contract names them after its column (#545). */
export function boundNames(column: string): { readonly min: string; readonly max: string } {
  return { min: `${column}_min`, max: `${column}_max` };
}

/**
 * The bounds the address sets on a column, each a figure of the contract; a value it would refuse —
 * not a figure of its kind — is not asked, as an unknown value is not.
 */
export function readBounds(search: SearchParameters, column: string, kind: FigureKind): Bounds {
  const names = boundNames(column);
  const figure = (name: string) => {
    const value = search.get(name);
    return value !== null && FIGURES[kind].test(value) ? value : undefined;
  };
  return { min: figure(names.min), max: figure(names.max) };
}

/** Whether the address bounds a column on either side. */
export function bounded(bounds: Bounds): boolean {
  return bounds.min !== undefined || bounds.max !== undefined;
}

/** The bounds of one column a filter writes, by the column as the address names it. */
export interface ColumnBounds {
  readonly column: string;
  readonly bounds: Bounds;
}

/**
 * The address of the same screen with the bounds of some columns set — a side left empty lifted —
 * and, when given, another parameter they go with (the year whose rate is bounded), set while a
 * bound is and lifted with the last; back to the first page of a list the server pages.
 */
export function boundsHref(
  pathname: string,
  query: URLSearchParams,
  columns: readonly ColumnBounds[],
  options: {
    readonly scope?: { readonly name: string; readonly value: string } | undefined;
    readonly page?: string | undefined;
  } = {},
): string {
  const next = new URLSearchParams(query);
  if (options.page !== undefined) {
    next.delete(options.page);
  }
  for (const { column, bounds } of columns) {
    const names = boundNames(column);
    for (const side of ["min", "max"] as const) {
      const value = bounds[side];
      if (value === undefined) {
        next.delete(names[side]);
      } else {
        next.set(names[side], value);
      }
    }
  }
  if (options.scope !== undefined) {
    if (columns.some(({ bounds }) => bounded(bounds))) {
      next.set(options.scope.name, options.scope.value);
    } else {
      next.delete(options.scope.name);
    }
  }
  const text = next.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}

/** A refusal of the API, by field: what a refused bound is read from. */
type FieldProblem = components["schemas"]["FieldProblem"];

/**
 * Why the API refused one parameter of the bounds of a list (#545): a bound that is no number of
 * its type (`NUMBER_INVALID`); an upper bound below the lower one, which it names
 * (`VALUE_OUT_OF_RANGE`, `params.minimum`, written as the contract writes a decimal, or a number
 * for a count); the choice a bound goes with, missing (`VALUE_REQUIRED`, the year of the rate).
 */
export type BoundRefusal =
  | { readonly code: "NUMBER_INVALID" | "VALUE_REQUIRED" }
  | { readonly code: "VALUE_OUT_OF_RANGE"; readonly minimum: string };

/** The refusals of the parameters of a query, by the name of the parameter in the contract. */
export type RefusedBounds = ReadonlyMap<string, BoundRefusal>;

/**
 * The parameters of a query the API refused (422, `VALIDATION_FAILED`), by their name in the
 * contract, as the envelope points at each (`/query/<name>`): the bounds and the choice they go
 * with, by their codes. Any other field, or another code, names no bound.
 */
export function refusedBounds(fields: readonly FieldProblem[]): RefusedBounds {
  const refused = new Map<string, BoundRefusal>();
  for (const { pointer, code, params } of fields) {
    const name = /^\/query\/(\w+)$/.exec(pointer)?.[1];
    if (name === undefined) {
      continue;
    }
    // The lower bound named as the contract types its column: a decimal written, a count a number.
    const minimum = typeof params?.minimum === "number" ? String(params.minimum) : params?.minimum;
    if (code === "VALUE_OUT_OF_RANGE" && typeof minimum === "string") {
      refused.set(name, { code, minimum });
    } else if (code === "NUMBER_INVALID" || code === "VALUE_REQUIRED") {
      refused.set(name, { code });
    }
  }
  return refused;
}

/** The refusals of the two bounds of a column of the contract; none on a side the API accepted. */
export function refusedSides(
  refused: RefusedBounds | undefined,
  column: string,
): { readonly min?: BoundRefusal; readonly max?: BoundRefusal } | undefined {
  const names = boundNames(column);
  const min = refused?.get(names.min);
  const max = refused?.get(names.max);
  return min === undefined && max === undefined
    ? undefined
    : { ...(min === undefined ? {} : { min }), ...(max === undefined ? {} : { max }) };
}

/**
 * The value a parameter of the address filters a boolean column on: `true` or `false`; none for
 * any other value — every row, the server reading no filter.
 */
export function readBoolean(search: SearchParameters, name: string): boolean | undefined {
  const value = search.get(name);
  return value === "true" ? true : value === "false" ? false : undefined;
}
