// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the reference data filter their lists by, besides the search of each grid
 * (WF-IHM-0130): the state of each list (WF-REF-0150, `is_active` after the prefix of its grid,
 * the active objects by default); an object chosen — the node of
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

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useOptimistic, useTransition } from "react";

import { CheckMenu } from "@/components/grid/check-menu";
import { ChoiceFilter } from "@/components/grid/choice-filter";
import { filterHref } from "@/components/grid/filters";
import { usePendingAddress } from "@/components/grid/pending-address";

import { ACTIVE_STATE, EVERY_STATE, INACTIVE_STATE } from "./address";
import { treeLabel } from "./org-tree";

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
 * The filter of a list on the state of its objects (`is_active`, WF-REF-0150): the active ones alone —
 * the state by default —, the deactivated ones alone, or every state, which the address writes
 * (`EVERY_STATE`) so that neither the account nor the default takes its place; a button for each,
 * pressed as last asked until the server answers, then as the address shows it. Offered only to a
 * session that may read the deactivated objects: for another, the list holds the active ones alone,
 * and the filter would change nothing.
 */
export function StateFilter({
  name,
  label,
  chosen,
  page,
}: {
  /** The parameter of the address the filter writes. */
  readonly name: string;
  /** The name of the menu: the state of which list. */
  readonly label: string;
  /** The state the list shows; none, every state. */
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
  return (
    <CheckMenu
      label={label}
      every={t("every")}
      multiple={false}
      options={[
        { value: ACTIVE_STATE, text: t("active") },
        { value: INACTIVE_STATE, text: t("inactive") },
      ]}
      chosen={shown === undefined ? [] : [shown ? ACTIVE_STATE : INACTIVE_STATE]}
      onChange={([value]) => {
        startTransition(() => {
          show(value === undefined ? undefined : value === ACTIVE_STATE);
          // The active ones are written too: an address that named none would read the state kept.
          request((query) => filterHref(pathname, query, name, value ?? EVERY_STATE, page));
        });
      }}
    />
  );
}
