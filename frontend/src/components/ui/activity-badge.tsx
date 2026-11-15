// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The state of an object of a list, active or deactivated (US-2070, #3079, #3249). « Actif » is
 * said by a dot and its word: the dot in the token of its own, `active-mark` — not a token of a
 * zone, which only `Signal` names. « Désactivé » keeps its mark, an outlined badge and the circle
 * struck through. The two differ by their shape and their word, never by their colour alone, so
 * that a grey copy of the screen still tells them apart (WF-IHM-0070).
 *
 * The word is the caller's, from its catalogue: this piece writes no text.
 */
import { CircleOff } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "./badge";

/** Render the state of an object, `active` or not, with its word (`children`). */
export function ActivityBadge({
  active,
  children,
}: {
  readonly active: boolean;
  /** The word of the state, translated. */
  readonly children: ReactNode;
}) {
  return active ? (
    <span data-slot="activity" className="inline-flex items-center gap-1.5">
      <span aria-hidden="true" className="size-2 shrink-0 rounded-full bg-active-mark" />
      {children}
    </span>
  ) : (
    <Badge data-slot="activity" variant="outline">
      <CircleOff aria-hidden="true" />
      {children}
    </Badge>
  );
}
