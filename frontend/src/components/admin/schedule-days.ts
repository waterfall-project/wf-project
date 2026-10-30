// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The days of a weekly schedule, shared by the forms of the schedules of the backups and of the
 * reading of the accounts: a module without a directive, which both sides import.
 */

/** The days of a weekly schedule, from 1, Monday, as the contract numbers them (ISO 8601). */
export const WEEKDAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const;

/**
 * The first day from the one given, by the universal calendar, that falls on a day of the week
 * numbered as the contract does (1, Monday, to 7, Sunday): where a weekly time is taken this week.
 */
export function nextWeekday(from: Date, weekday: number): Date {
  const today = from.getUTCDay() === 0 ? 7 : from.getUTCDay();
  return new Date(from.getTime() + ((weekday - today + 7) % 7) * 86_400_000);
}
