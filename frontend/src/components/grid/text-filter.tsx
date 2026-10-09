// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a list on a text (WF-IHM-0130) — the code of the nodes of organisation, the
 * correlation of the journal of audit —, sent when entered, lifted when emptied, back to the first
 * page of a list the server pages; of the length the contract takes at most, and of the form it
 * takes, if it takes one. The text only changes the address, under the name of the contract
 * (`filterHref`), and goes on from the address last asked (`usePendingAddress`): a sort or a search
 * under way is kept. An entry is dated by the text of the address (`useDatedEntry`): a text the
 * address changes — back in the history — shows anew, what was typed and not sent given up, what
 * was typed on while the text sent was on its way kept, and the field keeps the focus.
 */
"use client";

import { usePathname } from "next/navigation";
import { type SubmitEvent, useId } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { useDatedEntry } from "./dated-entry";
import { filterHref } from "./filters";
import { PendingAddress, usePendingAddress } from "./pending-address";

/** What a filter on a text shows: the parameter it writes, its name, the text the address holds. */
interface TextFilterProps {
  /** The parameter of the address the filter writes. */
  readonly name: string;
  readonly label: string;
  /** The text the address filters on; none, no filter. */
  readonly value: string | undefined;
  /** The longest text the contract takes. */
  readonly length: number;
  /** The parameter of the page of a list the server pages, which the filter takes back to its first. */
  readonly page?: string;
  /**
   * The form of a text the contract takes (`pattern` of the field): another is not sent, and the
   * browser says why.
   */
  readonly pattern?: string;
  /** The form the pattern asks, in words, which the browser says of a text out of it. */
  readonly form?: string;
}

/**
 * Render the filter of a list on a text, the one the address holds entered, sharing the address
 * last asked with its screen, or keeping its own (`PendingAddress`): what is typed on while the
 * text sent is on its way survives its arrival on a screen that shares none too.
 */
export function TextFilter(props: TextFilterProps) {
  return (
    <PendingAddress>
      <SharedTextFilter {...props} />
    </PendingAddress>
  );
}

/** Render the filter of a list on a text, the address last asked shared. */
function SharedTextFilter({ name, label, value, length, page, pattern, form }: TextFilterProps) {
  const id = useId();
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const { entered, enter, sent } = useDatedEntry<"text">(value ?? "");
  const text = entered.text ?? value ?? "";
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    // A text out of the form the contract takes is not sent: the browser says why — it sends no
    // such form itself, and this holds where something submits it all the same.
    if (!event.currentTarget.reportValidity()) {
      return;
    }
    const trimmed = text.trim();
    // Sent, the text arrives as the address writes it: only what is typed on after it stays.
    sent();
    request((query) =>
      filterHref(pathname, query, name, trimmed === "" ? undefined : trimmed, page ?? []),
    );
  };
  return (
    <form aria-label={label} onSubmit={submit} className="flex items-center gap-2 text-sm">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="search"
        value={text}
        maxLength={length}
        pattern={pattern}
        title={form}
        onChange={(event) => {
          enter("text", event.target.value);
        }}
        className="h-7 w-32 text-xs"
      />
    </form>
  );
}
