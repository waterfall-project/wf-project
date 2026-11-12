// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the chips of the filters of a flat table are made of (WF-IHM-0130, #2916): the words that
 * tell a period, the bounds of a column of figures, a list of values, in the language and the time
 * of the workstation. A screen builds its chips from its address with a kit (`useChipKit`), in the
 * order of its panel, and hands them to its grid (`filtering`, `filter-chips.ts`).
 *
 * A period of local days or instants is told in the time zone of the workstation, which only the
 * browser knows: before the hydration its days are told `…`, a name the user does not read for
 * long (`useHydrated`). A period of planning days is told as it is.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";

import { useCurrency } from "@/currency/context";
import { useHydrated } from "@/components/use-hydrated";
import {
  formatBytes,
  formatDecimal,
  formatMoney,
  formatPlanningDate,
  isPlanningDate,
} from "@/i18n/format";

import type { FilterChip } from "./filter-chips";
import { type Bounds, bounded, boundNames, type FigureKind } from "./filters";
import { fieldOf, PERIOD, type Period, type PeriodKind, type PeriodNames } from "./period";

/** What a day of a period is told as before the browser knows its time zone. */
export const PENDING_DAY = "…";

/** What a screen builds its chips with: each call adds one, in the order of the panel. */
export interface ChipKit {
  /** The chips added so far. */
  readonly chips: FilterChip[];
  /** A chip told in full. */
  readonly add: (key: string, name: string, value: string, params: readonly string[]) => void;
  /** A list of values chosen, told by their texts; nothing for an empty list. */
  readonly values: (
    key: string,
    name: string,
    texts: readonly string[],
    params?: readonly string[],
  ) => void;
  /** A period, nothing when neither side is set. */
  readonly period: (
    key: string,
    name: string,
    kind: PeriodKind,
    period: Period,
    names?: PeriodNames,
  ) => void;
  /** The bounds of a column of figures, nothing when neither side is set. */
  readonly bounds: (
    column: string,
    name: string,
    kind: FigureKind,
    bounds: Bounds,
    key?: string,
  ) => void;
}

/** The kit of a screen: its chips are built by calling it, in the order of its panel. */
export function useChipKit(): ChipKit {
  const t = useTranslations("grid.filtering");
  const locale = useLocale();
  const currency = useCurrency();
  const hydrated = useHydrated();
  const chips: FilterChip[] = [];
  const add: ChipKit["add"] = (key, name, value, params) => {
    chips.push({ key, name, value, params });
  };
  const day = (kind: PeriodKind, side: "from" | "to", bound: string) => {
    // No local day before the browser: the local day of an instant is not the server's.
    if (kind !== "date" && !hydrated) {
      return PENDING_DAY;
    }
    const field = fieldOf(kind, side, bound);
    return isPlanningDate(field) ? formatPlanningDate(field, locale) : field;
  };
  const figure = (kind: FigureKind, value: string) => {
    switch (kind) {
      case "bytes":
        return formatBytes(Number(value), locale);
      case "money":
        return formatMoney(value, locale, currency);
      default:
        return formatDecimal(value, locale);
    }
  };
  return {
    chips,
    add,
    values: (key, name, texts, params = [key]) => {
      if (texts.length > 0) {
        add(key, name, texts.join(", "), params);
      }
    },
    period: (key, name, kind, period, names = PERIOD) => {
      const { from, to } = period;
      let told: string | undefined;
      if (from !== undefined && to !== undefined) {
        told = t("between", { from: day(kind, "from", from), to: day(kind, "to", to) });
      } else if (from !== undefined) {
        told = t("since", { from: day(kind, "from", from) });
      } else if (to !== undefined) {
        told = t("until", { to: day(kind, "to", to) });
      }
      if (told !== undefined) {
        add(key, name, told, [names.from, names.to]);
      }
    },
    bounds: (column, name, kind, bounds, key = `${column}-bounds`) => {
      if (!bounded(bounds)) {
        return;
      }
      const { min, max } = bounds;
      let told: string;
      if (min !== undefined && max !== undefined) {
        told = t("boundsBetween", { min: figure(kind, min), max: figure(kind, max) });
      } else if (min !== undefined) {
        told = t("atLeast", { min: figure(kind, min) });
      } else {
        told = t("atMost", { max: figure(kind, max ?? "") });
      }
      const names = boundNames(column);
      add(key, name, told, [names.min, names.max]);
    },
  };
}
