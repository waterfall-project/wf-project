// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The entry of a cell of a grid, in place of its value (WF-IHM-0040): a field for a text or a
 * number, the list of its choices for a category or a role. It takes the focus as it opens.
 * Enter validates it, and the cursor goes to the row below — to the cell the row was started
 * from when Tab went along it —; Tab validates it and goes to the next cell that takes an entry,
 * Shift+Tab to the one before, traversing the computed cells; Escape abandons it, the cell left
 * as it was. Leaving it otherwise — a click elsewhere — validates it where it is, or abandons it
 * when it holds no number of the language.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { type KeyboardEvent, useLayoutEffect, useRef } from "react";

import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";

import { firstChoice } from "./cell-values";
import type { Choice, EntryKind } from "./columns";

/** How long a pause forgets what was typed in a list, in milliseconds. */
const SEARCH_PAUSE = 1_000;

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
  /** The text it starts from — the identifier of the choice made, for a list. */
  readonly text: string;
  /** The character typed that opened it, if one did: a list goes on searching from it. */
  readonly typed: string | undefined;
  /** The identifier of what says why the text was not validated, when it was not. */
  readonly invalid: string | undefined;
  /** Validate the text: whether the entry is done — a number misread keeps it open. */
  readonly onValidate: (text: string, move: EntryMove) => boolean;
  /** Abandon the entry: from the keyboard, the focus back on its cell; on a blur, where it went. */
  readonly onAbandon: (refocus: boolean) => void;
}

/** Render the entry of a cell. */
export function CellEditor({
  kind,
  label,
  text,
  typed,
  invalid,
  onValidate,
  onAbandon,
}: CellEditorProps) {
  const t = useTranslations("grid.entry");
  const locale = useLocale();
  const field = useRef<HTMLInputElement | HTMLSelectElement>(null);
  // What was typed in a list, which picks the first choice whose name starts with it; forgotten
  // after a pause, as a list of the browser forgets it.
  // The character that opened the list is searched on from, whatever the pause after it.
  const search = useRef({ typed: typed ?? "", at: Number.POSITIVE_INFINITY });
  // Done once validated or abandoned: the blur that follows as it goes validates nothing more.
  const done = useRef(false);
  useLayoutEffect(() => {
    const element = field.current;
    element?.focus();
    // The caret after what is typed, as when typing goes on.
    if (element instanceof HTMLInputElement) {
      element.setSelectionRange(element.value.length, element.value.length);
    }
  }, []);
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement | HTMLSelectElement>) => {
    const move = keyMove(event);
    if (move === undefined) {
      if (kind.type === "choice" && event.currentTarget instanceof HTMLSelectElement) {
        const none = { id: "", label: t("none"), active: true };
        searchList(event, event.currentTarget, [
          ...(kind.nullable ? [none] : []),
          ...kind.choices(),
        ]);
      }
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
  /** Pick, from a character typed in a list, the first choice whose name starts with the search. */
  const searchList = (
    event: KeyboardEvent,
    list: HTMLSelectElement,
    choices: readonly Choice[],
  ) => {
    if (!/^.$/u.test(event.key) || event.ctrlKey || event.metaKey || event.altKey) {
      return;
    }
    const now = Date.now();
    const kept = now - search.current.at < SEARCH_PAUSE ? search.current.typed : "";
    // Space opens the list, as the browser's does, unless it goes on a search (#198).
    if (event.key === " " && kept === "") {
      return;
    }
    event.preventDefault();
    search.current = { typed: kept + event.key, at: now };
    const found = firstChoice(choices, search.current.typed, locale);
    if (found !== undefined) {
      list.value = found.id;
    }
  };
  const common = {
    // A list or a field: the one reference takes either.
    ref: (element: HTMLInputElement | HTMLSelectElement | null) => {
      field.current = element;
    },
    "aria-label": label,
    "aria-invalid": invalid === undefined ? undefined : true,
    "aria-describedby": invalid,
    defaultValue: text,
    onKeyDown,
    // Left otherwise, validated where it is — abandoned if it cannot be. The window left, the
    // field keeps the focus of its document: nothing is left, nothing validated.
    onBlur: (event: { readonly currentTarget: HTMLInputElement | HTMLSelectElement }) => {
      if (!done.current && document.activeElement !== event.currentTarget) {
        done.current = true;
        if (!onValidate(event.currentTarget.value, "none")) {
          onAbandon(false);
        }
      }
    },
  };
  if (kind.type === "choice") {
    return (
      <NativeSelect {...common} className="h-6 rounded-sm text-xs">
        {kind.nullable || text === "" ? <option value="">{t("none")}</option> : null}
        {/* The choices that may be chosen, and the one made if it was deactivated since. */}
        {kind
          .choices()
          .filter((choice) => choice.active || choice.id === text)
          .map((choice) => (
            <option key={choice.id} value={choice.id}>
              {choice.label}
            </option>
          ))}
      </NativeSelect>
    );
  }
  return (
    <Input
      {...common}
      inputMode={kind.type === "text" ? undefined : "decimal"}
      maxLength={kind.type === "text" ? kind.maxLength : undefined}
      className={
        kind.type === "text"
          ? "h-6 rounded-sm px-1 text-xs"
          : "h-6 rounded-sm px-1 text-right text-xs"
      }
    />
  );
}
