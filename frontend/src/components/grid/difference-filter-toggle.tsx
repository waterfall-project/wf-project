// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The button « Écarts seulement » above the grid of a differential and the grid of the comparison
 * of two revisions (US-0700): pressed when the address retains every difference, it writes
 * `difference` in the address — the three values of the contract — or lifts it, and the page reads
 * anew, which the server filters (`difference-filter.ts`). A press goes on from the address last
 * asked (`usePendingAddress`), and shows until the server answers for it (défaut n° 21 de
 * `typescript.md`).
 *
 * Every prop is data — the text is given translated —, never a function: a server component hands
 * it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { Circle, CircleCheck } from "lucide-react";
import { usePathname } from "next/navigation";
import { useOptimistic, useTransition } from "react";

import { Button } from "@/components/ui/button";

import { differencesOnlyHref } from "./difference-filter";
import { usePendingAddress } from "./pending-address";

/** Render the button that retains the differences alone, pressed when the address does. */
export function DifferenceFilterToggle({
  label,
  pressed,
}: {
  /** What the button says: « Écarts seulement ». */
  readonly label: string;
  /** Whether the address retains every difference. */
  readonly pressed: boolean;
}) {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const [shown, show] = useOptimistic(pressed);
  const [, startTransition] = useTransition();
  const Icon = shown ? CircleCheck : Circle;
  return (
    <div className="flex items-center">
      <Button
        size="sm"
        variant={shown ? "default" : "outline"}
        aria-pressed={shown}
        onClick={() => {
          startTransition(() => {
            show(!shown);
            request((query) => differencesOnlyHref(pathname, query, !shown));
          });
        }}
      >
        <Icon aria-hidden="true" className="size-4" />
        {label}
      </Button>
    </div>
  );
}
