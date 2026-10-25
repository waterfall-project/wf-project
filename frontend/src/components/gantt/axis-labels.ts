// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The labels of the axis of the Gantt (US-0530): which boundaries of each of its two rows its width
 * holds, and how each is written, in the language of the interface, in UTC — for its header, and
 * for its exported image (`gantt-image.ts`). Neither server nor client.
 */
import type { useTranslations } from "next-intl";

import { formatLocale } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

import { DAY, SCALE_LEVELS } from "./scale";

/** The messages of the Gantt. */
type GanttTranslations = ReturnType<typeof useTranslations<"gantt">>;

/** The fewest pixels between two labels of a row of the axis: the lower, the upper. */
const LABEL_SPACING = { lower: 22, upper: 72 } as const;

/** How each unit is written on each row, in the language of the interface. */
const FORMATS: Readonly<Record<string, Intl.DateTimeFormatOptions>> = {
  "upper:year": { year: "numeric" },
  "upper:month": { month: "long", year: "numeric" },
  "upper:week": { day: "numeric", month: "short", year: "numeric" },
  "upper:day": { weekday: "short", day: "numeric", month: "short" },
  "lower:month": { month: "short" },
};

/**
 * How a boundary of a row of the axis is written, in the language of the interface, in UTC: a
 * quarter by the catalogue, an hour of work by its number in its day, from 1.
 */
export function axisWriter(
  t: GanttTranslations,
  locale: Locale,
  view: { readonly level: number; readonly hoursPerDay: number | undefined },
): (which: "lower" | "upper", tick: number) => string {
  const scale = SCALE_LEVELS[view.level];
  return (which, tick) => {
    const unit = scale?.[which] ?? "day";
    const date = new Date(tick);
    if (unit === "quarter") {
      return t(which === "upper" ? "quarter" : "quarterShort", {
        quarter: Math.floor(date.getUTCMonth() / 3) + 1,
        year: date.getUTCFullYear(),
      });
    }
    if (unit === "hour") {
      const hour = Math.round(((tick % DAY) / DAY) * (view.hoursPerDay ?? 1)) + 1;
      return new Intl.NumberFormat(formatLocale(locale)).format(hour);
    }
    return new Intl.DateTimeFormat(formatLocale(locale), {
      ...(FORMATS[`${which}:${unit}`] ?? { day: "numeric" }),
      timeZone: "UTC",
    }).format(date);
  };
}

/**
 * The labels of a row of the axis its width holds, each at its boundary; a unit of the upper row
 * begun before the axis is written at its start, one of the lower row is not.
 */
export function labelsOf(
  ticks: readonly number[],
  width: number,
  row: "lower" | "upper",
  at: (time: number) => number,
): (readonly [number, number])[] {
  const kept: (readonly [number, number])[] = [];
  const shown = row === "upper" ? ticks : ticks.filter((tick) => at(tick) >= 0);
  for (const tick of shown.filter((boundary) => at(boundary) < 1)) {
    const x = Math.max(at(tick), 0) * width;
    const before = kept.at(-1)?.[1];
    if (before === undefined || x - before >= LABEL_SPACING[row]) {
      kept.push([tick, x]);
    }
  }
  return kept;
}
