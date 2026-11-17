// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a button says while what it started has not answered (WF-IHM-0080, #3103), the same way for
 * every command: a request — a slow write done within it, the opening of a revision, included —, or
 * a background task, until it ends. It is inert — `aria-disabled`, and a second press runs nothing,
 * which the command that reads `waiting` holds —, `aria-busy`, and a wheel takes the place of its
 * icon, beside its label, which stays: the button keeps its name. The wheel turns, a state the
 * button tells and that stops with the answer; it stands still when the workstation asks for less
 * motion, as the pulse of the loading skeleton does (guide, « Charte graphique »). A failure gives
 * the button back: the same treatment can be run again. A button mounted anew while its task runs —
 * the tab reloaded, the screen left and come back to — waits the same way: it finds the task by what
 * it aims at (`taskAim`, `useRunningTask`, #3404), in the tab that started it only.
 */
import { LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

/** The attributes of a button that waits, or of one that does not: `aria-busy` said either way. */
export function waitingAttributes(waiting: boolean): {
  readonly "aria-busy": boolean;
  readonly "aria-disabled"?: true;
} {
  return waiting ? { "aria-busy": true, "aria-disabled": true } : { "aria-busy": false };
}

/** The icon of a button, or the wheel in its place while it waits. */
export function WaitingIcon({
  waiting,
  icon,
}: {
  readonly waiting: boolean;
  /** The icon of the button, hidden from a screen reader. */
  readonly icon: ReactNode;
}) {
  return waiting ? (
    <LoaderCircle
      aria-hidden="true"
      data-waiting=""
      className="animate-spin motion-reduce:animate-none"
    />
  ) : (
    icon
  );
}
