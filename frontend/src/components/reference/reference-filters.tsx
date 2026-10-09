// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the reference data filter their lists by, besides the search of each grid
 * (WF-IHM-0130): whether they show the deactivated objects too (WF-REF-0150, `include_inactive`);
 * the state of each list (`is_active`, after the prefix of its grid); an object chosen — the node of
 * organisation, the category or the calendar of the roles, the nature of the categories, the node of
 * the accounts (`OrgNodeFilter`, `ChoiceFilter`) —; the code (`TextFilter` of the grid) and the depth
 * of the nodes. Each only changes the address, under the name of the contract after the prefix of its
 * grid, back to the first page of a list the server pages, and the server answers anew; the front
 * filters nothing. A change goes on from the address last asked (`usePendingAddress`): a sort or a
 * search under way is kept.
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { Circle, CircleCheck, Eye, EyeOff, ListFilter } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useOptimistic, useTransition } from "react";

import { ChoiceFilter } from "@/components/grid/choice-filter";
import { filterHref } from "@/components/grid/filters";
import { usePendingAddress, usePendingLink } from "@/components/grid/pending-address";
import { Button, buttonVariants } from "@/components/ui/button";

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
 * deactivated objects decides —, the active ones alone, or the deactivated ones alone; a button for
 * each, pressed as last asked until the server answers, then as the address shows it. Offered only
 * to a session that may read the deactivated objects: for another, the list holds the active ones
 * alone, and the filter would change nothing.
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
  // The state asked, pressed until the server answers for it: the buttons would otherwise show the
  // address until the navigation arrives, and again the address should another navigation replace
  // it (défaut n° 21 de `typescript.md`).
  const [shown, show] = useOptimistic(chosen);
  const [, startTransition] = useTransition();
  const states: readonly { readonly value: boolean | undefined; readonly text: string }[] = [
    { value: undefined, text: t("every") },
    { value: true, text: t("active") },
    { value: false, text: t("inactive") },
  ];
  return (
    <div role="group" aria-label={label} className="flex flex-wrap items-center gap-1.5">
      {states.map(({ value, text }) => {
        const pressed = shown === value;
        const Icon = value === undefined ? ListFilter : pressed ? CircleCheck : Circle;
        return (
          <Button
            key={text}
            size="sm"
            variant={pressed ? "default" : "outline"}
            aria-pressed={pressed}
            onClick={() => {
              startTransition(() => {
                show(value);
                request((query) => filterHref(pathname, query, name, value?.toString(), page));
              });
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
