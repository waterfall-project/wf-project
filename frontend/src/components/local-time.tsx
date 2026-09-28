// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * An instant of the API — a `Timestamp`: a date of calculation, an audit column — shown in
 * the local time of the workstation. Only the browser knows its time zone: the server renders
 * the machine-readable instant alone, and the browser writes it in its own time.
 */
"use client";

import { useLocale } from "next-intl";
import { useSyncExternalStore } from "react";

import type { components } from "@/api/generated/schema";
import { formatTimestamp } from "@/i18n/format";

/** The instant to show. */
export interface LocalTimeProps {
  readonly value: components["schemas"]["Timestamp"];
}

// The time zone of a workstation does not change under a page: nothing to subscribe to.
const unchanging = () => () => undefined;

/** Show an instant in the language of the interface and the time zone of the workstation. */
export function LocalTime({ value }: LocalTimeProps) {
  const locale = useLocale();
  const text = useSyncExternalStore(
    unchanging,
    () => formatTimestamp(value, locale),
    () => "",
  );
  return <time dateTime={value}>{text}</time>;
}
