// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The mark of a difference in a dense grid (US-0500, WF-IHM-0100): a structure read as a diff
 * against another bears on each node the difference the server marks (`Node.difference`) — `+` for
 * a node added, `-` for one removed, shown at the place it had, `M` for one modified, a summary whose
 * content changes included. The character says it, in a column at the start of the grid; the colour
 * doubles it — the mark in a green, a red or a yellow, and the row tinted of the same —, never alone,
 * and the word of the difference is read by who does not see either. A node unchanged bears nothing.
 * The tints and the marks are tokens of the charter, with their dark values, measured in both modes.
 */
"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/components/ui/utils";

import type { RowDifference } from "./columns";

/** The difference a row bears, but the one that bears no mark. */
type Marked = Exclude<RowDifference, "unchanged">;

/**
 * What marks each difference: its character, the colour of the character, and the tint of the cells of
 * the row — all of them but those the server computes, which keep their own shade.
 */
const MARKS: Readonly<Record<Marked, { mark: string; text: string; row: string }>> = {
  added: {
    mark: "+",
    text: "text-diff-added-mark",
    row: "[&>td:not([aria-haspopup=dialog])]:bg-diff-added",
  },
  removed: {
    mark: "-",
    text: "text-diff-removed-mark",
    row: "[&>td:not([aria-haspopup=dialog])]:bg-diff-removed",
  },
  modified: {
    mark: "M",
    text: "text-diff-modified-mark",
    row: "[&>td:not([aria-haspopup=dialog])]:bg-diff-modified",
  },
};

/** The difference a row bears that is marked: none for a row unchanged, or with no difference. */
function markedOf(difference: RowDifference | null | undefined): Marked | undefined {
  return difference === null || difference === undefined || difference === "unchanged"
    ? undefined
    : difference;
}

/** The classes that tint the cells of a row of a difference; none for a row that bears none. */
export function differenceTint(difference: RowDifference | null | undefined): string | null {
  const marked = markedOf(difference);
  return marked === undefined ? null : MARKS[marked].row;
}

/** The mark of a difference: its character, and the word that names it to a reader of the screen. */
export function DiffMark({
  difference,
}: {
  readonly difference: RowDifference | null | undefined;
}) {
  const t = useTranslations("enums.NodeDifference");
  const marked = markedOf(difference);
  if (marked === undefined) {
    return null;
  }
  const { mark, text } = MARKS[marked];
  return (
    <>
      <span aria-hidden="true" className={cn("font-bold", text)}>
        {mark}
      </span>
      <span className="sr-only">{t(marked)}</span>
    </>
  );
}
