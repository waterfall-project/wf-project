// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The mark of a cell whose value differs from the base of a comparison (WF-IHM-0150, US-2340): the
 * same for the three grids, a sign at the start of the cell — never the colour alone (WF-IHM-0070) —
 * and the value of the base, given on demand: in a tooltip while the pointer is over the cell or the
 * cell has the focus of the keyboard, and, for a reader of the screen, in the content of the cell
 * itself, after its value — the sign and that text carry the class that excludes them from a
 * selection (`select-none`), so that the browser's copy of a cell leaves them out. The grid compares
 * nothing: it marks the cell the server names (`ComparedNodeRead.base`) and shows the value the
 * server gives (WF-ARC-0020).
 *
 * The cell is the target of the pointer and of the keyboard, not the mark: the mark follows the
 * cell it is in, by its events. Its tooltip, a Radix root, mounts while it is shown alone: a
 * comparison marks cells by the hundred, and a root in each would cost the hydration of the screen.
 */
"use client";

import { useTranslations } from "next-intl";
import { type ReactNode, useEffect, useRef, useState } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

/** The sign of a cell that differs: the Greek capital of a difference. */
const SIGN = "Δ";

/** The content of a cell marked: the mark at its start, the value of the cell at its end. */
const MARKED = "flex w-full min-w-0 items-center justify-between gap-1";

/** The events of the cell that show the base, and those that hide it. */
const SHOWING = ["pointerenter", "focusin"] as const;
const HIDING = ["pointerleave", "focusout"] as const;

/**
 * Whether the cell the mark is in is shown the pointer or the focus: it listens to the cell, which
 * is the one the keyboard and the pointer reach, never to the mark.
 */
function useCellShown(mark: { readonly current: HTMLElement | null }) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const cell = mark.current?.closest("td");
    if (cell === null || cell === undefined) {
      return undefined;
    }
    const show = () => {
      setShown(true);
    };
    const hide = () => {
      setShown(false);
    };
    SHOWING.forEach((name) => {
      cell.addEventListener(name, show);
    });
    HIDING.forEach((name) => {
      cell.addEventListener(name, hide);
    });
    return () => {
      SHOWING.forEach((name) => {
        cell.removeEventListener(name, show);
      });
      HIDING.forEach((name) => {
        cell.removeEventListener(name, hide);
      });
    };
  }, [mark]);
  return [shown, setShown] as const;
}

/**
 * The content of a cell whose value differs from the base, with the mark of it: `base` is the value
 * the base carried, as the cell would have shown it.
 */
export function BaseMark({
  base,
  children,
}: {
  readonly base: ReactNode;
  readonly children: ReactNode;
}) {
  const t = useTranslations("grid.compared");
  const mark = useRef<HTMLSpanElement>(null);
  // The tooltip shown is dismissed by Escape (WCAG 1.4.13) until the cell is left and reached again.
  const [open, setOpen] = useCellShown(mark);
  const sign = (
    <span aria-hidden="true" className="shrink-0 font-bold text-foreground select-none">
      {SIGN}
    </span>
  );
  return (
    <span className={MARKED}>
      <span ref={mark} className="inline-flex shrink-0">
        {open ? (
          <Tooltip
            open
            onOpenChange={(next) => {
              setOpen(next);
            }}
          >
            <TooltipTrigger asChild>{sign}</TooltipTrigger>
            <TooltipContent>
              {t("base")} {base}
            </TooltipContent>
          </Tooltip>
        ) : (
          sign
        )}
      </span>
      <span className="min-w-0 truncate">{children}</span>
      <span className="sr-only select-none">
        {t("base")} {base}
      </span>
    </span>
  );
}
