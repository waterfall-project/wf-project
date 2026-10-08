// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the reference data filter their lists by, besides the search of each grid:
 * whether they show the deactivated objects too (WF-REF-0150, `include_inactive`), and the node
 * of organisation the resource roles are restricted to (`org_node_id`, WF-IHM-0130). Each only
 * changes the address, and the server answers anew; the front filters nothing. A change goes on
 * from the address last asked (`usePendingAddress`): a sort or a search under way is kept.
 */
"use client";

import { Eye, EyeOff } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useId } from "react";

import { usePendingAddress, usePendingLink } from "@/components/grid/pending-address";
import { buttonVariants } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";

import { INCLUDE_INACTIVE, parameterHref } from "./address";
import { treeLabel } from "./org-tree";

/**
 * The link that shows the deactivated objects of the lists of the screen too, or hides them again:
 * a link, which works before the page is hydrated.
 */
export function InactiveSwitch({ shown }: { readonly shown: boolean }) {
  const t = useTranslations("reference.inactive");
  const pathname = usePathname();
  const { href, onClick } = usePendingLink((query) =>
    parameterHref(pathname, query, INCLUDE_INACTIVE, shown ? undefined : "true"),
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

/** A node of organisation the roles may be restricted to, with its depth in the tree. */
export interface NodeChoice {
  readonly id: string;
  readonly code: string;
  readonly label: string;
  readonly level: number;
}

/**
 * The filter of the roles by node of organisation, the nodes offered in the order of the tree the
 * server gives, each set in by its depth; a node the address names that is not offered — none the
 * session reads — stays chosen under its identifier, to be cleared.
 */
export function OrgNodeFilter({
  name,
  nodes,
  chosen,
}: {
  /** The parameter of the address the filter writes. */
  readonly name: string;
  readonly nodes: readonly NodeChoice[];
  readonly chosen: string | undefined;
}) {
  const t = useTranslations("reference.resourceRoles");
  const named = useTranslations("reference.orgNodes");
  const id = useId();
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const unknown = chosen !== undefined && !nodes.some((node) => node.id === chosen);
  return (
    <div className="flex items-center gap-2 text-sm">
      <Label htmlFor={id}>{t("orgNodeFilter")}</Label>
      <NativeSelect
        id={id}
        value={chosen ?? ""}
        onChange={(event) => {
          const value = event.target.value === "" ? undefined : event.target.value;
          request((query) => parameterHref(pathname, query, name, value));
        }}
        className="w-64"
      >
        <option value="">{t("everyNode")}</option>
        {nodes.map((node) => (
          <option key={node.id} value={node.id}>
            {treeLabel(node.level, named("choice", { code: node.code, label: node.label }))}
          </option>
        ))}
        {unknown ? <option value={chosen}>{chosen}</option> : null}
      </NativeSelect>
    </div>
  );
}
