// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The menu of a list of values of a filter (WF-IHM-0130, #2916): a button that says what is chosen
 * — « Tous », the one value, or « n sélectionnés » — and opens a list of boxes to check, one for
 * each value and one for every value, with a search over the list once it holds more than ten
 * values (or when asked). Checking a box applies at once and keeps the menu open, so that several
 * values are checked in a row; a menu of one choice (`multiple` false) takes the choice and
 * closes. The label stands above the button and names it, with what it says. The list is a
 * modal dialog, as the harness of accessibility wants of one (`e2e/tab-walk.ts`): Tab stays in it,
 * Escape or a click away closes it and gives the focus back to its button.
 */
"use client";

import { ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode, useEffect, useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

/** From how many values a menu offers a search. */
export const SEARCHED_FROM = 11;

/** How long a text typed waits before it is searched on the server, in milliseconds. */
const SEARCH_DELAY = 300;

/** The line of a value in the list. */
const ROW = "flex items-center gap-2 rounded-sm px-1 py-1 text-sm hover:bg-accent";

/** A value of the menu: what is chosen, what shows it, and what the search matches. */
export interface CheckOption {
  readonly value: string;
  /** What the value shows: a text, or a badge drawn. */
  readonly text: ReactNode;
  /** The text the search matches; the text itself when it is a string. */
  readonly plain?: string | undefined;
  /** Whether the search of the list leaves it: a value the server found for that very search. */
  readonly found?: boolean | undefined;
}

/** A text as the search compares it: lower case, without accents. */
function folded(text: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase();
}

/** The text of an option: what the search matches. */
function plainOf(option: CheckOption): string {
  return option.plain ?? (typeof option.text === "string" ? option.text : option.value);
}

/** Render the menu of a list of values, those chosen checked. */
export function CheckMenu({
  label,
  every,
  options,
  chosen,
  multiple,
  searchable,
  onChange,
  onQuery,
  footer,
}: {
  /** What the menu filters on: it stands above the button and names it. */
  readonly label: string;
  /** The text of the choice that lifts the filter. */
  readonly every: string;
  readonly options: readonly CheckOption[];
  /** The values chosen; none, every one. */
  readonly chosen: readonly string[];
  /** Whether several values may be chosen. */
  readonly multiple: boolean;
  /** Whether the menu offers a search; by default, from eleven values. */
  readonly searchable?: boolean | undefined;
  /**
   * What a choice applies: the values now chosen and, for a box checked or unchecked, which — a
   * filter goes on from the address last asked, not from the values shown.
   */
  readonly onChange: (
    values: readonly string[],
    toggled?: { readonly value: string; readonly checked: boolean },
  ) => void;
  /** What a text typed in the search asks of the server, once the typing pauses; none, a search of the list alone. */
  readonly onQuery?: ((text: string) => void) | undefined;
  /** What stands under the list: the outcome of a search of the server. */
  readonly footer?: ReactNode;
}) {
  const t = useTranslations("grid.filtering");
  const id = useId();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const searching = searchable ?? (options.length >= SEARCHED_FROM || onQuery !== undefined);
  useEffect(() => {
    if (onQuery === undefined || text.trim() === "") {
      return;
    }
    const timer = setTimeout(() => {
      onQuery(text.trim());
    }, SEARCH_DELAY);
    return () => {
      clearTimeout(timer);
    };
  }, [text, onQuery]);
  const needle = folded(text.trim());
  const shown = options.filter(
    (option) => needle === "" || option.found === true || folded(plainOf(option)).includes(needle),
  );
  const picked = options.filter((option) => chosen.includes(option.value));
  let summary: ReactNode = every;
  if (picked.length === 1) {
    summary = picked[0]?.text;
  } else if (chosen.length > 1) {
    summary = t("selected", { count: chosen.length });
  } else if (chosen.length === 1) {
    // Chosen by the address and not offered: named by what the address says.
    summary = chosen[0];
  }
  const lift = multiple ? (
    <label className={ROW}>
      <Checkbox
        checked={chosen.length === 0}
        onCheckedChange={() => {
          onChange([]);
        }}
      />
      {every}
    </label>
  ) : (
    <label className={ROW}>
      <RadioGroupItem value="" />
      {every}
    </label>
  );
  return (
    <div className="flex min-w-48 flex-col gap-1 text-sm">
      <Label id={`${id}-label`}>{label}</Label>
      <Popover
        modal
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          setText("");
        }}
      >
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="sm"
            id={`${id}-button`}
            aria-labelledby={`${id}-label ${id}-button`}
            className="w-full min-w-0 justify-between font-normal"
          >
            <span className="truncate">{summary}</span>
            <ChevronDown aria-hidden="true" className="size-4 shrink-0" />
          </Button>
        </PopoverTrigger>
        <PopoverContent align="start" className="flex max-h-80 w-64 flex-col gap-2 p-2">
          {searching ? (
            <Input
              type="search"
              aria-label={t("search", { label })}
              value={text}
              onChange={(event) => {
                setText(event.target.value);
              }}
              className="h-8"
            />
          ) : null}
          {multiple ? (
            <div role="group" aria-label={label} className="flex flex-col overflow-y-auto">
              {lift}
              {shown.map((option) => (
                <label key={option.value} className={ROW}>
                  <Checkbox
                    checked={chosen.includes(option.value)}
                    onCheckedChange={(checked) => {
                      const on = checked === true;
                      onChange(
                        on
                          ? [...chosen, option.value]
                          : chosen.filter((each) => each !== option.value),
                        { value: option.value, checked: on },
                      );
                    }}
                  />
                  {option.text}
                </label>
              ))}
            </div>
          ) : (
            <RadioGroup
              aria-label={label}
              value={chosen[0] ?? ""}
              onValueChange={(value) => {
                onChange(value === "" ? [] : [value]);
                setOpen(false);
              }}
              className="flex max-h-60 flex-col gap-0 overflow-y-auto"
            >
              {lift}
              {shown.map((option) => (
                <label key={option.value} className={ROW}>
                  <RadioGroupItem value={option.value} />
                  {option.text}
                </label>
              ))}
            </RadioGroup>
          )}
          {shown.length === 0 ? (
            <p className="px-1 text-xs text-muted-foreground">{t("noMatch")}</p>
          ) : null}
          {footer}
        </PopoverContent>
      </Popover>
    </div>
  );
}
