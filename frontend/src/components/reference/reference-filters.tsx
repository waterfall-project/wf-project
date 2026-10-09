// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the reference data filter their lists by, besides the search of each grid
 * (WF-IHM-0130): whether they show the deactivated objects too (WF-REF-0150, `include_inactive`);
 * the state of each list (`is_active`, after the prefix of its grid); an object chosen — the node of
 * organisation, the category or the calendar of the roles, the nature of the categories, the node of
 * the accounts (`OrgNodeFilter`, `ChoiceFilter`) —; the code and the depth of the nodes. Each only changes the
 * address, under the name of the contract after the prefix of its grid, back to the first page of a
 * list the server pages, and the server answers anew; the front filters nothing. A change goes on
 * from the address last asked (`usePendingAddress`): a sort or a search under way is kept.
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { Circle, CircleCheck, Eye, EyeOff, ListFilter } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId } from "react";

import { ChoiceFilter } from "@/components/grid/choice-filter";
import { useDatedEntry } from "@/components/grid/dated-entry";
import { filterHref } from "@/components/grid/filters";
import { usePendingAddress, usePendingLink } from "@/components/grid/pending-address";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { INCLUDE_INACTIVE } from "./address";
import { treeLabel } from "./org-tree";

/**
 * The link that shows the deactivated objects of the lists of the screen too, or hides them again,
 * back to the first page of each list the server pages (`pages`): a link, which works before the
 * page is hydrated.
 */
export function InactiveSwitch({
  shown,
  pages = [],
}: {
  readonly shown: boolean;
  /** The parameters of the pages of the lists of the screen. */
  readonly pages?: readonly string[];
}) {
  const t = useTranslations("reference.inactive");
  const pathname = usePathname();
  const { href, onClick } = usePendingLink((query) =>
    filterHref(pathname, query, INCLUDE_INACTIVE, shown ? undefined : "true", pages),
  );
  return (
    <Link
      href={href}
      onClick={onClick}
      scroll={false}
      className={buttonVariants({ variant: "outline", size: "sm" })}
    >
      {shown ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
      {shown ? t("hide") : t("show")}
    </Link>
  );
}

/** A node of organisation a list may be restricted to, with its depth in the tree. */
export interface NodeChoice {
  readonly id: string;
  readonly code: string;
  readonly label: string;
  readonly level: number;
}

/**
 * The filter of a list by node of organisation — the roles, the accounts, the labour of the
 * portfolio —, the nodes offered in the order of the tree the server gives, each set in by its depth.
 */
export function OrgNodeFilter({
  name,
  nodes,
  chosen,
  page,
  label,
  every,
}: {
  /** The parameter of the address the filter writes. */
  readonly name: string;
  readonly nodes: readonly NodeChoice[];
  readonly chosen: string | undefined;
  /** The parameter of the page of a list the server pages, which a node chosen takes back to its first. */
  readonly page?: string | undefined;
  /** What the filter filters on, and the choice that lifts it; those of a list of roles by default. */
  readonly label?: string;
  readonly every?: string;
}) {
  const t = useTranslations("reference.resourceRoles");
  const named = useTranslations("reference.orgNodes");
  return (
    <ChoiceFilter
      name={name}
      label={label ?? t("orgNodeFilter")}
      every={every ?? t("everyNode")}
      choices={nodes.map((node) => ({
        value: node.id,
        text: treeLabel(node.level, named("choice", { code: node.code, label: node.label })),
      }))}
      chosen={chosen}
      page={page}
    />
  );
}

/**
 * The filter of a list on the state of its objects (`is_active`): every state — as the switch of the
 * deactivated objects decides —, the active ones alone, or the deactivated ones alone; a button
 * pressed for each, as the address shows it. Offered only to a session that may read the deactivated
 * objects: for another, the list holds the active ones alone, and the filter would change nothing.
 */
export function StateFilter({
  name,
  label,
  chosen,
  page,
}: {
  /** The parameter of the address the filter writes. */
  readonly name: string;
  /** The name of the group of buttons: the state of which list. */
  readonly label: string;
  /** The state the address filters on; none, every state. */
  readonly chosen: boolean | undefined;
  /** The parameter of the page of a list the server pages, which a filter takes back to its first. */
  readonly page?: string | undefined;
}) {
  const t = useTranslations("reference.stateFilter");
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const states: readonly { readonly value: boolean | undefined; readonly text: string }[] = [
    { value: undefined, text: t("every") },
    { value: true, text: t("active") },
    { value: false, text: t("inactive") },
  ];
  return (
    <div role="group" aria-label={label} className="flex flex-wrap items-center gap-1.5">
      {states.map(({ value, text }) => {
        const pressed = chosen === value;
        const Icon = value === undefined ? ListFilter : pressed ? CircleCheck : Circle;
        return (
          <Button
            key={text}
            size="sm"
            variant={pressed ? "default" : "outline"}
            aria-pressed={pressed}
            onClick={() => {
              request((query) => filterHref(pathname, query, name, value?.toString(), page));
            }}
          >
            <Icon aria-hidden="true" className="size-4" />
            {text}
          </Button>
        );
      })}
    </div>
  );
}

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
 * The filter of a list on a text — the code of the nodes, the correlation of the journal of audit —,
 * sent when entered, lifted when emptied, back to the first page of a list the server pages; of the
 * length the contract takes at most. An entry is dated by the
 * text of the address (`useDatedEntry`): a text the address changes — back in the history — shows
 * anew, what was typed and not sent given up, and the field keeps the focus.
 */
export function TextFilter({ name, label, value, length, page, pattern, form }: TextFilterProps) {
  const id = useId();
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const { entered, enter } = useDatedEntry<"text">(value ?? "");
  const text = entered.text ?? value ?? "";
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    // A text out of the form the contract takes is not sent: the browser says why — it sends no
    // such form itself, and this holds where something submits it all the same.
    if (!event.currentTarget.reportValidity()) {
      return;
    }
    const trimmed = text.trim();
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
