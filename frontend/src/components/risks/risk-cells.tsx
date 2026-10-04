// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the grid of the risks that show more than a value formatted: the label of a risk,
 * a link to its detail on the same screen — its description, its mitigation, the history of its
 * reviews (WF-RIS-0040) —, out of the order of tabulation, the grid being one stop, which follows
 * it on Enter (`grid-keyboard.ts`); its state, by the catalogue; the cell of the matrix it falls
 * in, by the one signal of the application (WF-IHM-0070), whose zone the server gives. And the
 * link that closes the detail, which keeps the rest of the address as the label's does.
 */
"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { Signal } from "@/components/signal/signal";
import { buttonVariants } from "@/components/ui/button";

import { readRisk, riskHref, type RiskState } from "./address";
import type { RiskRow } from "./risk-grid";

/** Render the label of a risk, as a link to its detail; the risk shown says so. */
export function RiskLabelCell({ risk }: { readonly risk: RiskRow }) {
  const pathname = usePathname();
  const query = useSearchParams();
  const shown = readRisk(query) === risk.risk_id;
  return (
    <Link
      href={riskHref(pathname, new URLSearchParams(query), risk.risk_id)}
      tabIndex={-1}
      aria-current={shown ? "true" : undefined}
      className="block truncate underline-offset-2 hover:underline aria-[current]:font-semibold"
      scroll={false}
    >
      {risk.label}
    </Link>
  );
}

/** Render the state of a risk, in the language of the interface. */
export function RiskStateCell({ state }: { readonly state: RiskState }) {
  const t = useTranslations("enums.RiskState");
  return <span className="truncate">{t(state)}</span>;
}

/** Render the cell of the matrix a risk falls in, by its signal; none when the API gives none. */
export function RiskZoneCell({ risk }: { readonly risk: RiskRow }) {
  return risk.matrix_cell === undefined ? null : (
    <Signal zone={risk.matrix_cell.zone} variant="icon" />
  );
}

/** Render the link that closes the detail of a risk: the same screen, its query kept, without it. */
export function CloseRiskDetail() {
  const t = useTranslations("risks.detail");
  const pathname = usePathname();
  const query = useSearchParams();
  return (
    <Link
      href={riskHref(pathname, new URLSearchParams(query), undefined)}
      scroll={false}
      aria-label={t("close")}
      className={buttonVariants({ variant: "ghost", size: "icon" })}
    >
      <X aria-hidden="true" className="size-4" />
    </Link>
  );
}
