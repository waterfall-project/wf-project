// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A period a list is filtered on, as the address carries it under the names of the contract —
 * `from` and `to` —, in one of the three forms the contract takes:
 *
 * - `date`: two days of the calendar, both included, as the contract writes a date of planning —
 *   the documents of the actual costs (`listActualCosts`);
 * - `day`: two instants, the start included and the end excluded, drawn from days of the calendar
 *   entered in the local time of the reader — the start of the first day, the start of the day
 *   after the last —, the last modification of the projects of the home (`listProjects`). An
 *   address of instants that are not the start of a local day — typed by hand, or shared from
 *   another time zone — shows the local day its start falls in, and the local day of the last
 *   moment before its end; a side left untouched is sent as the address names it, so that the
 *   period read is the one shared, and only a side entered anew is drawn from the days of the
 *   reader;
 * - `instant`: two instants entered to the minute in the local time of the reader, the start
 *   included and the end excluded — the journal of audit (`listAuditEvents`).
 *
 * The address holds what the contract takes, and the page sends it as it is; only the browser knows
 * its time zone, so that an instant becomes the text of a field, and a field an instant, in the
 * browser alone (`fieldOf`, `addressOf`). A period the server refuses — an end before the start,
 * the one rule of every period of the contract — names the start it was given (`params.minimum`),
 * which the field of the end says (`refusedPeriod`).
 *
 * Pure, and neither server nor client: the page reads, the filter writes.
 */
import type { components } from "@/api/generated/schema";
import { isPlanningDate } from "@/i18n/format";
import type { SearchParameters } from "@/navigation/context";

/** The form of a period: days of planning, local days drawn as instants, or instants. */
export type PeriodKind = "date" | "day" | "instant";

/** A side of a period, from its start. */
export type PeriodSide = "from" | "to";

/** The sides of a period, from its start. */
export const PERIOD_SIDES: readonly PeriodSide[] = ["from", "to"];

/** The parameters of a period, as the contract names them. */
export interface PeriodNames {
  readonly from: string;
  readonly to: string;
}

/** The names of the contract for a period: `from` and `to`. */
export const PERIOD: PeriodNames = { from: "from", to: "to" };

/** A period the address sets, as the contract takes it; none, no bound on that side. */
export interface Period {
  readonly from: string | undefined;
  readonly to: string | undefined;
}

/**
 * An instant as the contract writes it (`date-time` of RFC 3339): the date, the time, the zone —
 * each field caught to be bounded.
 */
const INSTANT =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?(?:Z|[+-](\d{2}):(\d{2}))$/;

/** The days of a month of a year, the last of February included in a leap year. */
function daysIn(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

/** The lowest value of each field of an instant after its year, from the month to the zone. */
const LOWEST = [1, 1, 0, 0, 0, 0, 0];

/**
 * Whether a text is an instant the contract takes: its form, and each field within its bounds —
 * a month of the year, a day of that month, an hour up to 23, minutes and seconds up to 59, a
 * zone of 23 hours and 59 minutes at most.
 */
export function isInstant(value: string): boolean {
  const fields = INSTANT.exec(value);
  if (fields === null) {
    return false;
  }
  // A field the text leaves out — the seconds, the zone of `Z` — is nought.
  const [year = 0, ...rest] = fields
    .slice(1)
    .map((field: string | undefined) => Number(field ?? 0));
  const highest = [12, daysIn(year, rest[0] ?? 0), 23, 59, 59, 23, 59];
  return rest.every((field, at) => field >= (LOWEST[at] ?? 0) && field <= (highest[at] ?? 0));
}

/** Whether a text is a bound the contract takes for a period of a form. */
export function isBound(kind: PeriodKind, value: string): boolean {
  return kind === "date" ? isPlanningDate(value) : isInstant(value);
}

/**
 * The period the address sets, each side as the contract takes it for the form of the period; a
 * value it would refuse — 30 February, an instant that is none — is not asked.
 */
export function readPeriod(
  search: SearchParameters,
  kind: PeriodKind,
  names: PeriodNames = PERIOD,
): Period {
  const bound = (name: string) => {
    const value = search.get(name);
    return value !== null && isBound(kind, value) ? value : undefined;
  };
  return { from: bound(names.from), to: bound(names.to) };
}

/**
 * The address of the same screen with another period — a side left empty lifted —, back to the
 * first page of a list the server pages, the rest of its query kept.
 */
export function periodHref(
  pathname: string,
  query: URLSearchParams,
  period: Period,
  options: { readonly names?: PeriodNames; readonly page?: string | undefined } = {},
): string {
  const names = options.names ?? PERIOD;
  const next = new URLSearchParams(query);
  if (options.page !== undefined) {
    next.delete(options.page);
  }
  for (const side of PERIOD_SIDES) {
    const value = period[side];
    if (value === undefined || value === "") {
      next.delete(names[side]);
    } else {
      next.set(names[side], value);
    }
  }
  const text = next.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}

/** Two digits. */
function twoDigits(value: number): string {
  return String(value).padStart(2, "0");
}

/** The local day of a moment, as a field of a date writes it: `2026-03-01`. */
function dayOf(at: Date): string {
  return `${String(at.getFullYear())}-${twoDigits(at.getMonth() + 1)}-${twoDigits(at.getDate())}`;
}

/** The day of the calendar an instant falls on in the local time of the workstation. */
export function localDay(instant: string): string {
  return dayOf(new Date(instant));
}

/** An instant as a field of local date and time writes it: `2026-06-03T10:30`. */
function localField(instant: string): string {
  const at = new Date(instant);
  return `${dayOf(at)}T${twoDigits(at.getHours())}:${twoDigits(at.getMinutes())}`;
}

/** The start of a local day, some days after it, as the contract writes an instant. */
function startOfDay(day: string, after: number): string | undefined {
  const [year, month, date] = day.split("-").map(Number);
  if (!isPlanningDate(day) || year === undefined || month === undefined || date === undefined) {
    return undefined;
  }
  return new Date(year, month - 1, date + after).toISOString();
}

/** A local date and time entered, as the contract takes an instant; none for a field emptied. */
function instantOfField(field: string): string | undefined {
  const at = new Date(field);
  return field === "" || Number.isNaN(at.getTime()) ? undefined : at.toISOString();
}

/**
 * The text the field of a side shows of a bound of the address, in the local time of the
 * workstation — which is why it runs in the browser for the instants: a day as it is; the local day
 * of the start, or of the last moment before the end, excluded; an instant to the minute.
 */
export function fieldOf(kind: PeriodKind, side: PeriodSide, value: string): string {
  switch (kind) {
    case "date":
      return value;
    case "day":
      return localDay(side === "from" ? value : new Date(Date.parse(value) - 1).toISOString());
    case "instant":
      return localField(value);
  }
}

/**
 * The bound of the contract a field of a side writes: a day as it is; the start of the local day
 * entered, or of the day after it for the end, excluded; an instant entered to the minute. None for
 * a field emptied.
 */
export function addressOf(kind: PeriodKind, side: PeriodSide, field: string): string | undefined {
  if (field === "") {
    return undefined;
  }
  switch (kind) {
    case "date":
      return isPlanningDate(field) ? field : undefined;
    case "day":
      return startOfDay(field, side === "from" ? 0 : 1);
    case "instant":
      return instantOfField(field);
  }
}

/** A refusal of the API, by field: what a refused side is read from. */
type FieldProblem = components["schemas"]["FieldProblem"];

/**
 * Why the API refused one side of a period (422): a bound it does not take (`DATE_INVALID`), or an
 * end before the start, which it names as it was given (`VALUE_OUT_OF_RANGE`, `params.minimum`).
 */
export type PeriodRefusal =
  | { readonly code: "DATE_INVALID" }
  | { readonly code: "VALUE_OUT_OF_RANGE"; readonly minimum: string };

/** The refusals of the two sides of a period, by side; none on a side the API accepted. */
export interface PeriodRefusals {
  readonly from?: PeriodRefusal;
  readonly to?: PeriodRefusal;
}

/**
 * The sides of a period the API refused (422, `VALIDATION_FAILED`), as the envelope points at each
 * (`/query/from`, `/query/to`); none when it points at neither. Any other field, or another code,
 * names no side.
 */
export function refusedPeriod(
  fields: readonly FieldProblem[],
  names: PeriodNames = PERIOD,
): PeriodRefusals | undefined {
  const refused: { from?: PeriodRefusal; to?: PeriodRefusal } = {};
  for (const { pointer, code, params } of fields) {
    const side = PERIOD_SIDES.find((each) => pointer === `/query/${names[each]}`);
    if (side === undefined) {
      continue;
    }
    const minimum = params?.minimum;
    if (code === "VALUE_OUT_OF_RANGE" && typeof minimum === "string") {
      refused[side] = { code, minimum };
    } else if (code === "DATE_INVALID") {
      refused[side] = { code };
    }
  }
  return refused.from === undefined && refused.to === undefined ? undefined : refused;
}
