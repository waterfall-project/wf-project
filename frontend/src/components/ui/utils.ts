// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The helper the components of shadcn/ui share: classes joined, and the conflicting
 * utilities of Tailwind settled in favour of the last one, so that a caller's class
 * overrides a component's.
 */
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Join classes, the last utility of Tailwind winning over an earlier one it conflicts with. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
