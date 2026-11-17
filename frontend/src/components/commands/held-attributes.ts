// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The attributes of a button of a write that may wait for the screen to be read anew (US-2240,
 * `useReadAnew`): busy while it sends (`pending`) or while the screen is read (`holding`), and
 * `aria-disabled` — a press runs nothing — as long as the screen is read, never merely while it
 * sends, which the form says by its own guard.
 */

/** The attributes of a button that sends, or that holds for the screen read anew. */
export function heldAttributes(
  pending: boolean,
  holding: boolean,
): {
  readonly "aria-busy": boolean;
  readonly "aria-disabled"?: true;
} {
  return holding ? { "aria-busy": true, "aria-disabled": true } : { "aria-busy": pending };
}
