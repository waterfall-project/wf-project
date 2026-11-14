// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The time zone of the installation, handed down to every component that proposes the current
 * day (WF-PLA-0130, WF-DAT-0100): the layout reads it once per request
 * (`src/installation/request.ts`), the provider makes it available to the client components
 * below, and `useToday` gives them the day in it. Without a value — the API out of reach — the
 * day is that of universal time, which the contract gives an installation that has no zone
 * kept: never the one of the workstation.
 */
"use client";

import { createContext, type ReactNode, useContext } from "react";

import { today } from "@/components/remaining/address";

const FALLBACK_ZONE = "UTC";

const TimeZoneContext = createContext<string | undefined>(undefined);

/** Make the time zone of the installation available to the components below. */
export function TimeZoneProvider({
  timeZone,
  children,
}: {
  readonly timeZone: string | undefined;
  readonly children: ReactNode;
}) {
  return <TimeZoneContext value={timeZone}>{children}</TimeZoneContext>;
}

/** The IANA name of the time zone of the installation, universal time when it is unknown. */
export function useInstallationTimeZone(): string {
  return useContext(TimeZoneContext) ?? FALLBACK_ZONE;
}

/** A function that gives the current day in the time zone of the installation, as `2026-03-01`. */
export function useToday(): () => string {
  const timeZone = useInstallationTimeZone();
  return () => today(timeZone);
}
