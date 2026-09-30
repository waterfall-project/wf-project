// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The entry of a cell of a grid, in place of its value (WF-IHM-0040): a field for a text or a
 * number. It takes the focus as it opens.
 * Enter validates it, and the cursor goes to the row below — to the cell the row was started
 * from when Tab went along it —; Tab validates it and goes to the next cell that takes an entry,
 * Shift+Tab to the one before, traversing the computed cells; Escape abandons it, the cell left
 * as it was. Leaving it otherwise — a click elsewhere — validates it where it is, or abandons it
 * when it holds no number of the language.
 */
"use client";

import { type KeyboardEvent, useLayoutEffect, useRef } from "react";

import { Input } from "@/components/ui/input";

import type { EntryKind } from "./columns";

/** Where the cursor goes once an entry is validated: below, along the row, or nowhere. */
export type EntryMove = "down" | "next" | "previous" | "none";

/** What a key asks of an entry: to validate it and go somewhere, to abandon it, or nothing. */
function keyMove(event: KeyboardEvent): EntryMove | "abandon" | undefined {
  switch (event.key) {
    case "Escape":
      return "abandon";
    case "Enter":
      return "down";
    case "Tab":
      return event.shiftKey ? "previous" : "next";
    default:
      return undefined;
  }
}

/** What an entry is, where it starts, and what it does once validated or abandoned. */
export interface CellEditorProps {
  readonly kind: EntryKind;
  /** The name of the entry: the heading of its column. */
  readonly label: string;
  /** The text it starts from. */
  readonly text: string;
  /** The identifier of what says the text is not a number of the language, when it is not. */
  readonly invalid: string | undefined;
  /** Validate the text: whether the entry is done — a number misread keeps it open. */
  readonly onValidate: (text: string, move: EntryMove) => boolean;
  /** Abandon the entry: from the keyboard, the focus back on its cell; on a blur, where it went. */
  readonly onAbandon: (refocus: boolean) => void;
}

/** Render the entry of a cell. */
export function CellEditor({ kind, label, text, invalid, onValidate, onAbandon }: CellEditorProps) {
  const field = useRef<HTMLInputElement>(null);
  // Done once validated or abandoned: the blur that follows as it goes validates nothing more.
  const done = useRef(false);
  useLayoutEffect(() => {
    const element = field.current;
    element?.focus();
    // The caret after what is typed, as when typing goes on.
    element?.setSelectionRange(element.value.length, element.value.length);
  }, []);
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    const move = keyMove(event);
    if (move === undefined) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    done.current = true;
    if (move === "abandon") {
      onAbandon(true);
    } else {
      done.current = onValidate(event.currentTarget.value, move);
    }
  };
  const common = {
    ref: field,
    "aria-label": label,
    "aria-invalid": invalid === undefined ? undefined : true,
    "aria-describedby": invalid,
    defaultValue: text,
    onKeyDown,
    // Left otherwise, validated where it is — abandoned if it is not a number of the language.
    onBlur: (event: { readonly currentTarget: { readonly value: string } }) => {
      if (!done.current) {
        done.current = true;
        if (!onValidate(event.currentTarget.value, "none")) {
          onAbandon(false);
        }
      }
    },
  };
  return (
    <Input
      {...common}
      inputMode={kind.type === "text" ? undefined : "decimal"}
      className={
        kind.type === "text"
          ? "h-6 rounded-sm px-1 text-xs"
          : "h-6 rounded-sm px-1 text-right text-xs"
      }
    />
  );
}
