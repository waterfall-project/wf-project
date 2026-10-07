// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the grid of the actual costs that show more than a value formatted: the sub-project
 * a line is charged to, by its code and its label as the server resolves them, or that it is
 * charged to the project alone — with the code read in its OTP element when the file gave one that
 * no sub-project of the project bears (WF-CRE-0020); whether it is in the tracked scope, in words and by
 * an icon, never by a colour alone (WF-CRE-0030). The columns of the file kept for information
 * are columns of their own (`costGrid`), their values as imported — never translated
 * (WF-CRE-0010).
 */
"use client";

import { CircleCheck, CircleSlash } from "lucide-react";
import { useTranslations } from "next-intl";

import type { CostRow } from "./cost-grid";

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
