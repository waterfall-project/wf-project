// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the grid of the actual costs that show more than a value formatted: the sub-project
 * a line is charged to, by its code and its label as the server resolves them, or that it is
 * charged to the project alone — with the code read in its OTP element when the file gave one that
 * no sub-project of the project bears (WF-CRE-0020); whether it is in the tracked scope, in words and by
 * an icon, never by a colour alone (WF-CRE-0030). The columns of the file kept for information
 * are columns of their own (`costGrid`), their values as imported — never translated
 * (WF-CRE-0010). And, where the user may exclude a line or reinstate it, its number of document, a
 * link that shows its place in the tracked scope to change it (WF-CRE-0040), out of the order of
 * tabulation, the grid being one stop, which follows it on Enter (`grid-keyboard.ts`).
 */
"use client";

import { CircleCheck, CircleSlash } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { usePendingLink } from "@/components/grid/pending-address";

import { lineHref, readCostLine } from "./address";
import type { CostRow } from "./cost-grid";

/**
 * Show a line to change its place in the tracked scope — or none, `undefined` —, from the address
 * last asked: a sort or a filter under way is kept.
 */
export function useLineNavigation(line: string | undefined) {
  const pathname = usePathname();
  return usePendingLink((query) => lineHref(pathname, query, line));
}

/** Render the number of document of a line, as a link that shows it; the line shown says so. */
export function CostLineCell({ line }: { readonly line: CostRow }) {
  const shown = readCostLine(useSearchParams()) === line.cost_line_id;
  const { href, onClick } = useLineNavigation(line.cost_line_id);
  return (
    <Link
      href={href}
      onClick={onClick}
      tabIndex={-1}
      aria-current={shown ? "true" : undefined}
      className="block truncate underline-offset-2 hover:underline aria-[current]:font-semibold"
      scroll={false}
    >
      {line.document_number}
    </Link>
  );
}

/**
 * Render the sub-project of a line: its code and its label, or « no sub-project » — followed by
 * the code the OTP element gave, kept and shown when it matches no sub-project (WF-CRE-0020).
 */
export function SubprojectCell({ line }: { readonly line: CostRow }) {
  const t = useTranslations("enums.SubprojectFilter");
  // A line charged to the project alone has no sub-project to name: the label says so.
  if (line.subproject_label === null) {
    return (
      <span className="flex min-w-0 gap-1.5">
        <span className="truncate text-muted-foreground italic">{t("unassigned")}</span>
        {line.subproject_code === null ? null : (
          <span className="shrink-0 font-medium">{line.subproject_code}</span>
        )}
      </span>
    );
  }
  return (
    <span className="flex min-w-0 gap-1.5">
      <span className="shrink-0 font-medium">{line.subproject_code}</span>
      <span className="truncate">{line.subproject_label}</span>
    </span>
  );
}

/** Render whether a line is in the tracked scope: an icon and its word. */
export function ScopeCell({ tracked }: { readonly tracked: boolean }) {
  const t = useTranslations("actualCosts.scope");
  const Icon = tracked ? CircleCheck : CircleSlash;
  return (
    <span className="inline-flex items-center gap-1 truncate">
      <Icon aria-hidden="true" className="size-3.5 shrink-0" />
      {t(tracked ? "tracked" : "excluded")}
    </span>
  );
}
