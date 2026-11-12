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
import {
  type KeyboardEvent,
  type ReactElement,
  type ReactNode,
  useEffect,
  useId,
  useState,
} from "react";

import { CommandTooltip } from "@/components/commands/command-tooltip";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/components/ui/utils";

/** From how many values a menu offers a search. */
export const SEARCHED_FROM = 11;

/** How long a text typed waits before it is searched on the server, in milliseconds. */
const SEARCH_DELAY = 300;

/** The line of a value in the list. */
const ROW = "flex items-center gap-2 rounded-sm px-1 py-1 text-sm hover:bg-accent";

/** Move the focus among the radios of a menu, the arrows only moving it: a choice is made by Space, Enter or a click. */
function moveFocus(event: KeyboardEvent<HTMLElement>) {
  const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[event.key];
  if (step === undefined) {
    return;
  }
  event.preventDefault();
  const radios = [...event.currentTarget.querySelectorAll<HTMLElement>('[role="radio"]')];
  const at = radios.indexOf(document.activeElement as HTMLElement);
  radios[(at + step + radios.length) % radios.length]?.focus();
}

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

/** What the button shows of the choice, and the text a reader is told of it. */
function summaryOf(
  options: readonly CheckOption[],
  chosen: readonly string[],
  every: string,
  selected: (count: number) => string,
): { readonly summary: ReactNode; readonly said: string } {
  const [one] = options.filter((option) => chosen.includes(option.value));
  if (chosen.length > 1) {
    return { summary: selected(chosen.length), said: selected(chosen.length) };
  }
  if (one !== undefined && chosen.length === 1) {
    return { summary: one.text, said: plainOf(one) };
  }
  // Chosen by the address and not offered: named by what the address says.
  const unoffered = chosen[0];
  return unoffered === undefined
    ? { summary: every, said: every }
    : { summary: unoffered, said: unoffered };
}

/**
 * The region that tells a reader the choice while the list hides the page: mounted empty and
 * filled after, so that the text is announced, and again at each change.
 */
function Announced({ text }: { readonly text: string }) {
  const [told, setTold] = useState("");
  useEffect(() => {
    // After the region is in the document, so that the reader sees the text arrive.
    const timer = setTimeout(() => {
      setTold(text);
    }, 0);
    return () => {
      clearTimeout(timer);
    };
  }, [text]);
  return (
    <p role="status" className="sr-only">
      {told}
    </p>
  );
}

/** How a menu looks: above its field, or in the bar of a grid (#2916/L6). */
interface Look {
  /** The classes of the menu as a whole. */
  readonly menu: string;
  /** The classes of its button. */
  readonly button: string;
  /** Whether the label stands above the button; otherwise it stands on it, and names it. */
  readonly above: boolean;
}

/** A menu beside the filters of a list: its label above, the button the width of the field. */
const FIELD: Look = {
  menu: "min-w-48",
  button: "w-full min-w-0 justify-between font-normal",
  above: true,
};

/**
 * A menu in the bar of a grid: the height of the buttons of the bar, a floor under which it does not
 * go (the chevron and a few characters), and a width it gives up before the bar scrolls.
 */
const BAR: Look = {
  menu: "min-w-24 shrink basis-56",
  button: "h-7 w-full min-w-0 max-w-56 justify-between gap-1 text-xs font-normal",
  above: false,
};

/**
 * The tooltip of the button of a menu in a bar, whose value may be cut to the room it has: it says
 * the whole of it (`CommandTooltip`, never a `title`); a menu above its field has none.
 */
function BarTip({
  look,
  text,
  help,
  children,
}: {
  readonly look: Look;
  readonly text: string;
  readonly help: string;
  readonly children: ReactElement;
}) {
  return look.above ? (
    children
  ) : (
    <CommandTooltip label={text} help={help}>
      {children}
    </CommandTooltip>
  );
}

/** The look of a menu, in a bar or not. */
function lookOf(compact: boolean | undefined): Look {
  return compact === true ? BAR : FIELD;
}

/** The label a button of the bar carries before the choice, which names it; none above a menu. */
function ButtonLabel({ label }: { readonly label: string | undefined }) {
  return label === undefined ? null : <span className="text-muted-foreground">{label} </span>;
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
  compact,
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
  /**
   * For a menu in a bar (#2916/L6): the button on the height of the bar's, the label on it before
   * the choice — it names the button — and not above, the width of what it says.
   */
  readonly compact?: boolean | undefined;
}) {
  const t = useTranslations("grid.filtering");
  const look = lookOf(compact);
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
  const { summary, said } = summaryOf(options, chosen, every, (count) => t("selected", { count }));
  /** Close the list, and forget what was searched in it. */
  const close = () => {
    setOpen(false);
    setText("");
    onQuery?.("");
  };
  // The one radio Tab reaches: the one chosen if it is shown, else the first shown.
  const current = chosen[0] ?? "";
  const tabbable =
    current === "" || shown.some((option) => option.value === current) ? current : "";
  /** A value of a menu of one choice: a radio the arrows only reach. */
  const radio = (value: string, text: ReactNode) => {
    const checked = (chosen[0] ?? "") === value;
    return (
      <button
        key={value}
        type="button"
        role="radio"
        aria-checked={checked}
        tabIndex={value === tabbable ? 0 : -1}
        className={cn(
          ROW,
          "w-full text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        )}
        onClick={() => {
          if (!checked) {
            onChange(value === "" ? [] : [value]);
          }
          close();
        }}
      >
        <span
          aria-hidden="true"
          className="flex size-4 shrink-0 items-center justify-center rounded-full border border-input bg-background"
        >
          {checked ? <span className="size-2 rounded-full bg-primary" /> : null}
        </span>
        {text}
      </button>
    );
  };
  const lift = multiple ? (
    <label className={ROW}>
      <Checkbox
        checked={chosen.length === 0}
        onCheckedChange={() => {
          // Every value is already the choice: nothing to ask of the server.
          if (chosen.length > 0) {
            onChange([]);
          }
        }}
      />
      {every}
    </label>
  ) : (
    radio("", every)
  );
  return (
    <div className={cn("flex flex-col gap-1 text-sm", look.menu)}>
      {look.above ? <Label id={`${id}-label`}>{label}</Label> : null}
      <Popover
        modal
        open={open}
        onOpenChange={(next) => {
          if (next) {
            setOpen(true);
          } else {
            close();
          }
        }}
      >
        <BarTip look={look} text={`${label} ${said}`} help={t("barHelp", { label, value: said })}>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="outline"
              size="sm"
              id={`${id}-button`}
              aria-labelledby={look.above ? `${id}-label ${id}-button` : undefined}
              className={look.button}
            >
              <span className="truncate">
                <ButtonLabel label={look.above ? undefined : label} />
                {summary}
              </span>
              <ChevronDown aria-hidden="true" className="size-4 shrink-0" />
            </Button>
          </PopoverTrigger>
        </BarTip>
        <PopoverContent align="start" className="flex max-h-80 w-64 flex-col gap-2 p-2">
          {searching ? (
            <Input
              type="search"
              aria-label={t("search", { label })}
              value={text}
              onChange={(event) => {
                setText(event.target.value);
                if (event.target.value.trim() === "") {
                  onQuery?.("");
                }
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
            <div
              role="radiogroup"
              aria-label={label}
              onKeyDown={moveFocus}
              className="flex max-h-60 flex-col overflow-y-auto"
            >
              {lift}
              {shown.map((option) => radio(option.value, option.text))}
            </div>
          )}
          {shown.length === 0 ? (
            <p className="px-1 text-xs text-muted-foreground">{t("noMatch")}</p>
          ) : null}
          <Announced text={said} />
          {footer}
        </PopoverContent>
      </Popover>
    </div>
  );
}
